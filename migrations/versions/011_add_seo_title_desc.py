"""Add external_compare_at_price and external_discount to products

Revision ID: 009
Revises: 008
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products',
                  sa.Column('seo_title', sa.String(length=500), nullable=True),
                  )
    op.add_column('products',
                  sa.Column('seo_description', sa.String(length=500), nullable=True),
                  )


def downgrade():
    op.drop_column('products', 'seo_title')
    op.drop_column('products', 'seo_description')
