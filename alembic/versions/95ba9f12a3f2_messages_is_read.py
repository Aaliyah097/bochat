"""messages_is_read

Revision ID: 95ba9f12a3f2
Revises: c0a079e2cea9
Create Date: 2024-02-25 17:54:34.686836

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95ba9f12a3f2'
down_revision: Union[str, None] = 'c0a079e2cea9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('messages', sa.Column('is_read', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('messages', 'is_read')
    # ### end Alembic commands ###
