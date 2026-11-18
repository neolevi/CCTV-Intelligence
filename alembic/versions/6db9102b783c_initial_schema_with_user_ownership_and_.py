"""Initial schema with user ownership and foreign keys

Revision ID: 6db9102b783c
Revises: 
Create Date: 2026-11-17 14:37:33.301591

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6db9102b783c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: robustly handles both fresh databases and non-destructive upgrades of existing databases."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # 1. Fresh database creation: create tables if they do not exist
    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
            sa.Column("hashed_password", sa.String(255), nullable=False),
            sa.Column("full_name", sa.String(255), nullable=True),
            sa.Column("role", sa.String(50), default="operator"),
            sa.Column("is_active", sa.Boolean(), default=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
    if "cameras" not in tables:
        op.create_table(
            "cameras",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("device_index", sa.Integer(), default=0),
            sa.Column("rtsp_url", sa.String(512), nullable=True),
            sa.Column("resolution_width", sa.Integer(), default=640),
            sa.Column("resolution_height", sa.Integer(), default=480),
            sa.Column("fps", sa.Integer(), default=30),
            sa.Column("is_connected", sa.Boolean(), default=False),
            sa.Column("status", sa.String(50), default="standby"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
    if "monitoring_sessions" not in tables:
        op.create_table(
            "monitoring_sessions",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
            sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False, index=True),
            sa.Column("start_time", sa.DateTime(), nullable=False, index=True),
            sa.Column("end_time", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(50), default="active"),
            sa.Column("total_frames", sa.Integer(), default=0),
            sa.Column("active_duration_seconds", sa.Float(), default=0.0),
            sa.Column("idle_duration_seconds", sa.Float(), default=0.0),
            sa.Column("deep_idle_duration_seconds", sa.Float(), default=0.0),
        )
    if "motion_events" not in tables:
        op.create_table(
            "motion_events",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
            sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False, index=True),
            sa.Column("session_id", sa.Integer(), sa.ForeignKey("monitoring_sessions.id"), nullable=True, index=True),
            sa.Column("start_time", sa.DateTime(), nullable=False, index=True),
            sa.Column("end_time", sa.DateTime(), nullable=True),
            sa.Column("peak_motion_score", sa.Float(), default=0.0),
            sa.Column("activity_state", sa.String(50), default="ACTIVE"),
            sa.Column("frame_count", sa.Integer(), default=0),
            sa.Column("thumbnail_path", sa.String(512), nullable=True),
            sa.Column("description", sa.String(255), nullable=True),
        )
    if "captured_frames" not in tables:
        op.create_table(
            "captured_frames",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
            sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False, index=True),
            sa.Column("session_id", sa.Integer(), sa.ForeignKey("monitoring_sessions.id"), nullable=True, index=True),
            sa.Column("event_id", sa.Integer(), sa.ForeignKey("motion_events.id"), nullable=True, index=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False, index=True),
            sa.Column("activity_state", sa.String(50), default="IDLE"),
            sa.Column("file_path", sa.String(512), nullable=False),
            sa.Column("file_size_bytes", sa.Integer(), default=0),
            sa.Column("motion_score", sa.Float(), default=0.0),
        )
    if "recordings" not in tables:
        op.create_table(
            "recordings",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
            sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False, index=True),
            sa.Column("session_id", sa.Integer(), sa.ForeignKey("monitoring_sessions.id"), nullable=True, index=True),
            sa.Column("event_id", sa.Integer(), sa.ForeignKey("motion_events.id"), nullable=True, index=True),
            sa.Column("start_time", sa.DateTime(), nullable=False, index=True),
            sa.Column("end_time", sa.DateTime(), nullable=True),
            sa.Column("duration_seconds", sa.Float(), default=0.0),
            sa.Column("file_path", sa.String(512), nullable=False),
            sa.Column("file_size_bytes", sa.Integer(), default=0),
            sa.Column("thumbnail_path", sa.String(512), nullable=True),
            sa.Column("activity_state", sa.String(50), default="ACTIVE"),
        )
    if "daily_summaries" not in tables:
        op.create_table(
            "daily_summaries",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
            sa.Column("date", sa.String(10), index=True, nullable=False),
            sa.Column("total_monitoring_seconds", sa.Float(), default=0.0),
            sa.Column("active_seconds", sa.Float(), default=0.0),
            sa.Column("idle_seconds", sa.Float(), default=0.0),
            sa.Column("deep_idle_seconds", sa.Float(), default=0.0),
            sa.Column("total_motion_events", sa.Integer(), default=0),
            sa.Column("total_frames_captured", sa.Integer(), default=0),
            sa.Column("total_frames_saved", sa.Integer(), default=0),
            sa.Column("storage_consumed_bytes", sa.Integer(), default=0),
            sa.Column("first_activity_time", sa.DateTime(), nullable=True),
            sa.Column("last_activity_time", sa.DateTime(), nullable=True),
            sa.Column("peak_activity_hour", sa.Integer(), nullable=True),
            sa.Column("narrative_summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "date", name="uq_user_daily_summary"),
        )
    if "settings" not in tables:
        op.create_table(
            "settings",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("key", sa.String(100), unique=True, index=True, nullable=False),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )

    # 2. Existing database migration: add missing columns if upgrading an existing DB
    tables = inspector.get_table_names()
    columns_to_add = {
        "cameras": [("user_id", sa.Integer(), sa.ForeignKey("users.id"))],
        "monitoring_sessions": [("user_id", sa.Integer(), sa.ForeignKey("users.id"))],
        "motion_events": [("user_id", sa.Integer(), sa.ForeignKey("users.id"))],
        "captured_frames": [
            ("user_id", sa.Integer(), sa.ForeignKey("users.id")),
            ("file_size_bytes", sa.Integer(), None),
        ],
        "recordings": [("user_id", sa.Integer(), sa.ForeignKey("users.id"))],
        "daily_summaries": [("user_id", sa.Integer(), sa.ForeignKey("users.id"))],
    }

    for table_name, cols in columns_to_add.items():
        if table_name in tables:
            existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
            for col_info in cols:
                col_name = col_info[0]
                col_type = col_info[1]
                fk = col_info[2] if len(col_info) > 2 else None
                if col_name not in existing_cols:
                    if fk:
                        op.add_column(table_name, sa.Column(col_name, col_type, fk, nullable=True))
                    else:
                        op.add_column(table_name, sa.Column(col_name, col_type, server_default="0", nullable=True))

    # Migrate daily_summaries index from unique(date) to unique(user_id, date) on existing databases
    if "daily_summaries" in tables:
        try:
            op.execute("DROP INDEX IF EXISTS ix_daily_summaries_date")
            op.execute("CREATE INDEX IF NOT EXISTS ix_daily_summaries_date ON daily_summaries (date)")
            op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_daily_summary ON daily_summaries (user_id, date)")
        except Exception:
            pass


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_recordings_user_id'), table_name='recordings')
    op.drop_index(op.f('ix_motion_events_user_id'), table_name='motion_events')
    op.drop_index(op.f('ix_monitoring_sessions_user_id'), table_name='monitoring_sessions')
    op.drop_index(op.f('ix_captured_frames_user_id'), table_name='captured_frames')
    op.drop_index(op.f('ix_cameras_user_id'), table_name='cameras')
    # ### end Alembic commands ###
