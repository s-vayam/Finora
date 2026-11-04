"""create fx forecast and scenario tables

Revision ID: 005_create_fx_forecast_and_scenario_tables
Revises: 004_create_fx_tables
Create Date: 2026-11-05 00:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_create_fx_forecast_and_scenario_tables'
down_revision: Union[str, None] = '004_create_fx_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. fx_forecasts
    op.create_table(
        'fx_forecasts',
        sa.Column('forecast_id', sa.String(length=50), nullable=False),
        sa.Column('company_id', sa.String(length=50), nullable=False),
        sa.Column('currency_pair', sa.String(length=10), nullable=False),
        sa.Column('anchor_rate', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('anchor_date', sa.Date(), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=False),
        sa.Column('horizon_sessions', sa.Integer(), nullable=False),
        sa.Column('predicted_log_return', sa.Float(), nullable=False),
        sa.Column('predicted_rate', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('percentage_movement', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('predicted_direction', sa.String(length=10), nullable=False),
        sa.Column('direction_probabilities', sa.JSON(), nullable=False),
        sa.Column('prediction_range_80', sa.JSON(), nullable=True),
        sa.Column('prediction_range_95', sa.JSON(), nullable=True),
        sa.Column('model_version', sa.String(length=20), nullable=False),
        sa.Column('skill_status', sa.String(length=30), nullable=False),
        sa.Column('is_validated', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('forecast_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('forecast_id'),
    )
    op.create_index(op.f('ix_fx_forecasts_forecast_id'), 'fx_forecasts', ['forecast_id'], unique=False)
    op.create_index(op.f('ix_fx_forecasts_company_id'), 'fx_forecasts', ['company_id'], unique=False)
    op.create_index(op.f('ix_fx_forecasts_currency_pair'), 'fx_forecasts', ['currency_pair'], unique=False)
    op.create_index(op.f('ix_fx_forecasts_target_date'), 'fx_forecasts', ['target_date'], unique=False)
    op.create_index(op.f('ix_fx_forecasts_created_at'), 'fx_forecasts', ['created_at'], unique=False)

    # 2. fx_scenario_runs
    op.create_table(
        'fx_scenario_runs',
        sa.Column('scenario_id', sa.String(length=50), nullable=False),
        sa.Column('company_id', sa.String(length=50), nullable=False),
        sa.Column('currency_pair', sa.String(length=10), nullable=False),
        sa.Column('benchmark_rate', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('scenario_rate', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('percentage_change', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('receivable_exposure', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('payable_exposure', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('estimated_receivable_impact', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('estimated_payable_impact', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('net_estimated_impact', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='SIMULATED'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('scenario_id'),
    )
    op.create_index(op.f('ix_fx_scenario_runs_scenario_id'), 'fx_scenario_runs', ['scenario_id'], unique=False)
    op.create_index(op.f('ix_fx_scenario_runs_company_id'), 'fx_scenario_runs', ['company_id'], unique=False)
    op.create_index(op.f('ix_fx_scenario_runs_currency_pair'), 'fx_scenario_runs', ['currency_pair'], unique=False)
    op.create_index(op.f('ix_fx_scenario_runs_created_at'), 'fx_scenario_runs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('fx_scenario_runs')
    op.drop_table('fx_forecasts')

