"""add_mandatory_approval_workflow_fields

Revision ID: 7a19e2390f41
Revises: 6234e7f0b1b7
Create Date: 2026-11-08 17:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a19e2390f41'
down_revision: Union[str, Sequence[str], None] = '6234e7f0b1b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema using batch mode for SQLite & PostgreSQL compatibility."""
    with op.batch_alter_table('payment_drafts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('expires_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('requires_dual_approval', sa.Boolean(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('secondary_approved_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('secondary_approved_by_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))
        batch_op.create_index(batch_op.f('ix_payment_drafts_secondary_approved_by_id'), ['secondary_approved_by_id'], unique=False)

    with op.batch_alter_table('payment_approvals', schema=None) as batch_op:
        batch_op.add_column(sa.Column('approval_role', sa.String(length=50), server_default='PRIMARY_APPROVER', nullable=False))
        batch_op.add_column(sa.Column('details_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('expires_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('business_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('approval_validity_hours', sa.Float(), server_default='24.0', nullable=False))
        batch_op.add_column(sa.Column('block_critical_risk', sa.Boolean(), server_default='1', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('business_settings', schema=None) as batch_op:
        batch_op.drop_column('block_critical_risk')
        batch_op.drop_column('approval_validity_hours')

    with op.batch_alter_table('payment_approvals', schema=None) as batch_op:
        batch_op.drop_column('expires_at')
        batch_op.drop_column('details_hash')
        batch_op.drop_column('approval_role')

    with op.batch_alter_table('payment_drafts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_payment_drafts_secondary_approved_by_id'))
        batch_op.drop_column('rejection_reason')
        batch_op.drop_column('secondary_approved_by_id')
        batch_op.drop_column('secondary_approved_at')
        batch_op.drop_column('requires_dual_approval')
        batch_op.drop_column('expires_at')

