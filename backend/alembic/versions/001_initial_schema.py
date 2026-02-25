"""Schema inicial — todas las tablas

Revision ID: 001
Revises:
Create Date: 2026-02-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Dimensiones ---
    op.create_table(
        "molecules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("clase", sa.String(120)),
    )
    op.create_table(
        "regions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
    )
    op.create_table(
        "brands",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("molecule_id", sa.Integer, sa.ForeignKey("molecules.id")),
        sa.Column("manufacturer", sa.String(80)),
        sa.Column("is_siegfried", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("color", sa.String(7)),
    )
    op.create_table(
        "presentations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("dose", sa.String(80)),
        sa.Column("familia", sa.String(80)),
        sa.UniqueConstraint("brand_id", "name"),
    )

    # --- Cardio: Budget ---
    op.create_table(
        "budget_entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("year", sa.SmallInteger, nullable=False),
        sa.Column("month", sa.SmallInteger, nullable=False),
        sa.Column("budget", sa.Integer),
        sa.Column("actual", sa.Integer),
        sa.UniqueConstraint("brand_id", "year", "month"),
    )

    # --- Cardio: Market Performance ---
    op.create_table(
        "market_performance",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("molecule_id", sa.Integer, sa.ForeignKey("molecules.id"), nullable=False),
        sa.Column("month", sa.Date, nullable=False),
        sa.Column("units", sa.Integer),
        sa.Column("market_share", sa.Numeric(6, 2)),
        sa.UniqueConstraint("brand_id", "molecule_id", "month"),
    )
    op.create_table(
        "market_performance_accumulated",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("molecule_id", sa.Integer, sa.ForeignKey("molecules.id"), nullable=False),
        sa.Column("period_type", sa.String(3), nullable=False),
        sa.Column("ref_date", sa.Date, nullable=False),
        sa.Column("units", sa.Integer),
        sa.Column("market_share", sa.Numeric(6, 2)),
        sa.UniqueConstraint("brand_id", "molecule_id", "period_type", "ref_date"),
    )

    # --- Cardio: Recetas ---
    op.create_table(
        "prescriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("month", sa.Date, nullable=False),
        sa.Column("prescriptions", sa.Integer, nullable=False),
        sa.Column("physicians", sa.Integer, nullable=False),
        sa.UniqueConstraint("brand_id", "month"),
    )
    op.create_table(
        "prescription_market_share",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("month", sa.Date, nullable=False),
        sa.Column("sie_prescriptions", sa.Integer),
        sa.Column("market_prescriptions", sa.Integer),
        sa.Column("market_share", sa.Numeric(5, 2)),
        sa.UniqueConstraint("brand_id", "month"),
    )
    op.create_table(
        "prescription_competitors",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sie_brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("competitor_brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("month", sa.Date, nullable=False),
        sa.Column("prescriptions", sa.Integer, nullable=False),
        sa.UniqueConstraint("sie_brand_id", "competitor_brand_id", "month"),
    )

    # --- Cardio: Canales, Convenios, Precios ---
    op.create_table(
        "channel_distribution",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False, unique=True),
        sa.Column("units", sa.Integer, nullable=False),
        sa.Column("conversion_pct", sa.Numeric(5, 1)),
        sa.Column("counter_pct", sa.Numeric(5, 1)),
    )
    op.create_table(
        "agreements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("health_plan", sa.String(200), nullable=False),
        sa.Column("units_current", sa.Integer),
        sa.Column("units_previous", sa.Integer),
        sa.Column("delta_pct", sa.SmallInteger),
        sa.Column("net_amount", sa.Numeric(14, 2)),
        sa.UniqueConstraint("brand_id", "health_plan"),
    )
    op.create_table(
        "prices",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("presentation", sa.String(200), nullable=False),
        sa.Column("laboratory", sa.String(80), nullable=False),
        sa.Column("product_name", sa.String(100), nullable=False),
        sa.Column("pvp_previous", sa.Numeric(12, 2)),
        sa.Column("pvp_current", sa.Numeric(12, 2)),
        sa.Column("variation", sa.Numeric(6, 4)),
        sa.Column("is_siegfried", sa.Boolean, nullable=False, server_default="false"),
        sa.UniqueConstraint("brand_id", "presentation", "product_name"),
    )

    # --- Cardio: Stock ---
    op.create_table(
        "stock_brand",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("month", sa.Date, nullable=False),
        sa.Column("days_cover", sa.SmallInteger),
        sa.Column("sales", sa.Integer),
        sa.Column("stock_units", sa.Integer),
        sa.UniqueConstraint("brand_id", "month"),
    )
    op.create_table(
        "stock_presentation",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("presentation_id", sa.Integer, sa.ForeignKey("presentations.id"), nullable=False),
        sa.Column("month", sa.Date, nullable=False),
        sa.Column("sales", sa.Integer),
        sa.Column("days_cover", sa.SmallInteger),
        sa.Column("status", sa.String(10)),
        sa.UniqueConstraint("presentation_id", "month"),
    )

    # --- KPIs ---
    op.create_table(
        "kpi_global",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("loaded_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("data", postgresql.JSONB, nullable=False),
    )
    op.create_table(
        "kpi_brand",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("loaded_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("data", postgresql.JSONB, nullable=False),
    )

    # --- DDD ---
    op.create_table(
        "ddd_markets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("clase", sa.String(120)),
        sa.Column("total_units", sa.Integer),
        sa.Column("sie_units", sa.Integer),
        sa.Column("global_ms", sa.Numeric(5, 1)),
    )
    op.create_table(
        "ddd_brands",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("market_id", sa.Integer, sa.ForeignKey("ddd_markets.id"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("is_siegfried", sa.Boolean, nullable=False, server_default="false"),
        sa.UniqueConstraint("market_id", "name"),
    )
    op.create_table(
        "ddd_brand_monthly",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ddd_brand_id", sa.Integer, sa.ForeignKey("ddd_brands.id"), nullable=False),
        sa.Column("region_id", sa.Integer, sa.ForeignKey("regions.id"), nullable=False),
        sa.Column("month", sa.SmallInteger, nullable=False),
        sa.Column("units", sa.Integer),
        sa.UniqueConstraint("ddd_brand_id", "region_id", "month"),
    )
    op.create_table(
        "ddd_total_monthly",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("market_id", sa.Integer, sa.ForeignKey("ddd_markets.id"), nullable=False),
        sa.Column("region_id", sa.Integer, sa.ForeignKey("regions.id"), nullable=False),
        sa.Column("month", sa.SmallInteger, nullable=False),
        sa.Column("units", sa.Integer),
        sa.UniqueConstraint("market_id", "region_id", "month"),
    )
    op.create_table(
        "ddd_region_summary",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("market_id", sa.Integer, sa.ForeignKey("ddd_markets.id"), nullable=False),
        sa.Column("region_id", sa.Integer, sa.ForeignKey("regions.id"), nullable=False),
        sa.Column("total_units", sa.Integer),
        sa.Column("sie_units", sa.Integer),
        sa.Column("market_share", sa.Numeric(5, 1)),
        sa.UniqueConstraint("market_id", "region_id"),
    )


def downgrade() -> None:
    op.drop_table("ddd_region_summary")
    op.drop_table("ddd_total_monthly")
    op.drop_table("ddd_brand_monthly")
    op.drop_table("ddd_brands")
    op.drop_table("ddd_markets")
    op.drop_table("kpi_brand")
    op.drop_table("kpi_global")
    op.drop_table("stock_presentation")
    op.drop_table("stock_brand")
    op.drop_table("prices")
    op.drop_table("agreements")
    op.drop_table("channel_distribution")
    op.drop_table("prescription_competitors")
    op.drop_table("prescription_market_share")
    op.drop_table("prescriptions")
    op.drop_table("market_performance_accumulated")
    op.drop_table("market_performance")
    op.drop_table("budget_entries")
    op.drop_table("presentations")
    op.drop_table("brands")
    op.drop_table("regions")
    op.drop_table("molecules")
