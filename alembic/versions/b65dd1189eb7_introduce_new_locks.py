"""Introduce new locks

Revision ID: b65dd1189eb7
Revises: 17d8841c311b
Create Date: 2022-07-03 01:16:39.455210

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b65dd1189eb7'
down_revision = '17d8841c311b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('permissions', sa.Column('premiumsticker', sa.Boolean, default=False))
    op.add_column('permissions', sa.Column('animatedsticker', sa.Boolean, default=False))
    op.add_column('permissions', sa.Column('videosticker', sa.Boolean, default=False))


def downgrade():
    pass
