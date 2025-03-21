"""Make debut and last played date fields nullable

Revision ID: f8efb8336a15
Revises: cd35b9396032
Create Date: 2024-10-16 22:36:15.294006

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8efb8336a15'
down_revision: Union[str, None] = 'cd35b9396032'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('players', 'mlb_debut_date',
               existing_type=sa.DATE(),
               nullable=True)
    op.alter_column('players', 'last_played_date',
               existing_type=sa.DATE(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('players', 'last_played_date',
               existing_type=sa.DATE(),
               nullable=False)
    op.alter_column('players', 'mlb_debut_date',
               existing_type=sa.DATE(),
               nullable=False)
    # ### end Alembic commands ###
