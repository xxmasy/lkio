"""upgrade_relations_for_mvp2_c

Revision ID: e6b219ca0123
Revises: c5cab8886f85
Create Date: 2026-09-26 18:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e6b219ca0123'
down_revision: Union[str, Sequence[str], None] = 'c5cab8886f85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop existing triple unique constraint
    op.drop_constraint('uq_relations_triple', 'relations', type_='unique')

    # 2. Make object_entity_id nullable
    op.alter_column(
        'relations',
        'object_entity_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # 3. Add relation_key (TEXT UNIQUE NOT NULL)
    op.add_column(
        'relations',
        sa.Column('relation_key', sa.Text(), nullable=True),
    )
    # Populate existing rows with a deterministic fallback key if any exist
    op.execute(
        "UPDATE relations SET relation_key = 'RELATION:' || subject_entity_id || ':' || predicate || ':' || COALESCE(object_entity_id::text, 'null') || ':STATIC:default' WHERE relation_key IS NULL"
    )
    op.alter_column('relations', 'relation_key', nullable=False)
    op.create_index('ix_relations_relation_key', 'relations', ['relation_key'], unique=True)

    # 4. Add relation_kind, resolution_status, raw_target, status, occurrences
    op.add_column('relations', sa.Column('relation_kind', sa.String(length=32), nullable=False, server_default='STATIC'))
    op.add_column('relations', sa.Column('resolution_status', sa.String(length=32), nullable=False, server_default='RESOLVED'))
    op.add_column('relations', sa.Column('raw_target', sa.Text(), nullable=False, server_default=''))
    op.add_column('relations', sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'))
    op.add_column('relations', sa.Column('occurrences', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))

    # 5. Create index for subject_entity_id and predicate
    op.create_index('ix_relations_subject_predicate', 'relations', ['subject_entity_id', 'predicate'], unique=False)
    op.create_index('ix_relations_status', 'relations', ['status'], unique=False)
    op.create_index('ix_relations_relation_kind', 'relations', ['relation_kind'], unique=False)
    op.create_index('ix_relations_resolution_status', 'relations', ['resolution_status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_relations_resolution_status', table_name='relations')
    op.drop_index('ix_relations_relation_kind', table_name='relations')
    op.drop_index('ix_relations_status', table_name='relations')
    op.drop_index('ix_relations_subject_predicate', table_name='relations')
    op.drop_index('ix_relations_relation_key', table_name='relations')

    op.drop_column('relations', 'occurrences')
    op.drop_column('relations', 'status')
    op.drop_column('relations', 'raw_target')
    op.drop_column('relations', 'resolution_status')
    op.drop_column('relations', 'relation_kind')
    op.drop_column('relations', 'relation_key')

    op.alter_column(
        'relations',
        'object_entity_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_unique_constraint('uq_relations_triple', 'relations', ['subject_entity_id', 'predicate', 'object_entity_id'])
