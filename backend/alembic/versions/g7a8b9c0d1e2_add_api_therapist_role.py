"""add api_therapist role

Revision ID: g7a8b9c0d1e2
Revises: 0644ef70f268
Create Date: 2026-08-31 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g7a8b9c0d1e2'
down_revision = '0644ef70f268'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE roleenum ADD VALUE IF NOT EXISTS 'api_therapist'")

def downgrade() -> None:
    # PostgreSQL does not easily support removing a value from an enum type.
    pass
