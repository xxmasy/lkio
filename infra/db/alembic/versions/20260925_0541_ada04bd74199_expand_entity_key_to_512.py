"""expand_entity_key_to_512

Revision ID: ada04bd74199
Revises: 78079f581423
Create Date: 2026-09-25 05:41:31.565351+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ada04bd74199'
down_revision: Union[str, Sequence[str], None] = '78079f581423'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'entities',
        'entity_key',
        existing_type=sa.String(length=255),
        type_=sa.String(length=512),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'entities',
        'entity_key',
        existing_type=sa.String(length=512),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
