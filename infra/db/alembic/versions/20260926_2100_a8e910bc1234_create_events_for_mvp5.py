"""create_events_for_mvp5

Revision ID: a8e910bc1234
Revises: f7d3a812b345
Create Date: 2026-09-26 21:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a8e910bc1234'
down_revision: Union[str, Sequence[str], None] = 'f7d3a812b345'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_key', sa.Text(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.id', ondelete='SET NULL'), nullable=True),
        sa.Column('actor_type', sa.String(length=32), nullable=False, server_default='git'),
        sa.Column('actor_id', sa.String(length=255), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('before_state', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('after_state', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(length=64), nullable=False, server_default='git_commit'),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_events_event_key', 'events', ['event_key'], unique=True)
    op.create_index('ix_events_event_type', 'events', ['event_type'])
    op.create_index('ix_events_project_id', 'events', ['project_id'])
    op.create_index('ix_events_entity_id', 'events', ['entity_id'])
    op.create_index('ix_events_timestamp', 'events', ['timestamp'])
    op.create_index('ix_events_project_timestamp', 'events', ['project_id', 'timestamp'])


def downgrade() -> None:
    op.drop_index('ix_events_project_timestamp', table_name='events')
    op.drop_index('ix_events_timestamp', table_name='events')
    op.drop_index('ix_events_entity_id', table_name='events')
    op.drop_index('ix_events_project_id', table_name='events')
    op.drop_index('ix_events_event_type', table_name='events')
    op.drop_index('ix_events_event_key', table_name='events')
    op.drop_table('events')
