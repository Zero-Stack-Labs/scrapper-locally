"""add category tags options and coupon fields

Revision ID: 006
Revises: 005
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add category column
    op.add_column('products', sa.Column('category', sa.String(length=500), nullable=True, server_default=''))
    
    # Add tags column as JSONB
    op.add_column('products', sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    
    # Add options column as JSONB
    op.add_column('products', sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    
    # Add coupon fields
    op.add_column('products', sa.Column('coupon_code', sa.String(length=255), nullable=True, server_default=''))
    op.add_column('products', sa.Column('coupon_code_discount', sa.Float(), nullable=True, server_default='0.0'))


def downgrade() -> None:
    # Remove the added columns
    op.drop_column('products', 'coupon_code_discount')
    op.drop_column('products', 'coupon_code')
    op.drop_column('products', 'options')
    op.drop_column('products', 'tags')
    op.drop_column('products', 'category') 