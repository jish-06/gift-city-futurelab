from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from hashlib import sha256
import json, uuid
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Invoice, Hedge, Payment, Recommendation, AuditLog, Event, PipelineDeal

D = Decimal

def money(x): return D(str(x)).quantize(D("0.01"), rounding=ROUND_HALF_UP)

def snapshot_hash(db: Session, company_id: str) -> str:
    invoices = db.scalars(select(Invoice).where(Invoice.company_id==company_id).order_by(Invoice.id)).all()
    hedges = db.scalars(select(Hedge).where(Hedge.company_id==company_id).order_by(Hedge.id)).all()
    payments = db.scalars(select(Payment).where(Payment.company_id==company_id).order_by(Payment.id)).all()
    payload = {
        "invoices": [(i.id, str(i.outstanding_amount), i.due_date.isoformat(), i.status, i.version) for i in invoices],
        "hedges": [(h.id, str(h.remaining_amount), h.maturity_date.isoformat(), h.status, h.version) for h in hedges],
        "payments": [(p.id, str(p.amount), p.treatment, p.destination_currency, str(p.conversion_rate) if p.conversion_rate is not None else None, p.status) for p in payments]
    }
    return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

def calculate_exposures(db: Session, company_id: str):
    invoices = db.scalars(select(Invoice).where(Invoice.company_id==company_id, Invoice.status=="OPEN")).all()
    all_invoices = {x.id: x for x in db.scalars(select(Invoice).where(Invoice.company_id==company_id)).all()}
    payments = db.scalars(select(Payment).where(Payment.company_id==company_id)).all()
    totals = {}
    for inv in invoices:
        key = (inv.currency, inv.direction)
        totals[key] = totals.get(key, D("0")) + D(inv.outstanding_amount)
    # Received foreign currency is an asset exposure, not an outstanding invoice.
    # Keep it as a separate direction so dashboard totals don't hide the cash leg.
    for payment in payments:
        invoice = all_invoices.get(payment.invoice_id)
        if not invoice or invoice.direction != "RECEIVABLE":
            continue
        if payment.treatment == "RETAINED":
            key = (payment.currency, "ASSET_CASH")
            totals[key] = totals.get(key, D("0")) + D(payment.amount)
        elif (payment.treatment == "CONVERTED" and payment.destination_currency not in {"", "INR", payment.currency}
              and payment.conversion_rate is not None and D(payment.conversion_rate) > 0):
            key = (payment.destination_currency, "ASSET_CASH")
            totals[key] = totals.get(key, D("0")) + D(payment.amount) * D(payment.conversion_rate)
    return [{"currency": c, "direction": d, "amount": str(money(a))} for (c,d),a in sorted(totals.items())]

