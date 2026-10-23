"""initial music_jobs table migration

Revision ID: 001_initial
Revises: 
Create Date: 2026-10-23 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'music_jobs',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('request_hash', sa.String(length=64), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('duration_s', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='queued'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('request_json', sa.Text(), nullable=False),
        sa.Column('result_urls_json', sa.Text(), nullable=True),
        sa.Column('manifest_json', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_music_jobs_idempotency_key'), 'music_jobs', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_music_jobs_status'), 'music_jobs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_music_jobs_status'), table_name='music_jobs')
    op.drop_index(op.f('ix_music_jobs_idempotency_key'), table_name='music_jobs')
    op.drop_table('music_jobs')
