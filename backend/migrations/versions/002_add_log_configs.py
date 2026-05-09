"""add log_configs

Revision ID: 002_add_log_configs
Revises: 001_baseline
Create Date: 2026-04-30 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_log_configs'
down_revision: Union[str, None] = '001_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('log_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('log_path', sa.String(length=512), nullable=False),
        sa.Column('collector_type', sa.String(length=32), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('log_path')
    )


def downgrade() -> None:
    op.drop_table('log_configs')
