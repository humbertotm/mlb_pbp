"""Add created_at/updated_at index on Player table

Revision ID: 1ce0a5774253
Revises: 2951f7949746
Create Date: 2025-03-15 16:27:48.999534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ce0a5774253'
down_revision: Union[str, None] = '2951f7949746'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('idx_player_created_at', 'players', ['created_at'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('idx_player_created_at', table_name='players')
    # ### end Alembic commands ###
