"""add timestamps to products

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 00:02:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('products', sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False))
    op.add_column('products', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False))

def downgrade() -> None:
    op.drop_column('products', 'updated_at')
    op.drop_column('products', 'created_at') 