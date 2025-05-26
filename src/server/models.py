from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Numeric, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class TransactionStatus(str, Enum):
    PENDING_ITEMS = "pending_items"
    CAPTURED = "captured"
    CANCELLED = "cancelled"
    ERROR = "error"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True)
    device_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    location = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    transactions = relationship("Transaction", back_populates="device")
    inventory = relationship("DeviceInventory", back_populates="device")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    sku = Column(String(50), unique=True)
    category = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    inventory = relationship("DeviceInventory", back_populates="product")
    transaction_items = relationship("TransactionItem", back_populates="product")

class DeviceInventory(Base):
    __tablename__ = "device_inventory"
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=0)
    slot_number = Column(Integer)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    device = relationship("Device", back_populates="inventory")
    product = relationship("Product", back_populates="inventory")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(100), unique=True, nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    payment_intent_id = Column(String(100))
    status = Column(String(20), default=TransactionStatus.PENDING_ITEMS)
    payment_status = Column(String(20), default=PaymentStatus.PENDING)
    total_amount = Column(Numeric(10, 2))
    items_json = Column(Text)  # Temporary field for backward compatibility
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    device = relationship("Device", back_populates="transactions")
    items = relationship("TransactionItem", back_populates="transaction")

class TransactionItem(Base):
    __tablename__ = "transaction_items"
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    
    transaction = relationship("Transaction", back_populates="items")
    product = relationship("Product", back_populates="transaction_items")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    phone = Column(String(20))
    name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    table_name = Column(String(50), nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(String(20), nullable=False)  # INSERT, UPDATE, DELETE
    old_values = Column(Text)  # JSON
    new_values = Column(Text)  # JSON
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())