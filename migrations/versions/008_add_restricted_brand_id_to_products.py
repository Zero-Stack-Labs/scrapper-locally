"""Add restricted_brand_id to products

Revision ID: 008
Revises: 007
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', 
        sa.Column('restricted_brand_id', sa.String(255), nullable=True)
    )


def downgrade():
    op.drop_column('products', 'restricted_brand_id') 