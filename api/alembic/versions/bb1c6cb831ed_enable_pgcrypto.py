"""enable pgcrypto extension

Revision ID: bb1c6cb831ed
Revises: 
Create Date: 2026-05-05

"""
from typing import Sequence, Union

from alembic import op

revision: str = "bb1c6cb831ed"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgcrypto provides gen_random_uuid() used as server-side UUID default
    # on all non-hypertable primary keys.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
