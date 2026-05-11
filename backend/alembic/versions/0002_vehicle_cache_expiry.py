"""add last_seen_at and cache_expires_at to rt_vehicle

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-11 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rt_vehicle", sa.Column("feed_vehicle_id", sa.String(), nullable=True))
    op.create_index("ix_rt_vehicle_feed_vehicle_id", "rt_vehicle", ["feed_vehicle_id"])
    op.execute("""
        UPDATE rt_vehicle v
        SET feed_vehicle_id = t.feed_vehicle_id
        FROM (
            SELECT DISTINCT ON (vehicle_id) vehicle_id, feed_vehicle_id
            FROM rt_trip
            WHERE vehicle_id IS NOT NULL AND feed_vehicle_id IS NOT NULL
            ORDER BY vehicle_id, updated_at DESC
        ) t
        WHERE v.vehicle_id = t.vehicle_id
    """)
    op.add_column("rt_vehicle", sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("rt_vehicle", sa.Column("cache_expires_at", sa.DateTime(timezone=True), nullable=True))
    # Backfill existing rows with a randomized expiry in [5, 10] days from now
    # so the first refresh wave is spread across a 5-day window rather than all
    # expiring at the same instant.
    op.execute("UPDATE rt_vehicle SET cache_expires_at = now() + (random() * interval '5 days') + interval '5 days'")
    op.alter_column("rt_vehicle", "cache_expires_at", nullable=False)


def downgrade() -> None:
    op.drop_column("rt_vehicle", "cache_expires_at")
    op.drop_column("rt_vehicle", "last_seen_at")
    op.drop_index("ix_rt_vehicle_feed_vehicle_id", "rt_vehicle")
    op.drop_column("rt_vehicle", "feed_vehicle_id")
