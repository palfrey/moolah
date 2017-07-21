"""Fix types for currency/value

Revision ID: c586fd48cbf4
Revises: 41e781d0952d
Create Date: 2017-07-21 15:55:20.419747

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c586fd48cbf4'
down_revision = '41e781d0952d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('expense') as batch_op:
        batch_op.alter_column('original_currency', type_=sa.String())
        batch_op.alter_column('original_value', type_=sa.Float())


def downgrade():
    with op.batch_alter_table('expense') as batch_op:
        batch_op.alter_column('original_currency', type_=sa.Integer())
        batch_op.alter_column('original_value', type_=sa.Integer())
