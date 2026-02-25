from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DddMarket(Base):
    __tablename__ = "ddd_markets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    clase: Mapped[str | None] = mapped_column(String(120))
    total_units: Mapped[int | None] = mapped_column(Integer)
    sie_units: Mapped[int | None] = mapped_column(Integer)
    global_ms: Mapped[float | None] = mapped_column(Numeric(5, 1))

    brands: Mapped[list["DddBrand"]] = relationship(back_populates="market")


class DddBrand(Base):
    __tablename__ = "ddd_brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("ddd_markets.id"))
    name: Mapped[str] = mapped_column(String(80))
    is_siegfried: Mapped[bool] = mapped_column(Boolean, default=False)

    market: Mapped[DddMarket] = relationship(back_populates="brands")

    __table_args__ = (UniqueConstraint("market_id", "name"),)


class DddBrandMonthly(Base):
    __tablename__ = "ddd_brand_monthly"

    id: Mapped[int] = mapped_column(primary_key=True)
    ddd_brand_id: Mapped[int] = mapped_column(ForeignKey("ddd_brands.id"))
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    month: Mapped[int] = mapped_column(SmallInteger)
    units: Mapped[int | None] = mapped_column(Integer)

    ddd_brand: Mapped[DddBrand] = relationship()
    region: Mapped["Region"] = relationship()

    __table_args__ = (UniqueConstraint("ddd_brand_id", "region_id", "month"),)


# Avoid circular import — Region is from cardio module
from app.models.cardio import Region  # noqa: E402


class DddTotalMonthly(Base):
    __tablename__ = "ddd_total_monthly"

    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("ddd_markets.id"))
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    month: Mapped[int] = mapped_column(SmallInteger)
    units: Mapped[int | None] = mapped_column(Integer)

    market: Mapped[DddMarket] = relationship()
    region: Mapped[Region] = relationship()

    __table_args__ = (UniqueConstraint("market_id", "region_id", "month"),)


class DddRegionSummary(Base):
    __tablename__ = "ddd_region_summary"

    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("ddd_markets.id"))
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    total_units: Mapped[int | None] = mapped_column(Integer)
    sie_units: Mapped[int | None] = mapped_column(Integer)
    market_share: Mapped[float | None] = mapped_column(Numeric(5, 1))

    market: Mapped[DddMarket] = relationship()
    region: Mapped[Region] = relationship()

    __table_args__ = (UniqueConstraint("market_id", "region_id"),)
