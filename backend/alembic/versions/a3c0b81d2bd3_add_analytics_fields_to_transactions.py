"""add_analytics_fields_to_transactions

Revision ID: a3c0b81d2bd3
Revises: f08115e51ad2
Create Date: 2026-11-05 12:54:12.403752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c0b81d2bd3'
down_revision: Union[str, Sequence[str], None] = 'f08115e51ad2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema using batch mode for SQLite & PostgreSQL compatibility."""
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('transaction_type', sa.String(length=20), server_default='EXPENSE', nullable=False))
        batch_op.add_column(sa.Column('description', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('is_recurring', sa.Boolean(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('recurring_frequency', sa.String(length=50), nullable=True))
        batch_op.alter_column('vendor_id', existing_type=sa.INTEGER(), nullable=True)
        batch_op.create_index(batch_op.f('ix_transactions_category'), ['category'], unique=False)
        batch_op.create_index(batch_op.f('ix_transactions_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_transactions_is_recurring'), ['is_recurring'], unique=False)
        batch_op.create_index(batch_op.f('ix_transactions_transaction_type'), ['transaction_type'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_transactions_transaction_type'))
        batch_op.drop_index(batch_op.f('ix_transactions_is_recurring'))
        batch_op.drop_index(batch_op.f('ix_transactions_created_at'))
        batch_op.drop_index(batch_op.f('ix_transactions_category'))
        batch_op.alter_column('vendor_id', existing_type=sa.INTEGER(), nullable=False)
        batch_op.drop_column('recurring_frequency')
        batch_op.drop_column('is_recurring')
        batch_op.drop_column('description')
        batch_op.drop_column('transaction_type')
