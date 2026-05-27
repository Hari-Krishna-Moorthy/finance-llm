from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ForeignKey, Numeric
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
    
    transactions = relationship("Transaction", back_populates="category")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True)
    description = Column(String)
    amount = Column(Numeric(precision=15, scale=2))
    transaction_type = Column(String)  # Credit or Debit
    reference_id = Column(String, nullable=True, index=True)
    
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
