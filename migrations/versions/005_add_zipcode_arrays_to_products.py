"""add zipcode arrays to products

Revision ID: 005
Revises: 004
Create Date: 2024-01-01 00:04:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('products', sa.Column('available_zipcodes', postgresql.JSONB(), server_default='[]', nullable=True))
    op.add_column('products', sa.Column('in_stock_zipcodes', postgresql.JSONB(), server_default='[]', nullable=True))
    op.add_column('products', sa.Column('all_zipcodes', postgresql.JSONB(), server_default='[]', nullable=True))
    
    op.create_index('ix_products_available_zipcodes', 'products', ['available_zipcodes'], unique=False, postgresql_using='gin')
    op.create_index('ix_products_in_stock_zipcodes', 'products', ['in_stock_zipcodes'], unique=False, postgresql_using='gin')
    
    op.drop_column('products', 'zipcode')


def downgrade() -> None:
    op.add_column('products', sa.Column('zipcode', sa.String(length=20), server_default='', nullable=True))
    
    op.drop_index('ix_products_available_zipcodes', table_name='products')
    op.drop_index('ix_products_in_stock_zipcodes', table_name='products')
    op.drop_column('products', 'all_zipcodes')
    op.drop_column('products', 'in_stock_zipcodes')
    op.drop_column('products', 'available_zipcodes') 