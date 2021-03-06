"""Graphite SeparateInstances

Revision ID: 987305d75e3a
Revises: d20ab6a17489
Create Date: 2019-11-20 00:04:21.095499+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '987305d75e3a'
down_revision = 'd20ab6a17489'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('system_reporting', schema=None) as batch_op:
        batch_op.add_column(sa.Column('graphite_separateinstances', sa.Boolean(), nullable=True))

    op.execute("UPDATE system_reporting SET graphite_separateinstances = 0")

    with op.batch_alter_table('system_reporting', schema=None) as batch_op:
        batch_op.alter_column('graphite_separateinstances',
               existing_type=sa.BOOLEAN(),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('system_reporting', schema=None) as batch_op:
        batch_op.drop_column('graphite_separateinstances')

    # ### end Alembic commands ###
