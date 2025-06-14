"""create products table

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('products',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('record_type', sa.String(length=50), nullable=True),
    sa.Column('provider_id', sa.String(length=255), nullable=True),
    sa.Column('external_id', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=500), nullable=False),
    sa.Column('brand', sa.String(length=255), nullable=True),
    sa.Column('url', sa.Text(), nullable=True),
    sa.Column('sku', sa.String(length=255), nullable=True),
    sa.Column('images', sa.JSON(), nullable=True),
    sa.Column('external_sell_price', sa.Float(), nullable=True),
    sa.Column('currency', sa.String(length=10), nullable=True),
    sa.Column('condition', sa.String(length=100), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('variants', sa.JSON(), nullable=True),
    sa.Column('variants_count', sa.Integer(), nullable=True),
    sa.Column('images_count', sa.Integer(), nullable=True),
    sa.Column('page_number', sa.Integer(), nullable=True),
    sa.Column('store_id', sa.String(length=255), nullable=True),
    sa.Column('lat', sa.Float(), nullable=True),
    sa.Column('lng', sa.Float(), nullable=True),
    sa.Column('zipcode', sa.String(length=20), nullable=True),
    sa.Column('store_name', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_external_id'), 'products', ['external_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_products_external_id'), table_name='products')
    op.drop_table('products') 