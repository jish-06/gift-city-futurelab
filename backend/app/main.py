from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import select
from decimal import Decimal as D
from datetime import date, timedelta, datetime, timezone
from uuid import uuid4
import secrets
from typing import Any
from contextlib import asynccontextmanager
from .db import Base, engine, get_db, SessionLocal
from .config import settings
from .models import *
from .schemas import *
from .engine import calculate_exposures, reconcile, process_event, snapshot_hash, money
from .seed import seed
from .integrations import fetch_zoho_organizations, fetch_zoho_invoices, fetch_zoho_customer_payments, fetch_twelve_data_rate, IntegrationNotConfigured

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.seed_demo_data:
        db=SessionLocal()
        try:
            seed(db)
        finally:
            db.close()
    yield

app=FastAPI(title="FXNexus API", version="0.2.0", description="Event-driven FX exposure and hedge workflow prototype. Simulation only; no live trade execution.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Demo-only in-memory sessions. Replace with a managed identity provider + persistent
# session store before any multi-user or public deployment.
SESSIONS: dict[str, dict[str, Any]] = {}

@app.middleware("http")
async def require_demo_session(request: Request, call_next):
    path = request.url.path
    if request.method == "OPTIONS" or not path.startswith("/api/") or path in {"/api/health", "/api/auth/login"}:
        return await call_next(request)
    auth = request.headers.get("Authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    session = SESSIONS.get(token)
    now = datetime.now(timezone.utc)
    if not session or session["expires_at"] <= now:
        if token:
            SESSIONS.pop(token, None)
        return JSONResponse(status_code=401, content={"detail": "Your FXNexus session has expired. Please sign in again."})
    request.state.user = session
    return await call_next(request)


@app.get("/api/health")
def health(): return {"status":"ok","app":settings.app_name,"mode":"simulation_and_decision_support"}

@app.post("/api/auth/login")
def login(data: LoginIn):
    accounts = {
        settings.demo_maker_email.lower(): {"password": settings.demo_maker_password, "role": "maker", "name": "FXNexus Demo Maker"},
        settings.demo_checker_email.lower(): {"password": settings.demo_checker_password, "role": "checker", "name": "FXNexus Demo Checker"},
    }
    account = accounts.get(data.email.strip().lower())
    if not account or not secrets.compare_digest(data.password, account["password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = secrets.token_urlsafe(36)
    SESSIONS[token] = {
        "email": data.email.strip().lower(),
        "role": account["role"],
        "name": account["name"],
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=settings.demo_session_hours),
    }
    return {"access_token": token, "token_type": "bearer", "expires_in": settings.demo_session_hours * 3600,
            "user": {"email": data.email.strip().lower(), "role": account["role"], "name": account["name"]}}

@app.get("/api/auth/me")
def auth_me(request: Request):
    user = request.state.user
    return {"email": user["email"], "role": user["role"], "name": user["name"], "expires_at": user["expires_at"].isoformat()}

@app.post("/api/auth/logout")
def auth_logout(request: Request):
    auth = request.headers.get("Authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    SESSIONS.pop(token, None)
    return {"status": "signed_out"}

@app.get("/api/dashboard")
def dashboard(db: Session=Depends(get_db)):
    company=db.scalar(select(Company).order_by(Company.created_at))
    if not company: raise HTTPException(404,"No company seeded")
    recs=db.scalars(select(Recommendation).where(Recommendation.company_id==company.id).order_by(Recommendation.created_at.desc())).all()
    invs=db.scalars(select(Invoice).where(Invoice.company_id==company.id,Invoice.status=="OPEN")).all()
    hedges=db.scalars(select(Hedge).where(Hedge.company_id==company.id,Hedge.status=="OPEN")).all()
    return {"company":{"id":company.id,"name":company.name,"base_currency":company.base_currency},"exposures":calculate_exposures(db,company.id),"open_hedges":len(hedges),"open_invoices":len(invs),"pending_recommendations":sum(1 for r in recs if r.status in ["PENDING_REVIEW","UNDER_REVIEW","ACTION_PROPOSED"]),"recent_recommendations":[rec_dict(r) for r in recs[:6]],"events":event_feed(db,company.id)}

def rec_dict(r):
    return {"id":r.id,"type":r.recommendation_type,"severity":r.severity,"status":r.status,"title":r.title,"description":r.description,"currency":r.currency,"exposure_amount":str(r.exposure_amount or 0),"hedge_amount":str(r.hedge_amount or 0),"mismatch_amount":str(r.mismatch_amount or 0),"maturity_difference_days":r.maturity_difference_days,"assumptions":r.assumptions or [],"evidence":r.evidence or [],"snapshot_hash":r.snapshot_hash,"created_at":r.created_at.isoformat()}

def event_feed(db,company_id):
    events=db.scalars(select(Event).where(Event.company_id==company_id).order_by(Event.created_at.desc()).limit(8)).all()
    return [{"id":e.id,"type":e.event_type,"entity_type":e.entity_type,"entity_id":e.entity_id,"created_at":e.created_at.isoformat()} for e in events]

def company_or_404(db):
    c=db.scalar(select(Company).order_by(Company.created_at))
    if not c: raise HTTPException(404,"No demo company")
    return c

@app.get("/api/invoices")
def invoices(db: Session=Depends(get_db)):
    c=company_or_404(db); rows=db.scalars(select(Invoice).where(Invoice.company_id==c.id).order_by(Invoice.due_date)).all()
    return [{"id":x.id,"invoice_number":x.invoice_number,"customer":x.customer,"currency":x.currency,"direction":x.direction,"original_amount":str(x.original_amount),"outstanding_amount":str(x.outstanding_amount),"due_date":x.due_date.isoformat(),"status":x.status,"legal_entity":x.legal_entity} for x in rows]

@app.get("/api/hedges")
def hedges(db: Session=Depends(get_db)):
    c=company_or_404(db); rows=db.scalars(select(Hedge).where(Hedge.company_id==c.id)).all()
    return [{"id":x.id,"contract_number":x.contract_number,"currency_pair":x.currency_pair,"direction":x.direction,"notional_amount":str(x.notional_amount),"remaining_amount":str(x.remaining_amount),"contract_rate":str(x.contract_rate),"maturity_date":x.maturity_date.isoformat(),"status":x.status} for x in rows]

@app.get("/api/recommendations")
def recommendations(db: Session=Depends(get_db)):
    c=company_or_404(db); rows=db.scalars(select(Recommendation).where(Recommendation.company_id==c.id).order_by(Recommendation.created_at.desc())).all()
    return [rec_dict(x) for x in rows]

@app.get("/api/shadow-balances")
def shadow_balances(db: Session=Depends(get_db)):
    c=company_or_404(db)
    balances=db.scalars(select(CashBalance).where(CashBalance.company_id==c.id).order_by(CashBalance.currency, CashBalance.legal_entity)).all()
    payments=db.scalars(select(Payment).where(Payment.company_id==c.id).order_by(Payment.payment_date.desc())).all()
    invoices={x.id:x for x in db.scalars(select(Invoice).where(Invoice.company_id==c.id)).all()}
    return {
        "cash_snapshots":[{"id":b.id,"legal_entity":b.legal_entity,"currency":b.currency,"balance":str(b.balance),"available_balance":str(b.available_balance),"as_of":b.as_of.isoformat()} for b in balances],
        "settlement_ledger":[{"id":p.id,"source_record_id":p.source_record_id,"invoice_number":invoices[p.invoice_id].invoice_number if p.invoice_id in invoices else "Unknown invoice","invoice_id":p.invoice_id,"amount":str(p.amount),"currency":p.currency,"payment_date":p.payment_date.isoformat(),"treatment":p.treatment,"destination_currency":p.destination_currency,"conversion_rate":str(p.conversion_rate) if p.conversion_rate is not None else None,"classification":"FOREIGN_CURRENCY_CASH" if p.treatment=="RETAINED" else ("CONVERTED_OUT" if p.treatment=="CONVERTED" and p.destination_currency=="INR" else ("FOREIGN_CURRENCY_CASH_AFTER_CONVERSION" if p.treatment=="CONVERTED" and p.destination_currency not in {"",p.currency,"INR"} and p.conversion_rate is not None and p.conversion_rate>0 else ("UNRESOLVED" if p.treatment=="UNKNOWN" else "CROSS_CURRENCY_REVIEW")))} for p in payments],
        "controls":{"cash_snapshots_are_point_in_time":True,"payment_ledger_is_not_added_to_cash_snapshots":True,"unknown_treatment_requires_review":True,"cross_currency_conversion_requires_rate_and_bank_evidence":True},
        "warning":"Cash snapshots and payment movements are shown separately to avoid double counting. Retained foreign-currency receipts remain FX assets. A conversion into a different foreign currency is carried into the destination-currency cash exposure only when a positive destination-units-per-source-unit conversion rate is recorded. Converted INR receipts leave the foreign-currency exposure. Unknown or unsupported cross-currency treatment needs source evidence before classification."
    }

@app.post("/api/reconcile")
def run_reconcile(db: Session=Depends(get_db)):
    c=company_or_404(db); rows=reconcile(db,c.id); db.commit()
    return {"created":len(rows),"recommendations":[rec_dict(x) for x in rows]}

@app.post("/api/events")
def create_event(data: EventIn, request: Request, db: Session=Depends(get_db)):
    c=company_or_404(db)
    existing=db.scalar(select(Event).where(Event.company_id==c.id,Event.idempotency_key==data.idempotency_key))
    if existing: return {"event_id":existing.id,"duplicate":True,"recommendations":[]}
    if data.event_type in {"DUE_DATE_CHANGED","INVOICE_AMENDED","INVOICE_CANCELLED"}:
        source=db.get(Invoice,data.entity_id)
    elif data.event_type=="PAYMENT_TREATMENT_UPDATED":
        source=db.get(Payment,data.entity_id)
    else:
        source=db.get(PipelineDeal,data.entity_id)
    if not source or source.company_id!=c.id:
        raise HTTPException(404,"The source record for this event was not found in the current demo company")
    ev=Event(company_id=c.id,event_type=data.event_type,entity_type=data.entity_type,entity_id=data.entity_id,idempotency_key=data.idempotency_key,payload=data.payload)
    db.add(ev); db.flush(); created=process_event(db,c.id,ev)
    db.add(AuditLog(company_id=c.id,actor=request.state.user["email"],event_type=f"EVENT_INGESTED_{data.event_type}",entity_type=data.entity_type,entity_id=data.entity_id,details={"event_id":ev.id,"idempotency_key":data.idempotency_key,"payload":data.payload}))
    db.commit()
    return {"event_id":ev.id,"duplicate":False,"recommendations":[rec_dict(x) for x in created]}

@app.post("/api/payments")
def record_payment(data: PaymentIn, db: Session=Depends(get_db)):
    c=company_or_404(db); inv=db.get(Invoice,data.invoice_id)
    if not inv or inv.company_id!=c.id: raise HTTPException(404,"Invoice not found")
    if inv.direction!="RECEIVABLE": raise HTTPException(400,"This demo payment workflow records incoming customer receipts. Select a receivable invoice.")
    if data.amount>D(inv.outstanding_amount): raise HTTPException(400,"Payment exceeds invoice outstanding amount")
    payment=Payment(company_id=c.id,invoice_id=inv.id,source_record_id=data.source_record_id,amount=data.amount,currency=inv.currency,payment_date=data.payment_date,treatment=data.treatment,destination_currency=data.destination_currency,conversion_rate=data.conversion_rate)
    inv.outstanding_amount=D(inv.outstanding_amount)-data.amount; inv.version+=1
    if inv.outstanding_amount==0: inv.status="SETTLED"
    db.add(payment); db.flush()
    ev=Event(company_id=c.id,event_type="PAYMENT_RECEIVED",entity_type="payment",entity_id=payment.id,idempotency_key=f"payment:{payment.id}",payload={"invoice_id":inv.id,"treatment":data.treatment})
    db.add(ev); db.flush()
    created=reconcile(db,c.id,ev.id)
    db.add(AuditLog(company_id=c.id,actor="demo-user",event_type="PAYMENT_RECORDED",entity_type="payment",entity_id=payment.id,details={"invoice":inv.invoice_number,"amount":str(data.amount),"treatment":data.treatment}))
    db.commit()
    return {"payment_id":payment.id,"remaining_invoice_amount":str(inv.outstanding_amount),"treatment":data.treatment,"recommendations_created":[rec_dict(x) for x in created]}

@app.post("/api/recommendations/{recommendation_id}/proposals")
def create_proposal(recommendation_id: str, data: ProposalIn, request: Request, db: Session=Depends(get_db)):
    if request.state.user["role"] != "maker": raise HTTPException(403,"Only the maker role can prepare proposals")
    rec=db.get(Recommendation,recommendation_id)
    if not rec: raise HTTPException(404,"Recommendation not found")
    if rec.status not in ["PENDING_REVIEW","UNDER_REVIEW","ACTION_PROPOSED"]: raise HTTPException(409,"Recommendation is not actionable")
    proposal=Proposal(recommendation_id=rec.id,action_type=data.action_type,description=data.description,proposed_amount=data.proposed_amount,currency=data.currency,rationale=data.rationale,status="DRAFT",created_by=request.state.user["email"],snapshot_hash=snapshot_hash(db,rec.company_id))
    db.add(proposal); db.flush(); rec.status="ACTION_PROPOSED"
    db.add(AuditLog(company_id=rec.company_id,actor=request.state.user["email"],event_type="PROPOSAL_CREATED",entity_type="proposal",entity_id=proposal.id,details={"recommendation_id":rec.id,"action_type":data.action_type}))
    db.commit(); db.refresh(proposal)
    return {"proposal_id":proposal.id,"status":proposal.status,"snapshot_hash":proposal.snapshot_hash}

@app.post("/api/proposals/{proposal_id}/request-approval")
def request_approval(proposal_id: str, request: Request, db: Session=Depends(get_db)):
    if request.state.user["role"] != "maker": raise HTTPException(403,"Only the maker role can submit proposals for approval")
    p=db.get(Proposal,proposal_id)
    if not p: raise HTTPException(404,"Proposal not found")
    if p.status!="DRAFT": raise HTTPException(409,"Proposal must be draft")
    if p.created_by != request.state.user["email"]: raise HTTPException(403,"Only the proposal's maker can submit it")
    a=Approval(proposal_id=p.id,requested_by=p.created_by,assigned_to="checker",approved_snapshot_hash=p.snapshot_hash)
    p.status="PENDING_APPROVAL"; db.add(a); db.flush()
    rec=db.get(Recommendation,p.recommendation_id)
    db.add(AuditLog(company_id=rec.company_id,actor=p.created_by,event_type="APPROVAL_REQUESTED",entity_type="approval",entity_id=a.id,details={"proposal_id":p.id}))
    db.commit(); return {"approval_id":a.id,"status":a.status}

@app.get("/api/approvals/pending")
def pending_approvals(db: Session=Depends(get_db)):
    rows=db.scalars(select(Approval).where(Approval.status=="PENDING")).all(); out=[]
    for a in rows:
        p=db.get(Proposal,a.proposal_id); r=db.get(Recommendation,p.recommendation_id)
        out.append({"id":a.id,"proposal_id":p.id,"recommendation_id":r.id,"title":r.title,"description":p.description,"action_type":p.action_type,"proposed_amount":str(p.proposed_amount or ""),"currency":p.currency,"rationale":p.rationale,"requested_by":a.requested_by,"snapshot_hash":a.approved_snapshot_hash})
    return out

@app.post("/api/approvals/{approval_id}/decision")
def approval_decision(approval_id: str, data: ApprovalDecisionIn, request: Request, db: Session=Depends(get_db)):
    if request.state.user["role"] != "checker": raise HTTPException(403,"Only the checker role can decide approvals")
    a=db.get(Approval,approval_id)
    if not a: raise HTTPException(404,"Approval not found")
    p=db.get(Proposal,a.proposal_id); rec=db.get(Recommendation,p.recommendation_id)
    if a.status!="PENDING": raise HTTPException(409,"Approval is no longer pending")
    if a.requested_by == request.state.user["email"]: raise HTTPException(403,"Maker-checker separation failed: the checker cannot approve their own proposal")
    if data.expected_snapshot_hash!=a.approved_snapshot_hash or snapshot_hash(db,rec.company_id)!=a.approved_snapshot_hash:
        a.status="STALE"; p.status="STALE"; rec.status="SUPERSEDED"
        db.add(AuditLog(company_id=rec.company_id,actor=request.state.user["email"],event_type="APPROVAL_BLOCKED_STALE",entity_type="approval",entity_id=a.id,details={"expected":a.approved_snapshot_hash,"current":snapshot_hash(db,rec.company_id)}))
        db.commit(); raise HTTPException(409,"Underlying data changed. Recalculate and create a fresh proposal.")
    if data.decision!="APPROVE" and not data.comment.strip(): raise HTTPException(400,"A reason is required for rejection or requested changes")
    required=["underlying_exposure_verified","payment_treatment_verified","hedge_status_verified","maturity_reviewed"]
    if data.decision=="APPROVE" and not all(data.confirmations.get(k) is True for k in required): raise HTTPException(400,"Complete all four verification confirmations before approval")
    a.status={"APPROVE":"APPROVED","REJECT":"REJECTED","REQUEST_CHANGES":"CHANGES_REQUESTED"}[data.decision]
    p.status={"APPROVE":"APPROVED_NOT_EXECUTED","REJECT":"REJECTED","REQUEST_CHANGES":"CHANGES_REQUESTED"}[data.decision]
    if data.decision=="APPROVE": rec.status="APPROVED"
    elif data.decision=="REJECT": rec.status="REJECTED"
    a.decision_reason=data.comment; a.decided_at=datetime.now(timezone.utc)
    db.add(AuditLog(company_id=rec.company_id,actor=request.state.user["email"],event_type=f"APPROVAL_{data.decision}",entity_type="approval",entity_id=a.id,details={"comment":data.comment,"proposal_id":p.id}))
    db.commit(); return {"approval_id":a.id,"approval_status":a.status,"proposal_status":p.status,"message":"Approved internally only; no external trade was executed." if data.decision=="APPROVE" else "Decision recorded."}

@app.post("/api/proposals/{proposal_id}/simulate")
def simulate_proposal(proposal_id: str, request: Request, db: Session=Depends(get_db)):
    if request.state.user["role"] != "checker": raise HTTPException(403,"Only the checker role can run the approved-action simulation")
    p=db.get(Proposal,proposal_id)
    if not p: raise HTTPException(404,"Proposal not found")
    if p.status!="APPROVED_NOT_EXECUTED": raise HTTPException(409,"Only internally approved proposals can be simulated")
    rec=db.get(Recommendation,p.recommendation_id)
    if snapshot_hash(db,rec.company_id)!=p.snapshot_hash: raise HTTPException(409,"Proposal is stale; refresh before simulation")
    # Demo-only simulation: no real contract is modified and no external API is called.
    p.status="SIMULATED"; rec.status="COMPLETED"
    db.add(AuditLog(company_id=rec.company_id,actor="simulation-adapter",event_type="SIMULATED_ACTION",entity_type="proposal",entity_id=p.id,details={"action_type":p.action_type,"amount":str(p.proposed_amount or ""),"note":"No real derivative execution."}))
    db.commit(); return {"status":"SIMULATED","message":"Demo action simulated. No bank or broker order was placed."}

@app.get("/api/audit")
def audit(db: Session=Depends(get_db)):
    c=company_or_404(db); rows=db.scalars(select(AuditLog).where(AuditLog.company_id==c.id).order_by(AuditLog.created_at.desc()).limit(100)).all()
    return [{"id":x.id,"actor":x.actor,"event_type":x.event_type,"entity_type":x.entity_type,"entity_id":x.entity_id,"details":x.details,"created_at":x.created_at.isoformat()} for x in rows]

def pipeline_exposure(row: PipelineDeal):
    stage=row.stage.upper()
    if stage in {"CONTRACT_SIGNED","WON"}:
        factor=D("1"); mode="FIRM_PRE_INVOICE"
    elif stage in {"LOST","CANCELLED"}:
        factor=D("0"); mode="EXCLUDED_LOST"
    else:
        factor=D(row.probability); mode="PROBABILITY_WEIGHTED_FORECAST"
    return money(D(row.amount)*factor), factor, mode

@app.get("/api/pipeline")
def pipeline(db: Session=Depends(get_db)):
    c=company_or_404(db); rows=db.scalars(select(PipelineDeal).where(PipelineDeal.company_id==c.id)).all()
    out=[]
    for x in rows:
        weighted,factor,mode=pipeline_exposure(x)
        out.append({"id":x.id,"deal_name":x.deal_name,"customer":x.customer,"currency":x.currency,"amount":str(x.amount),"probability":str(x.probability),"effective_probability":str(factor),"risk_weighted_amount":str(weighted),"exposure_mode":mode,"expected_close_date":x.expected_close_date.isoformat(),"expected_payment_date":x.expected_payment_date.isoformat(),"stage":x.stage})
    return out

@app.post("/api/pipeline")
def add_pipeline(data: PipelineDealIn, db: Session=Depends(get_db)):
    c=company_or_404(db); row=PipelineDeal(company_id=c.id,**data.model_dump()); db.add(row); db.commit(); db.refresh(row)
    weighted,factor,mode=pipeline_exposure(row)
    return {"id":row.id,"risk_weighted_amount":str(weighted),"exposure_mode":mode,"effective_probability":str(factor),"note":"Pipeline scenario only; it remains pre-invoice and is not an accounting receivable or an automatic hedge instruction."}

@app.post("/api/netting/calculate")
def netting(db: Session=Depends(get_db)):
    c=company_or_404(db); rows=db.scalars(select(IntercompanyPosition).where(IntercompanyPosition.company_id==c.id)).all()
    groups={}
    for x in rows:
        # net only reciprocal entity pair, same currency and compatible due-date window <= 7 days
        pair=tuple(sorted([x.entity_name,x.counterparty_entity])); key=(pair,x.currency)
        groups.setdefault(key,[]).append(x)
    results=[]
    for (pair,currency),items in groups.items():
        recv=sum((D(x.amount) for x in items if x.direction=="RECEIVABLE"),D(0)); pay=sum((D(x.amount) for x in items if x.direction=="PAYABLE"),D(0))
        dates=[x.due_date for x in items]
        reciprocal_present=any(
            recv_item.direction=="RECEIVABLE" and pay_item.direction=="PAYABLE"
            and recv_item.entity_name==pay_item.counterparty_entity
            and recv_item.counterparty_entity==pay_item.entity_name
            for recv_item in items for pay_item in items
        )
        timing_compatible=bool(dates) and (max(dates)-min(dates)).days<=7
        compatible=(len(items)>1 and reciprocal_present and timing_compatible)
        results.append({"entities":pair,"currency":currency,"gross_receivables":str(money(recv)),"gross_payables":str(money(pay)),"illustrative_net":str(money(recv-pay)) if compatible else None,"compatible_for_demo_netting":compatible,"reciprocal_positions_present":reciprocal_present,"timing_compatible":timing_compatible,"warning":"Illustrative economic netting only; reciprocal records and a seven-day demo timing window are required. Legal enforceability, settlement agreements, tax and jurisdictional rules are not assessed."})
    return results

@app.post("/api/liquidity/stress")
def liquidity_stress(data: LiquidityStressIn):
    fx_factor=D(1)+D(data.fx_shock_pct)/D(100)
    if fx_factor < 0:
        raise HTTPException(400,"FX shock cannot reduce the receipt value below zero")
    cash=D(data.cash_inr); receipts=D(data.expected_receipts_inr)*fx_factor; payments=D(data.expected_payments_inr); margin=D(data.margin_call_inr)
    line_limit=D(data.credit_line_limit_inr); line_drawn=D(data.credit_line_drawn_inr)
    before=cash+receipts-payments; after=before-margin
    undrawn=max(D(0),line_limit-line_drawn)
    over_limit=max(D(0),line_drawn-line_limit)
    liquidity_after_line=after+undrawn
    utilisation=(line_drawn/line_limit*D(100)) if line_limit>0 else (D(100) if line_drawn>0 else D(0))
    return {
        "stressed_receipts_inr":str(money(receipts)),
        "cash_before_margin_inr":str(money(before)),
        "margin_call_inr":str(money(margin)),
        "cash_after_margin_inr":str(money(after)),
        "liquidity_shortfall_inr":str(money(max(D(0),-after))),
        "credit_line_limit_inr":str(money(line_limit)),
        "credit_line_drawn_inr":str(money(line_drawn)),
        "undrawn_credit_capacity_inr":str(money(undrawn)),
        "credit_line_utilisation_pct":str(money(utilisation)),
        "credit_line_over_limit_inr":str(money(over_limit)),
        "liquidity_after_available_credit_inr":str(money(liquidity_after_line)),
        "shortfall_after_available_credit_inr":str(money(max(D(0),-liquidity_after_line))),
        "warning":"Simplified stress scenario. Undrawn credit is assumed available only for illustration; actual facility covenants, draw conditions, derivative margin, collateral eligibility, netting sets and bank terms are not modelled."
    }

@app.post("/api/working-capital/compare")
def working_capital(data: WorkingCapitalIn):
    amount=D(data.invoice_amount); spot=D(data.spot_rate); fwd=D(data.forward_rate); days=max(0,data.days_to_payment)
    hedge_value=amount*fwd
    spot_value=amount*spot
    discount_cost=spot_value*D(data.early_discount_pct)/100
    financing_cost=spot_value*D(data.financing_annual_pct)/100*D(days)/365
    return {"indicative_forward_inr":str(money(hedge_value)),"spot_reference_inr":str(money(spot_value)),"early_discount_cost_inr":str(money(discount_cost)),"financing_cost_inr":str(money(financing_cost)),"note":"Illustrative comparison only. Forward points, fees, tax, credit terms, customer behaviour and accounting impacts are excluded."}

@app.post("/api/accounting/draft")
def accounting_draft(hedge_id: str=Query(...), framework: str=Query("Ind AS 109"), db: Session=Depends(get_db)):
    c=company_or_404(db); h=db.get(Hedge,hedge_id)
    if not h or h.company_id!=c.id: raise HTTPException(404,"Hedge not found")
    memo=(f"DRAFT FOR PROFESSIONAL REVIEW — {framework}\n\nInstrument: {h.contract_number} ({h.currency_pair}, {h.direction})\nNotional remaining: {h.remaining_amount} {h.currency_pair.split('/')[0]}\nContract rate: {h.contract_rate}\nMaturity: {h.maturity_date}\n\nThis draft is not a hedge-accounting designation or compliance conclusion. A qualified accountant must assess documented risk-management objective and strategy, eligible hedged item/instrument, economic relationship, credit risk, hedge ratio, effectiveness requirements, designation date, fair value evidence, disclosures and applicable local standards. No journal entry has been generated because valuation and designation evidence are not supplied.")
    row=AccountingDraft(company_id=c.id,hedge_id=h.id,framework=framework,memo=memo); db.add(row); db.commit(); db.refresh(row)
    db.add(AuditLog(company_id=c.id, actor="accounting-copilot", event_type="ACCOUNTING_MEMO_GENERATED", entity_type="accounting_draft", entity_id=row.id, details={"framework":framework,"hedge_contract":h.contract_number,"status":"DRAFT_FOR_REVIEW"}))
    db.commit()
    return {"id":row.id,"status":row.status,"framework":framework,"memo":memo,"download_url":f"/api/accounting/drafts/{row.id}/download"}

@app.get("/api/accounting/drafts/{draft_id}/download")
def download_accounting_draft(draft_id: str, db: Session=Depends(get_db)):
    c=company_or_404(db); row=db.get(AccountingDraft,draft_id)
    if not row or row.company_id!=c.id: raise HTTPException(404,"Accounting draft not found")
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
    from xml.sax.saxutils import escape
    buffer=BytesIO(); doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=48,leftMargin=48,topMargin=48,bottomMargin=48)
    styles=getSampleStyleSheet(); styles.add(ParagraphStyle(name="MemoTitle",parent=styles["Title"],alignment=TA_CENTER,textColor=colors.HexColor("#243b63"),fontSize=17,leading=22,spaceAfter=18))
    styles.add(ParagraphStyle(name="MemoBody",parent=styles["BodyText"],fontSize=9.5,leading=14,spaceAfter=8))
    story=[Paragraph("FXNEXUS — HEDGE ACCOUNTING DRAFT",styles["MemoTitle"]),Paragraph("DRAFT FOR PROFESSIONAL REVIEW · NOT A COMPLIANCE OPINION",styles["Heading2"]),Spacer(1,10)]
    for block in row.memo.split("\n\n"):
        if block.strip():
            lines=block.splitlines(); story.append(KeepTogether([Paragraph(escape(lines[0]),styles["Heading3"] if len(lines[0])<70 and not lines[0].startswith("This draft") else styles["MemoBody"])]))
            for line in lines[1:]: story.append(Paragraph(escape(line),styles["MemoBody"]))
    story += [Spacer(1,18),Paragraph("Generated by FXNexus prototype. Verify all source records, designation evidence, valuation inputs and applicable accounting requirements with a qualified professional.",styles["Italic"])]
    doc.build(story); buffer.seek(0)
    filename=f"FXNexus_{row.framework.replace(' ','_')}_Hedge_Accounting_Draft.pdf"
    return Response(content=buffer.getvalue(),media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{filename}"'})

@app.post("/api/scenarios/run")
def run_scenario(data: ScenarioIn, db: Session=Depends(get_db)):
    c=company_or_404(db); invoices=db.scalars(select(Invoice).where(Invoice.company_id==c.id,Invoice.status=="OPEN")).all()
    original=sum((D(x.outstanding_amount) for x in invoices if x.currency=="USD" and x.direction=="RECEIVABLE"),D(0))
    stressed=original*(D(1)-D(data.invoice_reduction_pct)/100)
    rate=D("86")*(D(1)+D(data.usd_inr_change_pct)/100)
    return {"base_usd_receivables":str(money(original)),"stressed_usd_receivables":str(money(stressed)),"reference_rate":str(money(rate)),"base_inr_value":str(money(original*D("86"))),"stressed_inr_value":str(money(stressed*rate)),"payment_delay_days":data.payment_delay_days,"note":"Scenario is illustrative and uses a demo base rate of INR 86/USD. Delay affects timing/liquidity, not the invoice notional."}

@app.get("/api/integrations/status")
def integration_status():
    return {"zoho_credentials_configured":bool(settings.zoho_client_id and settings.zoho_client_secret and settings.zoho_refresh_token),"zoho_organization_selected":bool(settings.zoho_organization_id),"zoho_configured":bool(settings.zoho_client_id and settings.zoho_client_secret and settings.zoho_refresh_token and settings.zoho_organization_id),"twelve_data_configured":bool(settings.twelve_data_api_key),"openai_configured":bool(settings.openai_api_key),"execution":"SIMULATION_ONLY"}

@app.get("/api/integrations/zoho/test")
async def zoho_test():
    try:
        org_response=await fetch_zoho_organizations()
        orgs=org_response.get("organizations", [])
        result={"status":"AUTHENTICATED","organization_count":len(orgs),"organizations":[{"organization_id":x.get("organization_id"),"name":x.get("name"),"currency_code":x.get("currency_code"),"is_default_org":x.get("is_default_org")} for x in orgs]}
        if not settings.zoho_organization_id:
            result["next_step"]="Choose an organization and set ZOHO_ORGANIZATION_ID in backend/.env to test invoice and payment retrieval."
            return result
        invoices=await fetch_zoho_invoices(); payments=await fetch_zoho_customer_payments()
        result.update({"status":"CONNECTED_READ_ONLY","invoice_count":len(invoices.get("invoices",[])),"payment_count":len(payments.get("customerpayments",[]))})
        return result
    except IntegrationNotConfigured as e: raise HTTPException(400,str(e))
    except Exception as e:
        # Avoid echoing credentials or full provider request URLs into the UI.
        detail=str(e)
        raise HTTPException(502,f"Zoho connection test failed: {detail[:240]}")

@app.get("/api/integrations/zoho/invoices")
async def zoho_invoices():
    try: return await fetch_zoho_invoices()
    except IntegrationNotConfigured as e: raise HTTPException(400,str(e))
    except Exception as e: raise HTTPException(502,f"Zoho request failed: {e}")

@app.get("/api/integrations/zoho/payments")
async def zoho_payments():
    try: return await fetch_zoho_customer_payments()
    except IntegrationNotConfigured as e: raise HTTPException(400,str(e))
    except Exception as e: raise HTTPException(502,f"Zoho request failed: {e}")

@app.get("/api/integrations/fx-rate")
async def fx_rate(symbol: str="USD/INR"):
    try: return await fetch_twelve_data_rate(symbol)
    except IntegrationNotConfigured as e: raise HTTPException(400,str(e))
    except Exception as e: raise HTTPException(502,f"FX rate provider failed: {e}")