def reconcile(db: Session, company_id: str, trigger_event_id=None):
    invoices = db.scalars(select(Invoice).where(Invoice.company_id==company_id, Invoice.status=="OPEN")).all()
    all_invoices = db.scalars(select(Invoice).where(Invoice.company_id==company_id)).all()
    invoice_by_id = {x.id: x for x in all_invoices}
    payments = db.scalars(select(Payment).where(Payment.company_id==company_id)).all()
    hedges = db.scalars(select(Hedge).where(Hedge.company_id==company_id, Hedge.status=="OPEN")).all()
    current_hash = snapshot_hash(db, company_id)
    findings=[]
    # MVP allocation matches currency, instrument direction and legal entity.
    # Incoming foreign-currency cash remains an asset even after its invoice is settled.
    for hedge in hedges:
        base = hedge.currency_pair.split("/")[0]
        compatible = [i for i in invoices if i.currency==base and i.legal_entity==hedge.legal_entity and ((i.direction=="RECEIVABLE" and hedge.direction=="SELL_BASE") or (i.direction=="PAYABLE" and hedge.direction=="BUY_BASE"))]
        exposure = sum((D(i.outstanding_amount) for i in compatible), D("0"))
        relevant_invoice_ids = {i.id for i in all_invoices if i.legal_entity==hedge.legal_entity and (
            (i.direction=="RECEIVABLE" and hedge.direction=="SELL_BASE") or
            (i.direction=="PAYABLE" and hedge.direction=="BUY_BASE")
        )}
        retained_payments = [p for p in payments if p.invoice_id in relevant_invoice_ids and p.currency==base and p.treatment=="RETAINED"]
        converted_cash_payments = [p for p in payments if p.invoice_id in relevant_invoice_ids and p.treatment=="CONVERTED"
            and p.destination_currency==base and p.currency!=base and p.conversion_rate is not None and D(p.conversion_rate)>0
            and invoice_by_id.get(p.invoice_id) is not None and invoice_by_id[p.invoice_id].direction=="RECEIVABLE" and hedge.direction=="SELL_BASE"]
        retained_cash = sum((D(p.amount) for p in retained_payments), D("0"))
        converted_cash = sum((D(p.amount)*D(p.conversion_rate) for p in converted_cash_payments), D("0"))
        exposure += retained_cash + converted_cash
        h_amt = D(hedge.remaining_amount)
        mismatch = h_amt - exposure
        linked_ids = {i.id for i in compatible}
        linked_ids.update(p.invoice_id for p in retained_payments + converted_cash_payments)
        evidence=[{"type":"hedge","id":hedge.id,"record":hedge.contract_number}] + [{"type":"invoice","id":i.id,"record":i.invoice_number} for i in all_invoices if i.id in linked_ids] + [{"type":"payment","id":p.id,"record":p.source_record_id or p.id,"treatment":p.treatment,"destination_currency":p.destination_currency,"conversion_rate":str(p.conversion_rate) if p.conversion_rate is not None else None} for p in retained_payments + converted_cash_payments]
        if mismatch > 0:
            findings.append({"type":"POTENTIAL_OVERHEDGE","severity":"HIGH","title":"Potential over-hedge detected","description":"Open hedge notional exceeds compatible outstanding underlying exposure. Verify cash treatment, other eligible exposures and contract terms before acting.","currency":base,"exposure":exposure,"hedge":h_amt,"mismatch":mismatch,"evidence":evidence,"assumptions":["Same legal entity and compatible hedge direction assumed.","Other off-system exposures may not be included.","Hedge eligibility and contractual settlement terms require human verification."]})
        elif mismatch < 0:
            findings.append({"type":"POTENTIAL_UNDERHEDGE","severity":"MEDIUM","title":"Potential under-hedge detected","description":"Compatible underlying exposure exceeds matched open hedge notional. This is an exposure gap, not an instruction to trade.","currency":base,"exposure":exposure,"hedge":h_amt,"mismatch":abs(mismatch),"evidence":evidence,"assumptions":["Same legal entity and compatible hedge direction assumed.","Other eligible hedges may exist outside the imported records."]})
        dates=[i.due_date for i in compatible]
        if dates:
            # conservative: nearest expected date vs hedge maturity; show mismatch for >7 calendar days
            nearest=min(dates, key=lambda x: abs((x-hedge.maturity_date).days))
            delta=(hedge.maturity_date-nearest).days
            if abs(delta)>7:
                findings.append({"type":"MATURITY_MISMATCH","severity":"MEDIUM","title":"Hedge maturity differs from expected cash-flow date","description":"The hedge maturity is outside the illustrative seven-day policy tolerance. Confirm shipment, payment and contract terms.","currency":base,"exposure":exposure,"hedge":h_amt,"mismatch":abs(mismatch),"days":delta,"evidence":evidence,"assumptions":["Seven-day tolerance is a demo policy setting, not a universal standard."]})
    # Do not silently classify an unknown or cross-currency settlement as either
    # converted-away or retained cash. Surface it for an operator to resolve.
    uncertain_payments = db.scalars(select(Payment).where(Payment.company_id==company_id)).all()
    for payment in uncertain_payments:
        converted_to_foreign_is_supported = (
            payment.treatment == "CONVERTED" and payment.destination_currency not in {"", "INR", payment.currency}
            and payment.conversion_rate is not None and D(payment.conversion_rate) > 0
        )
        needs_review = payment.treatment == "UNKNOWN" or (
            payment.treatment == "CONVERTED" and payment.destination_currency != "INR" and not converted_to_foreign_is_supported
        )
        if not needs_review:
            continue
        invoice = db.get(Invoice, payment.invoice_id)
        evidence = [{"type":"payment","id":payment.id,"record":payment.source_record_id or payment.id,"treatment":payment.treatment,"destination_currency":payment.destination_currency},
                    {"type":"invoice","id":invoice.id,"record":invoice.invoice_number}] if invoice else [{"type":"payment","id":payment.id,"record":payment.source_record_id or payment.id,"treatment":payment.treatment}]
        findings.append({"type":"PAYMENT_TREATMENT_REVIEW","severity":"MEDIUM","title":"Payment cash treatment needs reconciliation",
            "description":"The invoice has a linked settlement whose destination or retained-cash treatment is not established. Verify the bank advice, conversion currency and receiving account before treating the source-currency exposure as extinguished.",
            "currency":payment.currency,"exposure":D(payment.amount),"hedge":D("0"),"mismatch":D("0"),"evidence":evidence,
            "assumptions":["No conversion or retained-cash treatment is inferred without source evidence.","Cash snapshots and payment movements must be reconciled without double counting."]})
    # Avoid duplicating same active recommendation on every event; create only if type+evidence signature not already open.
    created=[]
    for f in findings:
        active=db.scalars(select(Recommendation).where(Recommendation.company_id==company_id, Recommendation.recommendation_type==f["type"], Recommendation.status.in_(["PENDING_REVIEW","UNDER_REVIEW","ACTION_PROPOSED"]))).all()
        evidence_ids=sorted(x["id"] for x in f["evidence"])
        same_finding=[a for a in active if sorted(x["id"] for x in (a.evidence or []))==evidence_ids]
        if any(a.snapshot_hash==current_hash for a in same_finding):
            continue
        # The same invoice/hedge IDs can produce a materially different result
        # after a date, payment or amount change. Supersede stale open findings
        # rather than reusing their old snapshot hash in a new approval flow.
        for previous in same_finding:
            previous.status="SUPERSEDED"
        rec=Recommendation(company_id=company_id,recommendation_type=f["type"],severity=f["severity"],title=f["title"],description=f["description"],currency=f["currency"],exposure_amount=f["exposure"],hedge_amount=f["hedge"],mismatch_amount=f["mismatch"],maturity_difference_days=f.get("days"),trigger_event_id=trigger_event_id,calculation_run_id=str(uuid.uuid4()),snapshot_hash=current_hash,assumptions=f["assumptions"],evidence=f["evidence"])
        db.add(rec); db.flush(); created.append(rec)
        db.add(AuditLog(company_id=company_id,actor="system",event_type="RECOMMENDATION_CREATED",entity_type="recommendation",entity_id=rec.id,details={"type":rec.recommendation_type,"snapshot_hash":current_hash}))
    return created

