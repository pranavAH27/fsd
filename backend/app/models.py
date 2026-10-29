from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(Enum("donor", "ngo", "volunteer", "admin"))
    organization_name: Mapped[str | None] = mapped_column(String(180))
    phone: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(String(500))
    lat: Mapped[float | None] = mapped_column(Numeric(10, 7))
    lng: Mapped[float | None] = mapped_column(Numeric(10, 7))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Donation(Base):
    __tablename__ = "donations"
    id: Mapped[int] = mapped_column(primary_key=True)
    donor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    food_name: Mapped[str] = mapped_column(String(180))
    food_type: Mapped[str] = mapped_column(Enum("cooked meal", "raw produce", "bakery", "packaged"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unit: Mapped[str] = mapped_column(String(32))
    dietary_info: Mapped[str] = mapped_column(Enum("veg", "non-veg", "vegan"))
    preparation_time: Mapped[datetime | None] = mapped_column(DateTime)
    expiry_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    pickup_address: Mapped[str] = mapped_column(String(500))
    lat: Mapped[float | None] = mapped_column(Numeric(10, 7))
    lng: Mapped[float | None] = mapped_column(Numeric(10, 7))
    storage_notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Enum("available", "claimed", "in_transit", "completed", "expired"), default="available", index=True)
    pickup_code: Mapped[str | None] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    donor = relationship("User", foreign_keys=[donor_id])
    claims = relationship("Claim", back_populates="donation")


class Claim(Base):
    __tablename__ = "claims"
    id: Mapped[int] = mapped_column(primary_key=True)
    donation_id: Mapped[int] = mapped_column(ForeignKey("donations.id"), index=True)
    ngo_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    volunteer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(Enum("claimed", "assigned", "in_transit", "completed", "cancelled"), default="claimed")
    notes: Mapped[str | None] = mapped_column(Text)
    claimed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)
    donation = relationship("Donation", back_populates="claims")
    ngo = relationship("User", foreign_keys=[ngo_id])
    volunteer = relationship("User", foreign_keys=[volunteer_id])


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(Enum("user", "assistant"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(120))
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
