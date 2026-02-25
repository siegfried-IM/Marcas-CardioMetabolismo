from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Molecule(Base):
    __tablename__ = "molecules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    clase: Mapped[str | None] = mapped_column(String(120))

    brands: Mapped[list["Brand"]] = relationship(back_populates="molecule")


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    molecule_id: Mapped[int | None] = mapped_column(ForeignKey("molecules.id"))
    manufacturer: Mapped[str | None] = mapped_column(String(80))
    is_siegfried: Mapped[bool] = mapped_column(Boolean, default=False)
    color: Mapped[str | None] = mapped_column(String(7))

    molecule: Mapped[Molecule | None] = relationship(back_populates="brands")
    presentations: Mapped[list["Presentation"]] = relationship(back_populates="brand")


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class Presentation(Base):
    __tablename__ = "presentations"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    name: Mapped[str] = mapped_column(String(200))
    dose: Mapped[str | None] = mapped_column(String(80))
    familia: Mapped[str | None] = mapped_column(String(80))

    brand: Mapped[Brand] = relationship(back_populates="presentations")

    __table_args__ = (UniqueConstraint("brand_id", "name"),)


class BudgetEntry(Base):
    __tablename__ = "budget_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    year: Mapped[int] = mapped_column(SmallInteger)
    month: Mapped[int] = mapped_column(SmallInteger)
    budget: Mapped[int | None] = mapped_column(Integer)
    actual: Mapped[int | None] = mapped_column(Integer)

    brand: Mapped[Brand] = relationship()

    __table_args__ = (UniqueConstraint("brand_id", "year", "month"),)


class MarketPerformance(Base):
    __tablename__ = "market_performance"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    molecule_id: Mapped[int] = mapped_column(ForeignKey("molecules.id"))
    month: Mapped[date] = mapped_column(Date)
    units: Mapped[int | None] = mapped_column(Integer)
    market_share: Mapped[float | None] = mapped_column(Numeric(6, 2))

    brand: Mapped[Brand] = relationship()
    molecule: Mapped[Molecule] = relationship()

    __table_args__ = (UniqueConstraint("brand_id", "molecule_id", "month"),)


class MarketPerformanceAccumulated(Base):
    __tablename__ = "market_performance_accumulated"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    molecule_id: Mapped[int] = mapped_column(ForeignKey("molecules.id"))
    period_type: Mapped[str] = mapped_column(String(3))
    ref_date: Mapped[date] = mapped_column(Date)
    units: Mapped[int | None] = mapped_column(Integer)
    market_share: Mapped[float | None] = mapped_column(Numeric(6, 2))

    brand: Mapped[Brand] = relationship()
    molecule: Mapped[Molecule] = relationship()

    __table_args__ = (
        UniqueConstraint("brand_id", "molecule_id", "period_type", "ref_date"),
    )


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    month: Mapped[date] = mapped_column(Date)
    prescriptions: Mapped[int] = mapped_column(Integer)
    physicians: Mapped[int] = mapped_column(Integer)

    brand: Mapped[Brand] = relationship()

    __table_args__ = (UniqueConstraint("brand_id", "month"),)


class PrescriptionMarketShare(Base):
    __tablename__ = "prescription_market_share"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    month: Mapped[date] = mapped_column(Date)
    sie_prescriptions: Mapped[int | None] = mapped_column(Integer)
    market_prescriptions: Mapped[int | None] = mapped_column(Integer)
    market_share: Mapped[float | None] = mapped_column(Numeric(5, 2))

    brand: Mapped[Brand] = relationship()

    __table_args__ = (UniqueConstraint("brand_id", "month"),)


class PrescriptionCompetitor(Base):
    __tablename__ = "prescription_competitors"

    id: Mapped[int] = mapped_column(primary_key=True)
    sie_brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    competitor_brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    month: Mapped[date] = mapped_column(Date)
    prescriptions: Mapped[int] = mapped_column(Integer)

    sie_brand: Mapped[Brand] = relationship(foreign_keys=[sie_brand_id])
    competitor_brand: Mapped[Brand] = relationship(foreign_keys=[competitor_brand_id])

    __table_args__ = (
        UniqueConstraint("sie_brand_id", "competitor_brand_id", "month"),
    )


class ChannelDistribution(Base):
    __tablename__ = "channel_distribution"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), unique=True)
    units: Mapped[int] = mapped_column(Integer)
    conversion_pct: Mapped[float | None] = mapped_column(Numeric(5, 1))
    counter_pct: Mapped[float | None] = mapped_column(Numeric(5, 1))

    brand: Mapped[Brand] = relationship()


class Agreement(Base):
    __tablename__ = "agreements"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    health_plan: Mapped[str] = mapped_column(String(200))
    units_current: Mapped[int | None] = mapped_column(Integer)
    units_previous: Mapped[int | None] = mapped_column(Integer)
    delta_pct: Mapped[int | None] = mapped_column(SmallInteger)
    net_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))

    brand: Mapped[Brand] = relationship()

    __table_args__ = (UniqueConstraint("brand_id", "health_plan"),)


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    presentation: Mapped[str] = mapped_column(String(200))
    laboratory: Mapped[str] = mapped_column(String(80))
    product_name: Mapped[str] = mapped_column(String(100))
    pvp_previous: Mapped[float | None] = mapped_column(Numeric(12, 2))
    pvp_current: Mapped[float | None] = mapped_column(Numeric(12, 2))
    variation: Mapped[float | None] = mapped_column(Numeric(6, 4))
    is_siegfried: Mapped[bool] = mapped_column(Boolean, default=False)

    brand: Mapped[Brand] = relationship()

    __table_args__ = (UniqueConstraint("brand_id", "presentation", "product_name"),)


class StockBrand(Base):
    __tablename__ = "stock_brand"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    month: Mapped[date] = mapped_column(Date)
    days_cover: Mapped[int | None] = mapped_column(SmallInteger)
    sales: Mapped[int | None] = mapped_column(Integer)
    stock_units: Mapped[int | None] = mapped_column(Integer)

    brand: Mapped[Brand] = relationship()

    __table_args__ = (UniqueConstraint("brand_id", "month"),)


class StockPresentation(Base):
    __tablename__ = "stock_presentation"

    id: Mapped[int] = mapped_column(primary_key=True)
    presentation_id: Mapped[int] = mapped_column(ForeignKey("presentations.id"))
    month: Mapped[date] = mapped_column(Date)
    sales: Mapped[int | None] = mapped_column(Integer)
    days_cover: Mapped[int | None] = mapped_column(SmallInteger)
    status: Mapped[str | None] = mapped_column(String(10))

    presentation: Mapped[Presentation] = relationship()

    __table_args__ = (UniqueConstraint("presentation_id", "month"),)


class KpiGlobal(Base):
    __tablename__ = "kpi_global"

    id: Mapped[int] = mapped_column(primary_key=True)
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("now()")
    )
    data: Mapped[dict] = mapped_column(JSONB)


class KpiBrand(Base):
    __tablename__ = "kpi_brand"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("now()")
    )
    data: Mapped[dict] = mapped_column(JSONB)

    brand: Mapped[Brand] = relationship()
