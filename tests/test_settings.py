from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from decimal import Decimal

from app.database import Base
from app.models import AppSetting, DashboardState, Transaction, Category
from app.services.app_settings import get_setting, upsert_setting
from app.services.dashboard_state import get_dashboard_state, upsert_dashboard_state, sync_dashboard_metrics

def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

def test_app_settings_upsert_and_get():
    db = _make_session()
    
    # Test initial get
    assert get_setting(db, "theme", "light") == "light"
    
    # Test upsert
    upsert_setting(db, "theme", "dark")
    assert get_setting(db, "theme", "light") == "dark"
    
    # Test update
    upsert_setting(db, "theme", "oled")
    assert get_setting(db, "theme", "light") == "oled"

def test_dashboard_state_upsert_and_get():
    db = _make_session()
    
    # Test initial get
    assert get_dashboard_state(db, "total_balance", "0") == "0"
    
    # Test upsert
    upsert_dashboard_state(db, "total_balance", "1000.50")
    assert get_dashboard_state(db, "total_balance", "0") == "1000.50"

def test_sync_dashboard_metrics():
    db = _make_session()
    
    # Setup transactions
    cat_self = Category(name="Self transfer")
    db.add(cat_self)
    db.commit()
    
    t1 = Transaction(amount=Decimal("1000"), base_amount_inr=Decimal("1000"), transaction_type="Credit")
    t2 = Transaction(amount=Decimal("200"), base_amount_inr=Decimal("200"), transaction_type="Debit")
    t3 = Transaction(amount=Decimal("500"), base_amount_inr=Decimal("500"), transaction_type="Debit", category_id=cat_self.id)
    
    db.add_all([t1, t2, t3])
    db.commit()
    
    # Test sync with default settings (exclude self transfer = true)
    sync_dashboard_metrics(db)
    # 1000 (credit) - 200 (debit) = 800. t3 is excluded.
    assert Decimal(get_dashboard_state(db, "total_balance")) == Decimal("800")
    
    # Test with balance adjustment
    upsert_setting(db, "balance_adjustment", "100")
    sync_dashboard_metrics(db)
    assert Decimal(get_dashboard_state(db, "total_balance")) == Decimal("900")
    
    # Test with include self transfer
    upsert_setting(db, "exclude_self_transfer_from_balance", "false")
    sync_dashboard_metrics(db)
    # 1000 - 200 - 500 + 100 = 400
    assert Decimal(get_dashboard_state(db, "total_balance")) == Decimal("400")
