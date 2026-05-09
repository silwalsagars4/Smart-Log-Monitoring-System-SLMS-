"""add alert_interactions

Revision ID: 003_add_alert_interactions
Revises: 002_add_log_configs
Create Date: 2026-04-30 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_alert_interactions'
down_revision: Union[str, None] = '002_add_log_configs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('alert_interactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('user_role', sa.String(length=32), nullable=False),
        sa.Column('action', sa.String(length=32), nullable=False),
        sa.Column('message', sa.Text(), nullable=False, server_default=''),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_interactions_alert_id'), 'alert_interactions', ['alert_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_alert_interactions_alert_id'), table_name='alert_interactions')
    op.drop_table('alert_interactions')
