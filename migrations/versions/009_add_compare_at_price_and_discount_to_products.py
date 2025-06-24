"""Add external_compare_at_price and external_discount to products

Revision ID: 009
Revises: 008
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', 
        sa.Column('external_compare_at_price', sa.Float, nullable=True)
    )
    op.add_column('products', 
        sa.Column('external_discount', sa.Float, nullable=True)
    )


def downgrade():
    op.drop_column('products', 'external_compare_at_price')
    op.drop_column('products', 'external_discount') 