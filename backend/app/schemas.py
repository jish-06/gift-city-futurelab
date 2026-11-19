from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

class LoginIn(BaseModel):
    email: str
    password: str

class EventIn(BaseModel):
    event_type: Literal["INVOICE_AMENDED","PAYMENT_TREATMENT_UPDATED","DUE_DATE_CHANGED","INVOICE_CANCELLED","CRM_DEAL_UPDATED"]
    entity_type: str
    entity_id: str
    idempotency_key: str
    payload: dict = Field(default_factory=dict)

class PaymentIn(BaseModel):
    invoice_id: str
    amount: Decimal = Field(gt=0)
    payment_date: date
    treatment: Literal["CONVERTED","RETAINED","UNKNOWN"] = "UNKNOWN"
    destination_currency: str = ""
    conversion_rate: Optional[Decimal] = None
    source_record_id: str = "manual"

class ProposalIn(BaseModel):
    action_type: str = "PREPARE_HEDGE_ADJUSTMENT_FOR_REVIEW"
    description: str
    proposed_amount: Optional[Decimal] = None
    currency: str = "USD"
    rationale: str

class ApprovalDecisionIn(BaseModel):
    decision: Literal["APPROVE","REJECT","REQUEST_CHANGES"]
    comment: str = ""
    expected_snapshot_hash: str
    confirmations: dict = Field(default_factory=dict)

class ScenarioIn(BaseModel):
    usd_inr_change_pct: Decimal = Decimal("0")
    payment_delay_days: int = 0
    invoice_reduction_pct: Decimal = Decimal("0")

class PipelineDealIn(BaseModel):
    deal_name: str
    customer: str
    currency: str = "USD"
    amount: Decimal = Field(gt=0)
    probability: Decimal = Field(ge=0, le=1)
    expected_close_date: date
    expected_payment_date: date
    stage: str = "PROPOSAL"

class NettingIn(BaseModel):
    positions: list[dict]

class LiquidityStressIn(BaseModel):
    cash_inr: Decimal = Field(ge=0)
    expected_receipts_inr: Decimal = Field(ge=0)
    expected_payments_inr: Decimal = Field(ge=0)
    margin_call_inr: Decimal = Field(ge=0)
    fx_shock_pct: Decimal = Decimal("0")
    credit_line_limit_inr: Decimal = Field(default=Decimal("0"), ge=0)
    credit_line_drawn_inr: Decimal = Field(default=Decimal("0"), ge=0)

class WorkingCapitalIn(BaseModel):
    invoice_amount: Decimal
    currency: str = "USD"
    spot_rate: Decimal
    forward_rate: Decimal
    days_to_payment: int
    early_discount_pct: Decimal
    financing_annual_pct: Decimal
