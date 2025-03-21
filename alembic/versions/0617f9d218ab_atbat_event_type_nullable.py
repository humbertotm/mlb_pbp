"""AtBat.event_type nullable

Revision ID: 0617f9d218ab
Revises: 85cfd3a8f9f4
Create Date: 2024-12-03 21:59:39.878746

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0617f9d218ab'
down_revision: Union[str, None] = '85cfd3a8f9f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('at_bats', 'event_type',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('at_bats', 'event_type',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###
