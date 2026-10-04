"""SQLAlchemy tables. JSON payloads preserve validated domain data."""

from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Business(Base):
    __tablename__ = "businesses"
    __table_args__ = (UniqueConstraint("source", "source_id"),)

    id: Mapped[str] = mapped_column(primary_key=True)
    source: Mapped[str]
    source_id: Mapped[str | None]
    name: Mapped[str]
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[str] = mapped_column(index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class ScanBusiness(Base):
    """One immutable discovery snapshot per business and scan."""

    __tablename__ = "scan_businesses"

    scan_id: Mapped[str] = mapped_column(ForeignKey("scans.id"), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class WebsiteAnalysis(Base):
    __tablename__ = "website_analyses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["scan_id", "business_id"],
            ["scan_businesses.scan_id", "scan_businesses.business_id"],
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    scan_id: Mapped[str] = mapped_column(index=True)
    business_id: Mapped[str] = mapped_column(index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        ForeignKeyConstraint(
            ["scan_id", "business_id"],
            ["scan_businesses.scan_id", "scan_businesses.business_id"],
        ),
        UniqueConstraint("scan_id", "business_id", "rule_code"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    scan_id: Mapped[str] = mapped_column(index=True)
    business_id: Mapped[str] = mapped_column(index=True)
    rule_code: Mapped[str]
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (
        ForeignKeyConstraint(
            ["scan_id", "business_id"],
            ["scan_businesses.scan_id", "scan_businesses.business_id"],
        ),
        CheckConstraint("value >= 0 AND value <= 100"),
    )

    scan_id: Mapped[str] = mapped_column(primary_key=True)
    business_id: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[int] = mapped_column(index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
