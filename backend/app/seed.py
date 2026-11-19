from datetime import date, timedelta
from decimal import Decimal as D
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Company, User, Invoice, Hedge, PipelineDeal, IntercompanyPosition, CashBalance

def seed(db: Session):
    company=db.scalar(select(Company).where(Company.name=="Aarav Engineering Exports (Demo)"))
    if company: return company
    company=Company(name="Aarav Engineering Exports (Demo)",base_currency="INR"); db.add(company); db.flush()
    db.add_all([
        User(id="maker",company_id=company.id,name="Jiya Demo (Maker)",email="maker@fxnexus.demo",role="maker"),
        User(id="checker",company_id=company.id,name="Treasury Manager (Checker)",email="checker@fxnexus.demo",role="checker"),
        User(id="reviewer",company_id=company.id,name="Treasury Analyst",email="reviewer@fxnexus.demo",role="reviewer")
    ])
    today=date.today()
    inv1=Invoice(company_id=company.id,source_system="demo",source_record_id="ZINV-1042",invoice_number="EXP-1042",customer="Northstar Components Inc.",legal_entity="India Export Co.",currency="USD",direction="RECEIVABLE",original_amount=D("50000"),outstanding_amount=D("35000"),issue_date=today-timedelta(days=12),due_date=today+timedelta(days=18),status="OPEN")
    inv2=Invoice(company_id=company.id,source_system="demo",source_record_id="ZINV-1043",invoice_number="EXP-1043",customer="EuroMach GmbH",legal_entity="India Export Co.",currency="EUR",direction="RECEIVABLE",original_amount=D("28000"),outstanding_amount=D("28000"),issue_date=today-timedelta(days=4),due_date=today+timedelta(days=42),status="OPEN")
    inv3=Invoice(company_id=company.id,source_system="demo",source_record_id="ZBILL-201",invoice_number="IMP-201",customer="Alloy Supplies LLC",legal_entity="India Export Co.",currency="USD",direction="PAYABLE",original_amount=D("12000"),outstanding_amount=D("12000"),issue_date=today-timedelta(days=8),due_date=today+timedelta(days=25),status="OPEN")
    db.add_all([inv1,inv2,inv3]); db.flush()
    db.add(Hedge(company_id=company.id,source_system="demo",contract_number="FWD-0045",currency_pair="USD/INR",direction="SELL_BASE",notional_amount=D("50000"),remaining_amount=D("50000"),contract_rate=D("86.000000"),maturity_date=today+timedelta(days=30),legal_entity="India Export Co.",status="OPEN"))
    db.add(Hedge(company_id=company.id,source_system="demo",contract_number="FWD-0046",currency_pair="EUR/INR",direction="SELL_BASE",notional_amount=D("20000"),remaining_amount=D("20000"),contract_rate=D("92.000000"),maturity_date=today+timedelta(days=42),legal_entity="India Export Co.",status="OPEN"))
    # Payment retained in USD: reduces invoice receivable but creates/maintains a USD cash balance.
    from .models import Payment
    db.add(Payment(company_id=company.id,invoice_id=inv1.id,source_record_id="PAY-DEMO-01",amount=D("15000"),currency="USD",payment_date=today-timedelta(days=2),treatment="RETAINED",destination_currency="USD"))
    db.add_all([
        PipelineDeal(company_id=company.id,deal_name="Q4 US machinery order",customer="Northstar Components",currency="USD",amount=D("120000"),probability=D("0.75"),expected_close_date=today+timedelta(days=10),expected_payment_date=today+timedelta(days=70),stage="NEGOTIATION"),
        PipelineDeal(company_id=company.id,deal_name="European tooling supply",customer="EuroMach",currency="EUR",amount=D("80000"),probability=D("0.45"),expected_close_date=today+timedelta(days=25),expected_payment_date=today+timedelta(days=90),stage="PROPOSAL")
    ])
    db.add_all([
        IntercompanyPosition(company_id=company.id,entity_name="India Export Co.",counterparty_entity="UAE Trading FZE",currency="USD",direction="RECEIVABLE",amount=D("30000"),due_date=today+timedelta(days=20)),
        IntercompanyPosition(company_id=company.id,entity_name="UAE Trading FZE",counterparty_entity="India Export Co.",currency="USD",direction="PAYABLE",amount=D("18000"),due_date=today+timedelta(days=22)),
        IntercompanyPosition(company_id=company.id,entity_name="India Export Co.",counterparty_entity="Germany GmbH",currency="EUR",direction="PAYABLE",amount=D("10000"),due_date=today+timedelta(days=25))
    ])
    db.add_all([
        CashBalance(company_id=company.id,legal_entity="India Export Co.",currency="INR",balance=D("12500000"),available_balance=D("10500000"),as_of=today),
        CashBalance(company_id=company.id,legal_entity="India Export Co.",currency="USD",balance=D("15000"),available_balance=D("15000"),as_of=today)
    ])
    db.commit()
    return company
