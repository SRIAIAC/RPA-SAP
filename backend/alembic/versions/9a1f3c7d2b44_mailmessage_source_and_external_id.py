"""mailmessage source + external_id (Gmail import support)

Revision ID: 9a1f3c7d2b44
Revises: 24e4ba8f4fd2
Create Date: 2026-08-19 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '9a1f3c7d2b44'
down_revision: Union[str, None] = '24e4ba8f4fd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'mailmessage',
        sa.Column('source', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='seed'),
    )
    op.alter_column('mailmessage', 'source', server_default=None)
    op.add_column(
        'mailmessage',
        sa.Column('external_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.create_index(op.f('ix_mailmessage_external_id'), 'mailmessage', ['external_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_mailmessage_external_id'), table_name='mailmessage')
    op.drop_column('mailmessage', 'external_id')
    op.drop_column('mailmessage', 'source')
