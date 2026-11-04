"""create cashflow forecasting tables

Revision ID: 003_create_cashflow_forecasting_tables
Revises: 002_create_ml_predictions_table
Create Date: 2026-11-04 23:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_create_cashflow_forecasting_tables'
down_revision: Union[str, None] = '002_create_ml_predictions_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. cash_balance_snapshots
    op.create_table(
        'cash_balance_snapshots',
        sa.Column('snapshot_id', sa.String(length=50), nullable=False),
        sa.Column('company_id', sa.String(length=50), nullable=False),
        sa.Column('as_of_date', sa.Date(), nullable=False),
        sa.Column('balance_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('minimum_cash_threshold', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='MANUAL'),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('snapshot_id'),
        sa.UniqueConstraint('company_id', 'as_of_date', 'currency', name='uq_cash_snapshot_company_date_curr'),
    )
    op.create_index(op.f('ix_cash_balance_snapshots_snapshot_id'), 'cash_balance_snapshots', ['snapshot_id'], unique=False)
    op.create_index(op.f('ix_cash_balance_snapshots_company_id'), 'cash_balance_snapshots', ['company_id'], unique=False)
    op.create_index(op.f('ix_cash_balance_snapshots_as_of_date'), 'cash_balance_snapshots', ['as_of_date'], unique=False)

    # 2. collection_forecast_overrides
    op.create_table(
        'collection_forecast_overrides',
        sa.Column('override_id', sa.String(length=50), nullable=False),
        sa.Column('company_id', sa.String(length=50), nullable=False),
        sa.Column('invoice_id', sa.String(length=50), nullable=False),
        sa.Column('expected_collection_date', sa.Date(), nullable=False),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.invoice_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('override_id'),
    )
    op.create_index(op.f('ix_collection_forecast_overrides_override_id'), 'collection_forecast_overrides', ['override_id'], unique=False)
    op.create_index(op.f('ix_collection_forecast_overrides_company_id'), 'collection_forecast_overrides', ['company_id'], unique=False)
    op.create_index(op.f('ix_collection_forecast_overrides_invoice_id'), 'collection_forecast_overrides', ['invoice_id'], unique=False)

    # 3. expense_forecast_assumptions
    op.create_table(
        'expense_forecast_assumptions',
        sa.Column('assumption_id', sa.String(length=50), nullable=False),
        sa.Column('company_id', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('monthly_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('effective_start_date', sa.Date(), nullable=False),
        sa.Column('effective_end_date', sa.Date(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='MANUAL'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('assumption_id'),
    )
    op.create_index(op.f('ix_expense_forecast_assumptions_assumption_id'), 'expense_forecast_assumptions', ['assumption_id'], unique=False)
    op.create_index(op.f('ix_expense_forecast_assumptions_company_id'), 'expense_forecast_assumptions', ['company_id'], unique=False)
    op.create_index(op.f('ix_expense_forecast_assumptions_category'), 'expense_forecast_assumptions', ['category'], unique=False)

    # 4. cashflow_forecast_runs
    op.create_table(
        'cashflow_forecast_runs',
        sa.Column('forecast_id', sa.String(length=50), nullable=False),
        sa.Column('company_id', sa.String(length=50), nullable=False),
        sa.Column('as_of_date', sa.Date(), nullable=False),
        sa.Column('horizon_days', sa.Integer(), nullable=False),
        sa.Column('base_currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('opening_balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('forecast_method_version', sa.String(length=50), nullable=False, server_default='v1.0.0'),
        sa.Column('payment_model_version', sa.String(length=50), nullable=False, server_default='v1.0.0'),
        sa.Column('data_freshness_status', sa.String(length=50), nullable=False),
        sa.Column('forecast_reliability', sa.String(length=50), nullable=False),
        sa.Column('forecast_type', sa.String(length=50), nullable=False, server_default='BASELINE'),
        sa.Column('forecast_payload', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('forecast_id'),
    )
    op.create_index(op.f('ix_cashflow_forecast_runs_forecast_id'), 'cashflow_forecast_runs', ['forecast_id'], unique=False)
    op.create_index(op.f('ix_cashflow_forecast_runs_company_id'), 'cashflow_forecast_runs', ['company_id'], unique=False)
    op.create_index(op.f('ix_cashflow_forecast_runs_as_of_date'), 'cashflow_forecast_runs', ['as_of_date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_cashflow_forecast_runs_as_of_date'), table_name='cashflow_forecast_runs')
    op.drop_index(op.f('ix_cashflow_forecast_runs_company_id'), table_name='cashflow_forecast_runs')
    op.drop_index(op.f('ix_cashflow_forecast_runs_forecast_id'), table_name='cashflow_forecast_runs')
    op.drop_table('cashflow_forecast_runs')

    op.drop_index(op.f('ix_expense_forecast_assumptions_category'), table_name='expense_forecast_assumptions')
    op.drop_index(op.f('ix_expense_forecast_assumptions_company_id'), table_name='expense_forecast_assumptions')
    op.drop_index(op.f('ix_expense_forecast_assumptions_assumption_id'), table_name='expense_forecast_assumptions')
    op.drop_table('expense_forecast_assumptions')

    op.drop_index(op.f('ix_collection_forecast_overrides_invoice_id'), table_name='collection_forecast_overrides')
    op.drop_index(op.f('ix_collection_forecast_overrides_company_id'), table_name='collection_forecast_overrides')
    op.drop_index(op.f('ix_collection_forecast_overrides_override_id'), table_name='collection_forecast_overrides')
    op.drop_table('collection_forecast_overrides')

    op.drop_index(op.f('ix_cash_balance_snapshots_as_of_date'), table_name='cash_balance_snapshots')
    op.drop_index(op.f('ix_cash_balance_snapshots_company_id'), table_name='cash_balance_snapshots')
    op.drop_index(op.f('ix_cash_balance_snapshots_snapshot_id'), table_name='cash_balance_snapshots')
    op.drop_table('cash_balance_snapshots')

