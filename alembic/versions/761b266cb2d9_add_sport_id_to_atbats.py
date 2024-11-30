"""Add sport id to AtBats

Revision ID: 761b266cb2d9
Revises: c6def68ae504
Create Date: 2024-11-30 11:54:12.835123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '761b266cb2d9'
down_revision: Union[str, None] = 'c6def68ae504'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('at_bats', sa.Column('sport_id', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('at_bats', 'sport_id')
    # ### end Alembic commands ###
