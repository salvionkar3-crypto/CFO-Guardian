"""add_risk_signals_detail_to_risk_assessments

Revision ID: 003f9445d2f6
Revises: a3c0b81d2bd3
Create Date: 2026-11-05 13:41:58.739066

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003f9445d2f6'
down_revision: Union[str, Sequence[str], None] = 'a3c0b81d2bd3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema using batch mode for SQLite & PostgreSQL compatibility."""
    with op.batch_alter_table('risk_assessments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('risk_signals', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('supporting_evidence', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('missing_information', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('recommended_action', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('plain_explanation', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('risk_assessments', schema=None) as batch_op:
        batch_op.drop_column('plain_explanation')
        batch_op.drop_column('recommended_action')
        batch_op.drop_column('missing_information')
        batch_op.drop_column('supporting_evidence')
        batch_op.drop_column('risk_signals')
