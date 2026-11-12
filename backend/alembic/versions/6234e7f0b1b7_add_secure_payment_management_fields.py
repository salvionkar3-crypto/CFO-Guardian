"""add_secure_payment_management_fields

Revision ID: 6234e7f0b1b7
Revises: 003f9445d2f6
Create Date: 2026-11-08 16:13:01.598827

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6234e7f0b1b7'
down_revision: Union[str, Sequence[str], None] = '003f9445d2f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema using batch mode for SQLite & PostgreSQL compatibility."""
    with op.batch_alter_table('payment_drafts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('purpose', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('idempotency_key', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('details_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('approved_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('approved_by_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_payment_drafts_idempotency_key'), ['idempotency_key'], unique=False)
        batch_op.create_index(batch_op.f('ix_payment_drafts_approved_by_id'), ['approved_by_id'], unique=False)

    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('idempotency_key', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('payment_method', sa.String(length=50), server_default='PAYPAL_SANDBOX', nullable=False))
        batch_op.create_index(batch_op.f('ix_transactions_idempotency_key'), ['idempotency_key'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_transactions_idempotency_key'))
        batch_op.drop_column('payment_method')
        batch_op.drop_column('idempotency_key')

    with op.batch_alter_table('payment_drafts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_payment_drafts_approved_by_id'))
        batch_op.drop_index(batch_op.f('ix_payment_drafts_idempotency_key'))
        batch_op.drop_column('approved_by_id')
        batch_op.drop_column('approved_at')
        batch_op.drop_column('details_hash')
        batch_op.drop_column('idempotency_key')
        batch_op.drop_column('purpose')
