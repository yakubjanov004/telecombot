import logging
from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)


def migrate_schema(sync_conn) -> None:
    """Apply lightweight PostgreSQL migrations for columns added after initial deploy."""
    inspector = inspect(sync_conn)
    table_names = set(inspector.get_table_names())
    if "chat_sessions" not in table_names:
        return

    columns = {c["name"] for c in inspector.get_columns("chat_sessions")}
    if "topic_created_at" not in columns:
        sync_conn.execute(
            text("ALTER TABLE chat_sessions ADD COLUMN topic_created_at TIMESTAMP WITH TIME ZONE")
        )
        logger.info("Added chat_sessions.topic_created_at column.")
    if "topic_expires_at" not in columns:
        sync_conn.execute(
            text("ALTER TABLE chat_sessions ADD COLUMN topic_expires_at TIMESTAMP WITH TIME ZONE")
        )
        logger.info("Added chat_sessions.topic_expires_at column.")

    if "internet_applications" in table_names:
        columns = {c["name"] for c in inspector.get_columns("internet_applications")}
        for name, ddl in {
            "branches": "VARCHAR(255)",
            "departments": "VARCHAR(255)",
            "navi_user": "VARCHAR(120)",
            "rt_lc_states": "VARCHAR(50)",
            "msisdn": "VARCHAR(100)",
            "rate_plan_first_connection": "VARCHAR(255)",
        }.items():
            if name not in columns:
                sync_conn.execute(
                    text(f"ALTER TABLE internet_applications ADD COLUMN {name} {ddl}")
                )
                logger.info("Added internet_applications.%s column.", name)

    if "mobile_applications" in table_names:
        columns = {c["name"] for c in inspector.get_columns("mobile_applications")}
        for name, ddl in {
            "dealer": "VARCHAR(255)",
            "navi_user": "VARCHAR(120)",
            "msisdn": "VARCHAR(100)",
            "rate_plan_first_connection": "VARCHAR(255)",
            "branches": "VARCHAR(255)",
        }.items():
            if name not in columns:
                sync_conn.execute(
                    text(f"ALTER TABLE mobile_applications ADD COLUMN {name} {ddl}")
                )
                logger.info("Added mobile_applications.%s column.", name)
