"""store comment id

Revision ID: e7905951b186
Revises: fec0d6350b1f
Create Date: 2017-07-22 19:10:15.397137

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7905951b186'
down_revision = 'fec0d6350b1f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('expense', sa.Column('comment_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('expense', 'comment_id')

