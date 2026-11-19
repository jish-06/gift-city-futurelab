from decimal import Decimal as D
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.models import Company, Invoice, Hedge
from app.engine import calculate_exposures, reconcile


def db_session():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

def test_exposure_aggregation():
    db=db_session(); c=Company(name="Test"); db.add(c); db.flush()
    db.add(Invoice(company_id=c.id,invoice_number="I1",customer="A",legal_entity="LE",currency="USD",direction="RECEIVABLE",original_amount=D("100"),outstanding_amount=D("70"),issue_date=date.today(),due_date=date.today()+timedelta(days=10),status="OPEN"))
    db.commit()
    result=calculate_exposures(db,c.id)
    assert result[0]["amount"]=="70.00"

def test_overhedge_recommendation():
    db=db_session(); c=Company(name="Test"); db.add(c); db.flush()
    db.add(Invoice(company_id=c.id,invoice_number="I1",customer="A",legal_entity="LE",currency="USD",direction="RECEIVABLE",original_amount=D("100"),outstanding_amount=D("70"),issue_date=date.today(),due_date=date.today()+timedelta(days=10),status="OPEN"))
    db.add(Hedge(company_id=c.id,contract_number="H1",currency_pair="USD/INR",direction="SELL_BASE",notional_amount=D("100"),remaining_amount=D("100"),contract_rate=D("86"),maturity_date=date.today()+timedelta(days=10),legal_entity="LE",status="OPEN"))
    db.commit(); findings=reconcile(db,c.id)
    assert any(x.recommendation_type=="POTENTIAL_OVERHEDGE" for x in findings)
    assert str(findings[0].mismatch_amount) in ("30.0000","30.00")


def test_retained_cash_is_a_separate_asset_and_survives_settled_invoice():
    from app.models import Payment
    db=db_session(); c=Company(name="Test"); db.add(c); db.flush()
    inv=Invoice(company_id=c.id,invoice_number="I-SETTLED",customer="A",legal_entity="LE",currency="USD",direction="RECEIVABLE",original_amount=D("100"),outstanding_amount=D("0"),issue_date=date.today(),due_date=date.today()+timedelta(days=10),status="SETTLED")
    db.add(inv); db.flush()
    hedge=Hedge(company_id=c.id,contract_number="H-RETAINED",currency_pair="USD/INR",direction="SELL_BASE",notional_amount=D("100"),remaining_amount=D("100"),contract_rate=D("86"),maturity_date=date.today()+timedelta(days=10),legal_entity="LE",status="OPEN")
    db.add_all([hedge,Payment(company_id=c.id,invoice_id=inv.id,source_record_id="P-1",amount=D("100"),currency="USD",payment_date=date.today(),treatment="RETAINED",destination_currency="USD")]); db.commit()
    exposures=calculate_exposures(db,c.id)
    assert { (x["currency"],x["direction"]):x["amount"] for x in exposures }[("USD","ASSET_CASH")] == "100.00"
    assert not any(x.recommendation_type in {"POTENTIAL_OVERHEDGE","POTENTIAL_UNDERHEDGE"} for x in reconcile(db,c.id))


def test_foreign_currency_conversion_creates_destination_cash_exposure():
    from app.models import Payment
    db=db_session(); c=Company(name="Test"); db.add(c); db.flush()
    inv=Invoice(company_id=c.id,invoice_number="I-FX",customer="A",legal_entity="LE",currency="USD",direction="RECEIVABLE",original_amount=D("100"),outstanding_amount=D("0"),issue_date=date.today(),due_date=date.today()+timedelta(days=10),status="SETTLED")
    db.add(inv); db.flush()
    hedge=Hedge(company_id=c.id,contract_number="H-EUR-CASH",currency_pair="EUR/INR",direction="SELL_BASE",notional_amount=D("92"),remaining_amount=D("92"),contract_rate=D("92"),maturity_date=date.today()+timedelta(days=10),legal_entity="LE",status="OPEN")
    db.add_all([hedge,Payment(company_id=c.id,invoice_id=inv.id,source_record_id="P-FX",amount=D("100"),currency="USD",payment_date=date.today(),treatment="CONVERTED",destination_currency="EUR",conversion_rate=D("0.92"))]); db.commit()
    exposures=calculate_exposures(db,c.id)
    assert { (x["currency"],x["direction"]):x["amount"] for x in exposures }[("EUR","ASSET_CASH")] == "92.00"
    assert not any(x.recommendation_type in {"POTENTIAL_OVERHEDGE","POTENTIAL_UNDERHEDGE"} for x in reconcile(db,c.id))


