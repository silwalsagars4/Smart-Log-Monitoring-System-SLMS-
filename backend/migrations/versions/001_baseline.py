"""baseline

Revision ID: 001_baseline
Revises: 
Create Date: 2026-04-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_baseline'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Baseline assumes users and alerts tables already exist.
    # We add the role column to users table if it doesn't exist.
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='role'"))
    if not res.fetchone():
        op.add_column('users', sa.Column('role', sa.String(length=32), nullable=False, server_default='user'))


def downgrade() -> None:
    op.drop_column('users', 'role')
