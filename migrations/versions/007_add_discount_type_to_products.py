"""add discount_type to products

Revision ID: 007
Revises: 006
Create Date: 2025-01-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('products', sa.Column('coupon_discount_type', sa.String(length=50), nullable=True, default=''))


def downgrade() -> None:
    op.drop_column('products', 'coupon_discount_type')