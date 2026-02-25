"""Nuevas tablas para 6 archivos de datos + columnas en existentes

Revision ID: 002
Revises: 001
Create Date: 2026-02-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- ALTER TABLEs existentes ---
    op.add_column("stock_brand", sa.Column("billing", sa.Numeric(14, 2)))
    op.add_column("stock_presentation", sa.Column("stock_units", sa.Integer))
    op.add_column("stock_presentation", sa.Column("billing", sa.Numeric(14, 2)))
    op.add_column("molecules", sa.Column("atc_code", sa.String(20)))
    op.add_column("brands", sa.Column("product_code", sa.String(20)))

    # --- agreement_details ---
    op.create_table(
        "agreement_details",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id")),
        sa.Column("laboratory", sa.String(120)),
        sa.Column("line", sa.String(80)),
        sa.Column("familia", sa.String(80)),
        sa.Column("health_plan", sa.String(200), nullable=False),
        sa.Column("health_plan_detail", sa.String(200)),
        sa.Column("product_name", sa.String(200)),
        sa.Column("units", sa.Integer),
        sa.Column("pvp_amount", sa.Numeric(14, 2)),
        sa.Column("system_coverage", sa.Numeric(14, 2)),
        sa.Column("lab_pvp_contribution", sa.Numeric(14, 2)),
        sa.Column("lab_adjustment", sa.Numeric(14, 2)),
        sa.Column("lab_total_contribution", sa.Numeric(14, 2)),
        sa.Column("net_contribution", sa.Numeric(14, 2)),
        sa.Column("report_date", sa.Date),
        sa.UniqueConstraint("brand_id", "health_plan", "health_plan_detail", "product_name", "report_date"),
    )

    # --- market_performance_regional ---
    op.create_table(
        "market_performance_regional",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.Integer, sa.ForeignKey("brands.id")),
        sa.Column("molecule_id", sa.Integer, sa.ForeignKey("molecules.id")),
        sa.Column("region_id", sa.Integer, sa.ForeignKey("regions.id")),
        sa.Column("month", sa.Date, nullable=False),
        sa.Column("units", sa.Integer),
        sa.UniqueConstraint("brand_id", "molecule_id", "region_id", "month"),
    )

    # --- market_ateneo ---
    op.create_table(
        "market_ateneo",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("atc_code", sa.String(20)),
        sa.Column("region", sa.String(120)),
        sa.Column("brand_name", sa.String(200)),
        sa.Column("product_name", sa.String(200)),
        sa.Column("laboratory", sa.String(80)),
        sa.Column("product_code", sa.String(20)),
        sa.Column("mat_5", sa.Integer),
        sa.Column("mat_4", sa.Integer),
        sa.Column("mat_3", sa.Integer),
        sa.Column("mat_2", sa.Integer),
        sa.Column("mat_current", sa.Integer),
        sa.Column("mes_12", sa.Integer),
        sa.Column("mes_11", sa.Integer),
        sa.Column("mes_10", sa.Integer),
        sa.Column("mes_9", sa.Integer),
        sa.Column("mes_8", sa.Integer),
        sa.Column("mes_7", sa.Integer),
        sa.Column("mes_6", sa.Integer),
        sa.Column("mes_5", sa.Integer),
        sa.Column("mes_4", sa.Integer),
        sa.Column("mes_3", sa.Integer),
        sa.Column("mes_2", sa.Integer),
        sa.Column("mes_current", sa.Integer),
        sa.Column("ytd_5", sa.Integer),
        sa.Column("ytd_4", sa.Integer),
        sa.Column("ytd_3", sa.Integer),
        sa.Column("ytd_2", sa.Integer),
        sa.Column("ytd_current", sa.Integer),
        sa.Column("ref_date", sa.Date),
        sa.Column("loaded_at", sa.DateTime, server_default=sa.text("now()")),
    )
    op.create_index("ix_market_ateneo_atc", "market_ateneo", ["atc_code"])
    op.create_index("ix_market_ateneo_region", "market_ateneo", ["region"])
    op.create_index("ix_market_ateneo_brand", "market_ateneo", ["brand_name"])

    # --- market_ateneo_national ---
    op.create_table(
        "market_ateneo_national",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pack_code", sa.String(40)),
        sa.Column("pack_name", sa.String(200)),
        sa.Column("product_name", sa.String(200)),
        sa.Column("corporation", sa.String(120)),
        sa.Column("manufacturer", sa.String(120)),
        sa.Column("atc_iv", sa.String(20)),
        sa.Column("molecule", sa.String(500)),
        sa.Column("pharma_form", sa.String(80)),
        sa.Column("launch_date", sa.String(40)),
        sa.Column("market_type", sa.String(10)),
        sa.Column("period_type", sa.String(10), nullable=False),
        sa.Column("period_date", sa.Date, nullable=False),
        sa.Column("usd_amount", sa.Numeric(16, 2)),
        sa.Column("local_amount", sa.Numeric(16, 2)),
        sa.Column("units", sa.Integer),
        sa.Column("loaded_at", sa.DateTime, server_default=sa.text("now()")),
        sa.UniqueConstraint("pack_code", "period_type", "period_date"),
    )

    # --- price_catalog ---
    op.create_table(
        "price_catalog",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("registro", sa.String(40)),
        sa.Column("troquel", sa.String(40)),
        sa.Column("product_name", sa.String(200)),
        sa.Column("presentation", sa.String(300)),
        sa.Column("drug_name", sa.String(200)),
        sa.Column("pharma_action", sa.String(200)),
        sa.Column("laboratory", sa.String(120)),
        sa.Column("barcode", sa.String(40)),
        sa.Column("product_type", sa.String(40)),
        sa.Column("pami_category", sa.String(40)),
        sa.Column("status", sa.String(40)),
        sa.Column("qty_presentations", sa.Integer),
        sa.Column("pvp_previous", sa.Numeric(14, 2)),
        sa.Column("pvp_current", sa.Numeric(14, 2)),
        sa.Column("variation_pct", sa.Numeric(6, 2)),
        sa.Column("effective_date", sa.Date),
        sa.Column("pvp_previous_date", sa.Date),
        sa.Column("pvp_current_date", sa.Date),
        sa.Column("loaded_at", sa.DateTime, server_default=sa.text("now()")),
        sa.UniqueConstraint("registro", "presentation"),
    )


def downgrade() -> None:
    op.drop_table("price_catalog")
    op.drop_table("market_ateneo_national")
    op.drop_index("ix_market_ateneo_brand", "market_ateneo")
    op.drop_index("ix_market_ateneo_region", "market_ateneo")
    op.drop_index("ix_market_ateneo_atc", "market_ateneo")
    op.drop_table("market_ateneo")
    op.drop_table("market_performance_regional")
    op.drop_table("agreement_details")

    op.drop_column("brands", "product_code")
    op.drop_column("molecules", "atc_code")
    op.drop_column("stock_presentation", "billing")
    op.drop_column("stock_presentation", "stock_units")
    op.drop_column("stock_brand", "billing")
