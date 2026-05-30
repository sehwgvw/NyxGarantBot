from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    USER = "user"
    GUARANTOR = "guarantor"
    MODERATOR = "moderator"
    ADMIN = "admin"


class DealStatus(str, enum.Enum):
    DRAFT = "draft"
    WAITING_USER = "waiting_user"
    WAITING_GROUP = "waiting_group"
    ACTIVE = "active"
    DISPUTE = "dispute"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class DealSide(str, enum.Enum):
    BUYER = "buyer"
    SELLER = "seller"


class ReportStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class BlockType(str, enum.Enum):
    TEMPORARY = "temporary"
    PERMANENT = "permanent"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(32), default="Russian")
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    unpaid_cancel_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    roles: Mapped[list[RoleAssignment]] = relationship(back_populates="user", cascade="all, delete-orphan", foreign_keys="RoleAssignment.user_id")
    guarantor_profile: Mapped[GuarantorProfile | None] = relationship(back_populates="user")


class RoleAssignment(Base):
    __tablename__ = "role_assignments"
    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_user_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), index=True)
    granted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="roles", foreign_keys=[user_id])


class GuarantorProfile(Base):
    __tablename__ = "guarantor_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(255))
    display_username: Mapped[str | None] = mapped_column(String(255))
    telegram_public_id: Mapped[int | None] = mapped_column(BigInteger)
    description: Mapped[str | None] = mapped_column(Text)
    commission_percent: Mapped[float] = mapped_column(Float, default=10.0)
    zero_commission_until: Mapped[float | None] = mapped_column(Float)
    min_deal_amount: Mapped[float | None] = mapped_column(Float)
    max_deal_amount: Mapped[float | None] = mapped_column(Float)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    successful_deals: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_deals: Mapped[int] = mapped_column(Integer, default=0)
    complaints_count: Mapped[int] = mapped_column(Integer, default=0)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_top: Mapped[bool] = mapped_column(Boolean, default=False)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    review_link: Mapped[str | None] = mapped_column(String(512))
    pledge_links: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_username_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_telegram_id_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="guarantor_profile")


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(32), default="RUB")
    subject: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(String(128))
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    seller_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    guarantor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[DealStatus] = mapped_column(Enum(DealStatus), default=DealStatus.DRAFT, index=True)
    group_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    group_invite_link: Mapped[str | None] = mapped_column(String(512))
    buyer_confirmed_group: Mapped[bool] = mapped_column(Boolean, default=False)
    seller_confirmed_group: Mapped[bool] = mapped_column(Boolean, default=False)
    guarantor_confirmed_group: Mapped[bool] = mapped_column(Boolean, default=False)
    buyer_success_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    seller_success_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RuchMember(Base):
    __tablename__ = "ruch_members"
    __table_args__ = (UniqueConstraint("deal_id", "user_id", name="uq_deal_ruch"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    added_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("deal_id", "author_id", name="uq_review_deal_author"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"))
    guarantor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    stars: Mapped[int] = mapped_column(Integer)
    text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FavoriteGuarantor(Base):
    __tablename__ = "favorite_guarantors"
    __table_args__ = (UniqueConstraint("user_id", "guarantor_id", name="uq_favorite_guarantor"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    guarantor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("deals.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.OPEN)
    kind: Mapped[str] = mapped_column(String(64), default="support")
    text: Mapped[str] = mapped_column(Text)
    moderation_message_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Block(Base):
    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[BlockType] = mapped_column(Enum(BlockType), default=BlockType.TEMPORARY)
    reason: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BotSetting(Base):
    __tablename__ = "bot_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    severity: Mapped[str] = mapped_column(String(32), default="info")
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("deals.id"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class BackupLog(Base):
    __tablename__ = "backup_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(64))
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
