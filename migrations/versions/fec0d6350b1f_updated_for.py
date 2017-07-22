"""Add updated_for

Revision ID: fec0d6350b1f
Revises: c586fd48cbf4
Create Date: 2017-07-22 18:54:37.924305

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fec0d6350b1f'
down_revision = 'c586fd48cbf4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('expense', sa.Column('updated_for', sa.Integer(), nullable=False, server_default=sa.text("id")))


def downgrade():
    op.drop_column('expense', 'updated_for')
