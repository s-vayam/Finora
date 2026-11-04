"""create fx tables

Revision ID: 004_create_fx_tables
Revises: 003_create_cashflow_forecasting_tables
Create Date: 2026-11-05 00:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_create_fx_tables'
down_revision: Union[str, None] = '003_create_cashflow_forecasting_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. fx_rate_observations
    op.create_table(
        'fx_rate_observations',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('base_currency', sa.String(length=10), nullable=False),
        sa.Column('quote_currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('rate_type', sa.String(length=30), nullable=False),
        sa.Column('rate_value', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('original_rate_value', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('original_unit', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('provider_effective_at', sa.DateTime(), nullable=True),
        sa.Column('observation_date', sa.Date(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.Column('market_session', sa.String(length=50), nullable=True),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('is_stale', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_derived', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('data_delay_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('source_notice', sa.String(length=500), nullable=True),
        sa.Column('observation_key', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('observation_key', name='uq_fx_obs_key'),
    )
    op.create_index(op.f('ix_fx_rate_observations_id'), 'fx_rate_observations', ['id'], unique=False)
    op.create_index(op.f('ix_fx_rate_observations_base_currency'), 'fx_rate_observations', ['base_currency'], unique=False)
    op.create_index(op.f('ix_fx_rate_observations_quote_currency'), 'fx_rate_observations', ['quote_currency'], unique=False)
    op.create_index(op.f('ix_fx_rate_observations_rate_type'), 'fx_rate_observations', ['rate_type'], unique=False)
    op.create_index(op.f('ix_fx_rate_observations_provider'), 'fx_rate_observations', ['provider'], unique=False)
    op.create_index(op.f('ix_fx_rate_observations_observation_date'), 'fx_rate_observations', ['observation_date'], unique=False)
    op.create_index(op.f('ix_fx_rate_observations_observation_key'), 'fx_rate_observations', ['observation_key'], unique=True)
    op.create_index('idx_fx_obs_pair_date_type', 'fx_rate_observations', ['base_currency', 'quote_currency', 'observation_date', 'rate_type'], unique=False)

    # 2. fx_fetch_runs
    op.create_table(
        'fx_fetch_runs',
        sa.Column('fetch_id', sa.String(length=50), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('requested_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('response_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('fetch_id'),
    )
    op.create_index(op.f('ix_fx_fetch_runs_fetch_id'), 'fx_fetch_runs', ['fetch_id'], unique=False)
    op.create_index(op.f('ix_fx_fetch_runs_provider'), 'fx_fetch_runs', ['provider'], unique=False)
    op.create_index(op.f('ix_fx_fetch_runs_status'), 'fx_fetch_runs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('fx_fetch_runs')
    op.drop_table('fx_rate_observations')

