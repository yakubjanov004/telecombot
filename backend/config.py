import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env.example"))
load_dotenv(os.path.join(project_root, ".env"), override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_GROUP_ID = os.getenv("CHAT_GROUP_ID")


def _first_env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()
    return default


def _postgres_url_from_env() -> str | None:
    database = _first_env("POSTGRES_DB", "DB_NAME", "PGDATABASE")
    if not database:
        return None

    return URL.create(
        "postgresql+asyncpg",
        username=_first_env("POSTGRES_USER", "PGUSER", default="postgres"),
        password=_first_env("POSTGRES_PASSWORD", "PGPASSWORD"),
        host=_first_env("POSTGRES_HOST", "PGHOST", default="localhost"),
        port=int(_first_env("POSTGRES_PORT", "PGPORT", default="5432") or "5432"),
        database=database,
    ).render_as_string(hide_password=False)


def _normalize_database_url(value: str) -> str:
    value = value.strip()
    if value.startswith("postgresql://"):
        value = value.replace("postgresql://", "postgresql+asyncpg://", 1)

    url = make_url(value)
    if not url.drivername.startswith("postgresql"):
        raise RuntimeError(
            "DATABASE_URL must point to PostgreSQL. Use "
            "postgresql+asyncpg://user:password@host:5432/database_name "
            "or set POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD."
        )
    return url.render_as_string(hide_password=False)


DATABASE_URL = os.getenv("DATABASE_URL")
POSTGRES_DATABASE_URL = _postgres_url_from_env()

if DATABASE_URL and DATABASE_URL.strip():
    DATABASE_URL = _normalize_database_url(DATABASE_URL)
elif POSTGRES_DATABASE_URL:
    DATABASE_URL = POSTGRES_DATABASE_URL
else:
    raise RuntimeError("PostgreSQL config not found. Add DATABASE_URL or POSTGRES_DB settings to .env.")

INTERNET_TOPIC_ID = os.getenv("INTERNET_TOPIC_ID", "6")
MOBILE_TOPIC_ID = os.getenv("MOBILE_TOPIC_ID", "8")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8100"))
BOT_WEBHOOK_PATH = os.getenv("BOT_WEBHOOK_PATH", "/bot/webhook")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
CLIENT_RATE_LIMIT_SECONDS = int(os.getenv("CLIENT_RATE_LIMIT_SECONDS", "1"))
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

ADMINS = os.getenv("ADMINS", "[]")
OPERATOR_PASSWORD = os.getenv("OPERATOR_PASSWORD", "123")
MANAGER_PASSWORD = os.getenv("MANAGER_PASSWORD", "456")
SUPPORT_GROUP_ID = os.getenv("SUPPORT_GROUP_ID")
if not SUPPORT_GROUP_ID and CHAT_GROUP_ID:
    SUPPORT_GROUP_ID = CHAT_GROUP_ID

BASE_DIR = project_root

USERBOT_API_ID = os.getenv("API_ID")
USERBOT_API_HASH = os.getenv("API_HASH")
USERBOT_PHONE = os.getenv("PHONE_NUMBER")
USERBOT_SESSION_NAME = os.getenv("SESSION_NAME", "storage/sessions/fake_client_session")
SCENARIOS_DIR = os.path.join(project_root, "assets", "scenarios")
FAKE_ENABLED = os.getenv("FAKE_ENABLED", "false").lower() == "true"

FAKE_TARGET_LOW_MIN = int(os.getenv("FAKE_TARGET_LOW_MIN", "5"))
FAKE_TARGET_LOW_MAX = int(os.getenv("FAKE_TARGET_LOW_MAX", "10"))
FAKE_TARGET_MEDIUM_MIN = int(os.getenv("FAKE_TARGET_MEDIUM_MIN", "15"))
FAKE_TARGET_MEDIUM_MAX = int(os.getenv("FAKE_TARGET_MEDIUM_MAX", "20"))
FAKE_TARGET_PEAK_MIN = int(os.getenv("FAKE_TARGET_PEAK_MIN", "30"))
FAKE_TARGET_PEAK_MAX = int(os.getenv("FAKE_TARGET_PEAK_MAX", "30"))
FAKE_TARGET_ROTATE_MIN_MINUTES = int(os.getenv("FAKE_TARGET_ROTATE_MIN_MINUTES", "20"))
FAKE_TARGET_ROTATE_MAX_MINUTES = int(os.getenv("FAKE_TARGET_ROTATE_MAX_MINUTES", "45"))
FAKE_INTERVAL_MIN_SEC = int(os.getenv("FAKE_INTERVAL_MIN_SEC", "120"))
FAKE_INTERVAL_MAX_SEC = int(os.getenv("FAKE_INTERVAL_MAX_SEC", "300"))
FAKE_STEP_TIMEOUT_MIN = int(os.getenv("FAKE_STEP_TIMEOUT_MIN", "30"))
FAKE_COMPLETED_CLOSE_MIN = int(os.getenv("FAKE_COMPLETED_CLOSE_MIN", "5"))
FAKE_MAX_ACTIVE_SESSIONS = int(os.getenv("FAKE_MAX_ACTIVE_SESSIONS", "30"))
FAKE_CREATE_BURST_MAX = int(os.getenv("FAKE_CREATE_BURST_MAX", "2"))
TOPIC_AUTO_DELETE_DAYS = int(os.getenv("TOPIC_AUTO_DELETE_DAYS", "3"))
TOPIC_EXPIRY_CHECK_SEC = int(os.getenv("TOPIC_EXPIRY_CHECK_SEC", "300"))

# Night/Day schedule and voice settings
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")
NIGHT_START_HOUR = int(os.getenv("NIGHT_START_HOUR", "23"))
NIGHT_END_HOUR = int(os.getenv("NIGHT_END_HOUR", "7"))


required_vars = {"BOT_TOKEN": BOT_TOKEN, "CHAT_GROUP_ID": CHAT_GROUP_ID}
missing = [k for k, v in required_vars.items() if not v]
if missing:
    raise RuntimeError(f"Missing required config parameters: {', '.join(missing)}")
