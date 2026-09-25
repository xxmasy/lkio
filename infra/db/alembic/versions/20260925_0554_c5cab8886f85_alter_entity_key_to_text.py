"""alter_entity_key_to_text

Revision ID: c5cab8886f85
Revises: ada04bd74199
Create Date: 2026-09-25 05:54:59.688275+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c5cab8886f85'
down_revision: Union[str, Sequence[str], None] = 'ada04bd74199'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'entities',
        'entity_key',
        existing_type=sa.String(length=512),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'entities',
        'entity_key',
        existing_type=sa.Text(),
        type_=sa.String(length=512),
        existing_nullable=False,
    )
