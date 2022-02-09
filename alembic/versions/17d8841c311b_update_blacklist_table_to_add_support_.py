"""Update blacklist table to add support for custom blacklist mode

Revision ID: 17d8841c311b
Revises: 
Create Date: 2022-02-08 23:00:02.784212

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '17d8841c311b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('blacklist', sa.Column('custom_mode', sa.UnicodeText, default=None))


def downgrade():
    pass
