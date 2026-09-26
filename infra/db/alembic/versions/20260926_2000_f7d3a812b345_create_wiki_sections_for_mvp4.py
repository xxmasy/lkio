"""create_wiki_sections_for_mvp4

Revision ID: f7d3a812b345
Revises: e6b219ca0123
Create Date: 2026-09-26 20:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f7d3a812b345'
down_revision: Union[str, Sequence[str], None] = 'e6b219ca0123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'wiki_sections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=True),
        sa.Column('project_key', sa.String(length=64), nullable=False),
        sa.Column('section_key', sa.Text(), nullable=False),
        sa.Column('section_name', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source_entity_keys', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('source_relation_keys', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('source_document_paths', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('source_commit_hashes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('evidence_citations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('model', sa.String(length=64), nullable=False, server_default='deterministic-synthesizer'),
        sa.Column('prompt_version', sa.String(length=32), nullable=False, server_default='v1.0'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='GENERATED'),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_wiki_sections_project_id', 'wiki_sections', ['project_id'])
    op.create_index('ix_wiki_sections_project_key', 'wiki_sections', ['project_key'])
    op.create_index('ix_wiki_sections_section_key', 'wiki_sections', ['section_key'], unique=True)
    op.create_index('ix_wiki_sections_section_name', 'wiki_sections', ['section_name'])


def downgrade() -> None:
    op.drop_index('ix_wiki_sections_section_name', table_name='wiki_sections')
    op.drop_index('ix_wiki_sections_section_key', table_name='wiki_sections')
    op.drop_index('ix_wiki_sections_project_key', table_name='wiki_sections')
    op.drop_index('ix_wiki_sections_project_id', table_name='wiki_sections')
    op.drop_table('wiki_sections')
