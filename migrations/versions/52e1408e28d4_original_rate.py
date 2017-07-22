"""original rate

Revision ID: 52e1408e28d4
Revises: e7905951b186
Create Date: 2017-07-22 19:50:08.252548

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '52e1408e28d4'
down_revision = 'e7905951b186'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('expense', sa.Column('original_rate', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('expense', 'original_rate')
