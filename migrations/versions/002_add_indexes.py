"""add indexes

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_products_external_id_provider_id', 'products', ['external_id', 'provider_id'], unique=True)
    op.create_index('ix_products_provider_id', 'products', ['provider_id'], unique=False)
    op.create_index('ix_products_store_id', 'products', ['store_id'], unique=False)
    op.create_index('ix_products_store_name', 'products', ['store_name'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_products_store_name', table_name='products')
    op.drop_index('ix_products_store_id', table_name='products')
    op.drop_index('ix_products_provider_id', table_name='products')
    op.drop_index('ix_products_external_id_provider_id', table_name='products') 