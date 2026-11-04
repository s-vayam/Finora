"""create payments table

Revision ID: 001_create_payments_table
Revises: 
Create Date: 2026-11-04 22:18:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_create_payments_table'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'payments',
        sa.Column('payment_id', sa.String(length=50), nullable=False),
        sa.Column('company_id', sa.String(length=50), nullable=False),
        sa.Column('invoice_id', sa.String(length=50), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('reference_number', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('cash_transaction_id', sa.String(length=50), nullable=False),
        sa.Column('idempotency_key', sa.String(length=100), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False, server_default='MANUAL'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.invoice_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cash_transaction_id'], ['cash_transactions.transaction_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('payment_id'),
        sa.UniqueConstraint('cash_transaction_id', name='uq_payments_cash_transaction_id'),
        sa.UniqueConstraint('idempotency_key', name='uq_payments_idempotency_key'),
    )
    op.create_index(op.f('ix_payments_payment_id'), 'payments', ['payment_id'], unique=False)
    op.create_index(op.f('ix_payments_company_id'), 'payments', ['company_id'], unique=False)
    op.create_index(op.f('ix_payments_invoice_id'), 'payments', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_payments_payment_date'), 'payments', ['payment_date'], unique=False)
    op.create_index(op.f('ix_payments_cash_transaction_id'), 'payments', ['cash_transaction_id'], unique=True)
    op.create_index(op.f('ix_payments_idempotency_key'), 'payments', ['idempotency_key'], unique=True)

def downgrade() -> None:
    # Manual downgrade only - never executed automatically
    op.drop_index(op.f('ix_payments_idempotency_key'), table_name='payments')
    op.drop_index(op.f('ix_payments_cash_transaction_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_payment_date'), table_name='payments')
    op.drop_index(op.f('ix_payments_invoice_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_company_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_payment_id'), table_name='payments')
    op.drop_table('payments')
