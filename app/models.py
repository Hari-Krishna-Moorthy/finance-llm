from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ForeignKey, Numeric, DateTime, func, JSON
from sqlalchemy.orm import relationship
from .database import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    account_type = Column(String)  # e.g., Checking, Savings, Credit Card
    currency = Column(String, default="INR")
    
    transactions = relationship("Transaction", back_populates="account")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    is_custom = Column(Boolean, default=False, nullable=False)
    
    transactions = relationship("Transaction", back_populates="category")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True)
    description = Column(String)
    amount = Column(Numeric(precision=15, scale=2))
    transaction_type = Column(String)  # Credit or Debit
    reference_id = Column(String, nullable=True, index=True)
    extra_details = Column(JSON, nullable=True)
    
    # Multi-Currency Support
    original_currency = Column(String, default="INR")
    exchange_rate = Column(Numeric(precision=15, scale=6), default=1.0)
    base_amount_inr = Column(Numeric(precision=15, scale=2))
    
    # Tax Tagging
    is_tax_deductible = Column(Boolean, default=False)
    tax_category = Column(String, nullable=True)
    
    # Relationships
    account_id = Column(Integer, ForeignKey("accounts.id"))
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Reconciliation: link to matching internal transfer
    internal_transfer_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    
    # Self-referential relationship for reconciliation
    internal_transfer = relationship("Transaction", remote_side=[id], post_update=True)


class StatementUpload(Base):
    __tablename__ = "statement_uploads"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, nullable=False)
    has_password = Column(Boolean, default=False, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processing_error = Column(String, nullable=True)

    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    account = relationship("Account")


class DashboardState(Base):
    __tablename__ = "dashboard_state"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# US Stock Momentum Analyzer Models

class StockSignal(Base):
    __tablename__ = "stock_signals"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    company_name = Column(String)
    current_price = Column(Numeric(15, 2))
    signal_type = Column(String)  # Strong Buy, Buy, etc.
    score = Column(Integer)
    status = Column(String)  # Active, Closed
    suggested_entry = Column(String)
    suggested_stop_loss = Column(Numeric(15, 2))
    suggested_target = Column(Numeric(15, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    rsi = Column(Float)
    macd_val = Column(Float)
    macd_signal = Column(Float)
    ema10 = Column(Float)
    ema20 = Column(Float)
    sma50 = Column(Float)
    sma200 = Column(Float)
    relative_strength = Column(Float)  # vs SPY
    volume_ratio = Column(Float)  # relative volume
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

class SupportResistanceLevel(Base):
    __tablename__ = "support_resistance_levels"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    support_price = Column(Numeric(15, 2))
    resistance_price = Column(Numeric(15, 2))
    is_breakout = Column(Boolean, default=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())

class MomentumScore(Base):
    __tablename__ = "momentum_scores"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    overall_score = Column(Integer)
    support_score = Column(Integer)
    ema_score = Column(Integer)
    sma_score = Column(Integer)
    rs_score = Column(Integer)
    vol_score = Column(Integer)
    macd_score = Column(Integer)
    scored_at = Column(DateTime(timezone=True), server_default=func.now())

class HistoricalScanResult(Base):
    __tablename__ = "historical_scan_results"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    score = Column(Integer)
    classification = Column(String)
    price_at_scan = Column(Numeric(15, 2))
    scanned_at = Column(DateTime(timezone=True), server_default=func.now())

class AIAnalysisResult(Base):
    __tablename__ = "ai_analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    analysis_text = Column(String, nullable=False)
    generated_date = Column(Date, default=func.current_date(), index=True, nullable=False)
