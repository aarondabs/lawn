"""phase 3: assistant conversation persistence

Revision ID: b3d7f2a91c45
Revises: a7c4e91b52d8
Create Date: 2026-08-31

Chat and briefing transcripts for the read-only assistant. A conversation's
kind ('chat' | 'briefing') lets the UI filter scheduled briefings out of the
chat list while keeping them continuable as normal conversations -- the
operator-confirmed design (2026-08-31 amendments to the Phase 3 handoff).

Messages store rendered text only; the system prompt and context bundle are
rebuilt per request, never persisted. Token counts on assistant turns feed
cost visibility.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3d7f2a91c45"
down_revision: Union[str, None] = "a7c4e91b52d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assistant_conversation",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("kind", sa.Text(), server_default=sa.text("'chat'"), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("kind IN ('chat', 'briefing')", name="assistant_conversation_kind_check"),
    )
    op.create_table(
        "assistant_message",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        # Monotonic insertion order. created_at cannot order turns: now() is
        # transaction start time, so both halves of an exchange tie.
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["assistant_conversation.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="assistant_message_role_check"),
    )
    op.create_index("ix_assistant_message_conversation_seq", "assistant_message", ["conversation_id", "seq"])


def downgrade() -> None:
    op.drop_index("ix_assistant_message_conversation_seq", table_name="assistant_message")
    op.drop_table("assistant_message")
    op.drop_table("assistant_conversation")
