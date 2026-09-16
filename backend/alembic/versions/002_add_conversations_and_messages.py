"""Add conversations and messages tables for persistent multi-conversation AI Advisor

Revision ID: 002_add_conversations_and_messages
Revises: 001_initial_database_foundation
Create Date: 2026-09-16 18:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_add_conversations_and_messages'
down_revision: Union[str, None] = '001_initial_database_foundation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Conversations Table
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False, server_default='New Chat'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_conversations_id', 'conversations', ['id'])
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('ix_conversations_updated_at', 'conversations', ['updated_at'])

    # 2. Messages Table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender', sa.String(length=32), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('meta_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_messages_id', 'messages', ['id'])
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])


def downgrade() -> None:
    op.drop_table('messages')
    op.drop_table('conversations')