def test_unknown_cash_treatment_creates_review_recommendation():
    from app.models import Payment
    db=db_session(); c=Company(name="Test"); db.add(c); db.flush()
    inv=Invoice(company_id=c.id,invoice_number="I-UNKNOWN",customer="A",legal_entity="LE",currency="USD",direction="RECEIVABLE",original_amount=D("100"),outstanding_amount=D("40"),issue_date=date.today(),due_date=date.today()+timedelta(days=10),status="OPEN")
    db.add(inv); db.flush()
    db.add(Payment(company_id=c.id,invoice_id=inv.id,source_record_id="P-UNKNOWN",amount=D("60"),currency="USD",payment_date=date.today(),treatment="UNKNOWN",destination_currency="")); db.commit()
    findings=reconcile(db,c.id)
    assert any(x.recommendation_type=="PAYMENT_TREATMENT_REVIEW" for x in findings)


def test_changed_source_snapshot_supersedes_old_recommendation():
    db=db_session(); c=Company(name="Test"); db.add(c); db.flush()
    inv=Invoice(company_id=c.id,invoice_number="I-CHANGE",customer="A",legal_entity="LE",currency="USD",direction="RECEIVABLE",original_amount=D("100"),outstanding_amount=D("70"),issue_date=date.today(),due_date=date.today()+timedelta(days=10),status="OPEN")
    hedge=Hedge(company_id=c.id,contract_number="H-CHANGE",currency_pair="USD/INR",direction="SELL_BASE",notional_amount=D("100"),remaining_amount=D("100"),contract_rate=D("86"),maturity_date=date.today()+timedelta(days=10),legal_entity="LE",status="OPEN")
    db.add_all([inv,hedge]); db.commit()
    first=reconcile(db,c.id)[0]
    inv.due_date=date.today()+timedelta(days=45); inv.version+=1; db.commit()
    second=reconcile(db,c.id)
    db.refresh(first)
    assert first.status=="SUPERSEDED"
    assert any(x.recommendation_type=="POTENTIAL_OVERHEDGE" and x.snapshot_hash != first.snapshot_hash for x in second)


def test_signed_and_lost_pipeline_stages_override_probability():
    from app.main import pipeline_exposure
    from app.models import PipelineDeal
    deal = PipelineDeal(
        company_id="test", deal_name="Order", customer="Customer", currency="USD",
        amount=D("1000"), probability=D("0.25"), expected_close_date=date.today(),
        expected_payment_date=date.today()+timedelta(days=30), stage="CONTRACT_SIGNED"
    )
    amount, factor, mode = pipeline_exposure(deal)
    assert (amount, factor, mode) == (D("1000.00"), D("1"), "FIRM_PRE_INVOICE")
    deal.stage = "LOST"
    amount, factor, mode = pipeline_exposure(deal)
    assert (amount, factor, mode) == (D("0.00"), D("0"), "EXCLUDED_LOST")


def test_liquidity_stress_includes_undrawn_credit_line_capacity():
    from app.main import liquidity_stress
    from app.schemas import LiquidityStressIn
    result = liquidity_stress(LiquidityStressIn(
        cash_inr=D("100"), expected_receipts_inr=D("50"), expected_payments_inr=D("80"),
        margin_call_inr=D("100"), fx_shock_pct=D("-10"),
        credit_line_limit_inr=D("200"), credit_line_drawn_inr=D("50")
    ))
    assert result["cash_after_margin_inr"] == "-35.00"
    assert result["undrawn_credit_capacity_inr"] == "150.00"
    assert result["credit_line_utilisation_pct"] == "25.00"
    assert result["shortfall_after_available_credit_inr"] == "0.00"
