from sqlalchemy import String, Date, DateTime, Boolean, ForeignKey, Numeric, Text, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date, timezone
from decimal import Decimal
import uuid
from .db import Base

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)

class Company(Base):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160))
    base_currency: Mapped[str] = mapped_column(String(3), default="INR")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(180), unique=True)
    role: Mapped[str] = mapped_column(String(40), default="reviewer")

class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    source_system: Mapped[str] = mapped_column(String(40), default="demo")
    source_record_id: Mapped[str] = mapped_column(String(100), default="")
    invoice_number: Mapped[str] = mapped_column(String(80), index=True)
    customer: Mapped[str] = mapped_column(String(160), default="")
    legal_entity: Mapped[str] = mapped_column(String(100), default="Main entity")
    currency: Mapped[str] = mapped_column(String(3))
    direction: Mapped[str] = mapped_column(String(12), default="RECEIVABLE")
    original_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    outstanding_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(24), default="OPEN")
    version: Mapped[int] = mapped_column(Integer, default=1)

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    source_record_id: Mapped[str] = mapped_column(String(100), default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3))
    payment_date: Mapped[date] = mapped_column(Date)
    treatment: Mapped[str] = mapped_column(String(24), default="UNKNOWN") # CONVERTED, RETAINED, UNKNOWN
    destination_currency: Mapped[str] = mapped_column(String(3), default="")
    conversion_rate: Mapped[Decimal | None] = mapped_column(Numeric(19, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="POSTED")

class Hedge(Base):
    __tablename__ = "hedges"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    source_system: Mapped[str] = mapped_column(String(40), default="manual")
    contract_number: Mapped[str] = mapped_column(String(80), unique=True)
    currency_pair: Mapped[str] = mapped_column(String(7))
    direction: Mapped[str] = mapped_column(String(16)) # SELL_BASE / BUY_BASE
    notional_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    contract_rate: Mapped[Decimal] = mapped_column(Numeric(19, 6))
    maturity_date: Mapped[date] = mapped_column(Date)
    legal_entity: Mapped[str] = mapped_column(String(100), default="Main entity")
    status: Mapped[str] = mapped_column(String(24), default="OPEN")
    version: Mapped[int] = mapped_column(Integer, default=1)

class Event(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("company_id", "idempotency_key", name="uq_event_idempotency"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(80))
    idempotency_key: Mapped[str] = mapped_column(String(160))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    recommendation_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(30), default="PENDING_REVIEW")
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    exposure_amount: Mapped[Decimal | None] = mapped_column(Numeric(19,4), nullable=True)
    hedge_amount: Mapped[Decimal | None] = mapped_column(Numeric(19,4), nullable=True)
    mismatch_amount: Mapped[Decimal | None] = mapped_column(Numeric(19,4), nullable=True)
    maturity_difference_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trigger_event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    calculation_run_id: Mapped[str] = mapped_column(String(80), default="")
    snapshot_hash: Mapped[str] = mapped_column(String(64), default="")
    assumptions: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Proposal(Base):
    __tablename__ = "proposals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    recommendation_id: Mapped[str] = mapped_column(ForeignKey("recommendations.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(Text)
    proposed_amount: Mapped[Decimal | None] = mapped_column(Numeric(19,4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    rationale: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    created_by: Mapped[str] = mapped_column(String(80))
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("proposals.id"), index=True)
    requested_by: Mapped[str] = mapped_column(String(80))
    assigned_to: Mapped[str] = mapped_column(String(80), default="checker")
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    decision_reason: Mapped[str] = mapped_column(Text, default="")
    approved_snapshot_hash: Mapped[str] = mapped_column(String(64))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    actor: Mapped[str] = mapped_column(String(100), default="system")
    event_type: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class PipelineDeal(Base):
    __tablename__ = "pipeline_deals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    deal_name: Mapped[str] = mapped_column(String(160))
    customer: Mapped[str] = mapped_column(String(160))
    currency: Mapped[str] = mapped_column(String(3))
    amount: Mapped[Decimal] = mapped_column(Numeric(19,4))
    probability: Mapped[Decimal] = mapped_column(Numeric(6,4))
    expected_close_date: Mapped[date] = mapped_column(Date)
    expected_payment_date: Mapped[date] = mapped_column(Date)
    stage: Mapped[str] = mapped_column(String(40), default="PROPOSAL")

class IntercompanyPosition(Base):
    __tablename__ = "intercompany_positions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    entity_name: Mapped[str] = mapped_column(String(100))
    counterparty_entity: Mapped[str] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3))
    direction: Mapped[str] = mapped_column(String(16))
    amount: Mapped[Decimal] = mapped_column(Numeric(19,4))
    due_date: Mapped[date] = mapped_column(Date)

class CashBalance(Base):
    __tablename__ = "cash_balances"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    legal_entity: Mapped[str] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3))
    balance: Mapped[Decimal] = mapped_column(Numeric(19,4))
    available_balance: Mapped[Decimal] = mapped_column(Numeric(19,4))
    as_of: Mapped[date] = mapped_column(Date)

class AccountingDraft(Base):
    __tablename__ = "accounting_drafts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    hedge_id: Mapped[str] = mapped_column(String(80))
    framework: Mapped[str] = mapped_column(String(30))
    memo: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT_FOR_REVIEW")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