def process_event(db: Session, company_id: str, event: Event):
    if event.processed: return []
    p=event.payload or {}
    if event.event_type in ("DUE_DATE_CHANGED","INVOICE_AMENDED","INVOICE_CANCELLED"):
        inv=db.get(Invoice,event.entity_id)
        if inv:
            if event.event_type=="DUE_DATE_CHANGED" and p.get("due_date"):
                inv.due_date=date.fromisoformat(p["due_date"]); inv.version+=1
            elif event.event_type=="INVOICE_AMENDED" and p.get("outstanding_amount") is not None:
                inv.outstanding_amount=D(str(p["outstanding_amount"])); inv.version+=1
            elif event.event_type=="INVOICE_CANCELLED":
                inv.status="CANCELLED"; inv.outstanding_amount=D("0"); inv.version+=1
    elif event.event_type=="PAYMENT_TREATMENT_UPDATED":
        payment=db.get(Payment,event.entity_id)
        if payment:
            payment.treatment=p.get("treatment","UNKNOWN"); payment.destination_currency=p.get("destination_currency","")
            if p.get("conversion_rate") is not None: payment.conversion_rate=D(str(p["conversion_rate"]))
            db.add(AuditLog(company_id=company_id,actor="event-processor",event_type="PAYMENT_TREATMENT_UPDATED",entity_type="payment",entity_id=payment.id,details={"treatment":payment.treatment,"destination_currency":payment.destination_currency,"conversion_rate":str(payment.conversion_rate) if payment.conversion_rate is not None else None}))
            # Close the active data-quality recommendation only after an operator
            # explicitly records a treatment. The linked event remains auditable.
            treatment_verified = payment.treatment == "RETAINED" or (
                payment.treatment == "CONVERTED" and (
                    payment.destination_currency == "INR" or
                    (payment.destination_currency not in {"", payment.currency} and payment.conversion_rate is not None and D(payment.conversion_rate) > 0)
                )
            )
            if treatment_verified:
                active_reviews=db.scalars(select(Recommendation).where(
                    Recommendation.company_id==company_id,
                    Recommendation.recommendation_type=="PAYMENT_TREATMENT_REVIEW",
                    Recommendation.status.in_(["PENDING_REVIEW","UNDER_REVIEW","ACTION_PROPOSED"])
                )).all()
                for review in active_reviews:
                    if any(item.get("type")=="payment" and item.get("id")==payment.id for item in (review.evidence or [])):
                        review.status="RESOLVED"
                        db.add(AuditLog(company_id=company_id,actor="system",event_type="PAYMENT_TREATMENT_RESOLVED",entity_type="payment",entity_id=payment.id,details={"treatment":payment.treatment,"destination_currency":payment.destination_currency,"recommendation_id":review.id}))
    elif event.event_type=="CRM_DEAL_UPDATED":
        deal=db.get(PipelineDeal,event.entity_id)
        if deal and deal.company_id==company_id:
            if p.get("amount") is not None: deal.amount=D(str(p["amount"]))
            if p.get("probability") is not None: deal.probability=D(str(p["probability"]))
            if p.get("expected_close_date"): deal.expected_close_date=date.fromisoformat(p["expected_close_date"])
            if p.get("expected_payment_date"): deal.expected_payment_date=date.fromisoformat(p["expected_payment_date"])
            if p.get("stage"): deal.stage=str(p["stage"])
            if p.get("deal_name"): deal.deal_name=str(p["deal_name"])
            if p.get("customer"): deal.customer=str(p["customer"])
    event.processed=True
    db.flush()
    return reconcile(db,company_id,event.id)
