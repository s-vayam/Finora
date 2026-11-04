"""create ml_predictions table

Revision ID: 002_create_ml_predictions_table
Revises: 001_create_payments_table
Create Date: 2026-11-04 23:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_create_ml_predictions_table'
down_revision: Union[str, None] = '001_create_payments_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ml_predictions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('invoice_id', sa.String(length=50), nullable=False),
        sa.Column('prediction_timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('predicted_late_probability', sa.Float(), nullable=False),
        sa.Column('risk_category', sa.String(length=20), nullable=False),
        sa.Column('predicted_delay_days', sa.Float(), nullable=False),
        sa.Column('expected_delay_days', sa.Float(), nullable=False),
        sa.Column('estimated_payment_date', sa.Date(), nullable=False),
        sa.Column('features_snapshot', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.invoice_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ml_predictions_invoice_id'), 'ml_predictions', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_ml_predictions_prediction_timestamp'), 'ml_predictions', ['prediction_timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ml_predictions_prediction_timestamp'), table_name='ml_predictions')
    op.drop_index(op.f('ix_ml_predictions_invoice_id'), table_name='ml_predictions')
    op.drop_table('ml_predictions')
