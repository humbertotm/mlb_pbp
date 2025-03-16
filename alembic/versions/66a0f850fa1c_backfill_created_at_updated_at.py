"""Backfill created_at/updated_at

Revision ID: 66a0f850fa1c
Revises: 12ff0f461eb8
Create Date: 2025-03-16 11:58:19.509201

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66a0f850fa1c'
down_revision: Union[str, None] = '12ff0f461eb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tables = ['players', 'teams', 'games']
    batch_size = 10000
    
    connection = op.get_bind()
    
    try:
        for table in tables:
            print(f"\nProcessing table {table}...")
            
            # Count total records needing update
            result = connection.execute(sa.text(
                f"SELECT COUNT(*) FROM {table} WHERE created_at IS NULL OR updated_at IS NULL"
            ))
            total = result.scalar()
            print(f"Found {total} records to update in {table}")
            
            if total == 0:
                continue
                
            # Update in batches
            updated = 0
            while True:
                result = connection.execute(sa.text(
                    f"""
                    UPDATE {table} 
                    SET created_at = CURRENT_TIMESTAMP, 
                        updated_at = CURRENT_TIMESTAMP 
                    WHERE id IN (
                        SELECT id 
                        FROM {table} 
                        WHERE created_at IS NULL 
                        OR updated_at IS NULL 
                        ORDER BY id 
                        LIMIT :batch_size
                    )
                    """
                ), {'batch_size': batch_size})
                
                if result.rowcount == 0:
                    break
                    
                updated += result.rowcount
                print(f"Updated {updated}/{total} records in {table}")
                
    except Exception as e:
        print(f"Error occurred: {e}")
        raise


def downgrade() -> None:
    pass
