"""add stock_status to products

Revision ID: 004
Revises: 003
Create Date: 2024-01-01 00:03:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('products', sa.Column('stock_status', sa.String(50), server_default='unknown', nullable=True))
    
    op.create_index('ix_products_stock_status', 'products', ['stock_status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_products_stock_status', table_name='products')
    op.drop_column('products', 'stock_status') 