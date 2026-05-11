"""drop feed_vehicle_id, last_seen_at, cache_expires_at from rt_vehicle

The cache was predicated on saving API calls, but I did not realize there is no other easy way
how to fetch route_origin_name/run_number... Reverting the schema.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-11 13:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("rt_vehicle", "cache_expires_at")
    op.drop_column("rt_vehicle", "last_seen_at")
    op.drop_index("ix_rt_vehicle_feed_vehicle_id", "rt_vehicle")
    op.drop_column("rt_vehicle", "feed_vehicle_id")


def downgrade() -> None:
    op.add_column("rt_vehicle", sa.Column("feed_vehicle_id", sa.String(), nullable=True))
    op.create_index("ix_rt_vehicle_feed_vehicle_id", "rt_vehicle", ["feed_vehicle_id"])
    op.add_column("rt_vehicle", sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("rt_vehicle", sa.Column("cache_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE rt_vehicle SET cache_expires_at = now() + (random() * interval '5 days') + interval '5 days'")
    op.alter_column("rt_vehicle", "cache_expires_at", nullable=False)
