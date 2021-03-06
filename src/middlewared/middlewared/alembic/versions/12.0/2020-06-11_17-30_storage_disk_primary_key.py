"""storage_disk primary key

Revision ID: 8ac8158773c4
Revises: 5a365c7248da
Create Date: 2020-06-11 17:30:51.913706+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8ac8158773c4'
down_revision = '5a365c7248da'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    conn = op.get_bind()
    for disk_identifier, count in conn.execute("""
        SELECT disk_identifier, COUNT(*)
        FROM storage_disk
        GROUP BY disk_identifier
        HAVING COUNT(*) > 1
    """).fetchall():
        conn.execute("""
            DELETE FROM storage_disk
            WHERE ROWID IN (
                SELECT ROWID
                FROM storage_disk
                WHERE disk_identifier = ?
                LIMIT ?
            )
        """, [disk_identifier, count - 1])

    with op.batch_alter_table('storage_disk', schema=None) as batch_op:
        batch_op.create_primary_key('pk_storage_disk', ['disk_identifier'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
