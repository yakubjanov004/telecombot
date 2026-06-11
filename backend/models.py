import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum as SAEnum,
    BigInteger,
    Text,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Index,
    Date,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

# =========================
# ENUMS
# =========================

class StatusEnum(enum.Enum):
    NEW = "NEW"
    DONE = "DONE"


class ServiceType(str, enum.Enum):
    INTERNET = "internet"
    MOBILE = "mobile"


class UserRole(str, enum.Enum):
    CLIENT = "client"
    OPERATOR = "operator"
    MANAGER = "manager"
    ADMIN = "admin"


class OperatorType(str, enum.Enum):
    OUTSOURCE = "outsource"
    MOBILE = "mobile"


class SaleStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class SaleSource(str, enum.Enum):
    EXCEL_IMPORT = "excel_import"
    MANUAL = "manual"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class ClientMode(str, enum.Enum):
    REAL = "real"
    SIMULATED = "simulated"


class InitiatorType(str, enum.Enum):
    CLIENT = "client"
    BOT = "bot"
    SYSTEM = "system"


class ClosedReason(str, enum.Enum):
    RESOLVED = "resolved"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    SCRIPT_COMPLETED = "script_completed"
    ERROR = "error"


class WaitingFor(str, enum.Enum):
    CLIENT = "client"
    OPERATOR = "operator"
    BOT = "bot"
    NONE = "none"


class BotTaskType(str, enum.Enum):
    SEND_INTRO = "send_intro"
    SEND_SCENARIO_STEP = "send_scenario_step"
    CHECK_OPERATOR_REPLY = "check_operator_reply"
    CLOSE_TOPIC = "close_topic"
    CHECK_TIMEOUT = "check_timeout"
    OPERATOR_REPLY = "operator_reply"


class BotTaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class SessionEventType(str, enum.Enum):
    TOPIC_OPENED = "topic_opened"
    TOPIC_PINNED = "topic_pinned"
    CLIENT_MESSAGE_RECEIVED = "client_message_received"
    OPERATOR_ASSIGNED = "operator_assigned"
    OPERATOR_JOINED = "operator_joined"
    BOT_MESSAGE_SENT = "bot_message_sent"
    CLOSE_REQUESTED = "close_requested"
    TOPIC_CLOSED = "topic_closed"
    SCRIPT_COMPLETED = "script_completed"
    ERROR_OCCURRED = "error_occurred"


class TopicStatusEnum(enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DELETED = "deleted"


# =========================
# MIXINS
# =========================

class TimestampMixin:
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class UpdatedAtMixin(TimestampMixin):
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# =========================
# LOOKUP TABLES
# =========================

class Branch(TimestampMixin, Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    code = Column(String(100), unique=True, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    users = relationship("User", back_populates="branch")
    dealers = relationship("Dealer", back_populates="branch")


class Dealer(TimestampMixin, Base):
    __tablename__ = "dealers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), nullable=True)
    service_type = Column(SAEnum(ServiceType), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    branch = relationship("Branch", back_populates="dealers")
    sale_points = relationship("SalePoint", back_populates="dealer")

    __table_args__ = (
        UniqueConstraint("branch_id", "name", name="uq_dealer_branch_name"),
    )


class SalePoint(TimestampMixin, Base):
    __tablename__ = "sale_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    dealer = relationship("Dealer", back_populates="sale_points")

    __table_args__ = (
        UniqueConstraint("dealer_id", "name", name="uq_sale_point_dealer_name"),
    )


class ReportPeriod(TimestampMixin, Base):
    __tablename__ = "report_periods"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_closed = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_report_period_year_month"),
    )


class RatePlan(TimestampMixin, Base):
    __tablename__ = "rate_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    service_type = Column(SAEnum(ServiceType), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    price = Column(Integer, nullable=True)
    description = Column(String(500), nullable=True)
    speed = Column(String(100), nullable=True)
    minutes = Column(String(100), nullable=True)
    sms = Column(String(100), nullable=True)
    mb = Column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("name", "service_type", name="uq_rate_plan_name_service_type"),
    )


class ImportBatch(TimestampMixin, Base):
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_type = Column(SAEnum(ServiceType), nullable=False)
    period_id = Column(Integer, ForeignKey("report_periods.id", ondelete="SET NULL"), nullable=True)
    file_name = Column(String(255), nullable=True)
    sheet_name = Column(String(255), nullable=True)
    source = Column(SAEnum(SaleSource), default=SaleSource.EXCEL_IMPORT, nullable=False)
    rows_total = Column(Integer, default=0, nullable=False)
    rows_success = Column(Integer, default=0, nullable=False)
    rows_failed = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)


# =========================
# USERS
# =========================

class User(UpdatedAtMixin, Base):
    __tablename__ = "users"

    tg_id = Column(BigInteger, primary_key=True, index=True)
    full_name = Column(String(255), nullable=True)
    username = Column(String(100), unique=True, nullable=True)
    phone = Column(String(50), nullable=True)
    lang = Column(String(10), default="uz", nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.CLIENT, nullable=False)
    operator_type = Column(SAEnum(OperatorType), nullable=True)
    navi_username = Column(String(120), nullable=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    is_simulated = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    warnings_count = Column(Integer, default=0, nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)

    branch = relationship("Branch", back_populates="users")

    client_sessions = relationship(
        "ChatSession",
        back_populates="client",
        foreign_keys="ChatSession.client_tg_id",
    )
    operator_sessions = relationship(
        "ChatSession",
        back_populates="operator",
        foreign_keys="ChatSession.operator_tg_id",
    )


# =========================
# APPLICATIONS (LEADS)
# =========================

class InternetApplication(Base):
    __tablename__ = "internet_applications"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(255), nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    father_name = Column(String(255), nullable=False)
    status = Column(SAEnum(StatusEnum), default=StatusEnum.NEW)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    done_at = Column(DateTime, nullable=True)
    done_by = Column(BigInteger, nullable=True)
    phone = Column(String(50), nullable=True)
    selected_tariff_id = Column(Integer, nullable=True)
    selected_tariff_code = Column(String(100), nullable=True)
    address = Column(String(500), nullable=True)
    branches = Column(String(255), nullable=True)
    departments = Column(String(255), nullable=True)
    navi_user = Column(String(120), nullable=True)
    rt_lc_states = Column(String(50), nullable=True)
    msisdn = Column(String(100), nullable=True)
    rate_plan_first_connection = Column(String(255), nullable=True)


class MobileApplication(Base):
    __tablename__ = "mobile_applications"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), nullable=False)
    operator_code = Column(String(2), nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    father_name = Column(String(255), nullable=False)
    status = Column(SAEnum(StatusEnum), default=StatusEnum.NEW)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    done_at = Column(DateTime, nullable=True)
    done_by = Column(BigInteger, nullable=True)
    selected_tariff_id = Column(Integer, nullable=True)
    selected_tariff_code = Column(String(100), nullable=True)
    address = Column(String(500), nullable=True)
    dealer = Column(String(255), nullable=True)
    navi_user = Column(String(120), nullable=True)
    msisdn = Column(String(100), nullable=True)
    rate_plan_first_connection = Column(String(255), nullable=True)
    branches = Column(String(255), nullable=True)


# =========================
# CHAT / TOPIC CONTROL
# =========================

class ChatSession(UpdatedAtMixin, Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    
    # Optional fields for Web Clients vs Telegram Clients
    client_tg_id = Column(BigInteger, ForeignKey("users.tg_id", ondelete="CASCADE"), nullable=True, index=True)
    operator_tg_id = Column(BigInteger, ForeignKey("users.tg_id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Web Client application reference
    client_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    application_type = Column(SAEnum(ServiceType), nullable=True)
    application_id = Column(Integer, nullable=True)
    
    # Telegram Topic fields
    telegram_message_id = Column(BigInteger, nullable=True)
    telegram_topic_id = Column(BigInteger, unique=True, nullable=True, index=True)
    telegram_group_id = Column(BigInteger, nullable=True)
    
    # State tracking
    is_active = Column(Integer, default=1)  # 1 for active web chat
    status = Column(SAEnum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False, index=True)
    topic_status = Column(SAEnum(TopicStatusEnum), default=TopicStatusEnum.ACTIVE)
    topic_created_at = Column(DateTime(timezone=True), nullable=True)
    topic_expires_at = Column(DateTime(timezone=True), nullable=True)
    service_type = Column(SAEnum(ServiceType), nullable=False)
    initiator_type = Column(SAEnum(InitiatorType), default=InitiatorType.CLIENT, nullable=False)
    client_mode = Column(SAEnum(ClientMode), default=ClientMode.REAL, nullable=False)
    
    userbot_active = Column(Boolean, default=True, nullable=False)
    operator_joined = Column(Boolean, default=False, nullable=False)
    
    first_message_at = Column(DateTime(timezone=True), nullable=True)
    last_client_message_at = Column(DateTime(timezone=True), nullable=True)
    last_operator_message_at = Column(DateTime(timezone=True), nullable=True)
    last_bot_message_at = Column(DateTime(timezone=True), nullable=True)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    last_bot_message_id = Column(BigInteger, nullable=True)
    auto_reply_enabled = Column(Boolean, default=True, nullable=False)
    
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_reason = Column(SAEnum(ClosedReason), nullable=True)

    @property
    def claimed_by_operator_id(self):
        return self.operator_tg_id
        
    @claimed_by_operator_id.setter
    def claimed_by_operator_id(self, value):
        self.operator_tg_id = value

    client = relationship("User", back_populates="client_sessions", foreign_keys=[client_tg_id])
    operator = relationship("User", back_populates="operator_sessions", foreign_keys=[operator_tg_id])
    state = relationship("UserbotState", back_populates="session", uselist=False, cascade="all, delete-orphan")
    bot_tasks = relationship("BotTask", back_populates="session", cascade="all, delete-orphan")
    event_logs = relationship("SessionEventLog", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_chat_session_client_mode_status", "client_mode", "status"),
    )


class UserbotState(UpdatedAtMixin, Base):
    __tablename__ = "userbot_states"

    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), primary_key=True)
    current_step = Column(String(100), nullable=True)
    collected_data = Column(Text, default="{}", nullable=False)  # Serialized JSON payload
    waiting_for = Column(SAEnum(WaitingFor), default=WaitingFor.NONE, nullable=False)
    next_action_at = Column(DateTime(timezone=True), nullable=True)
    scenario_index = Column(Integer, default=0, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)

    session = relationship("ChatSession", back_populates="state")


class BotTask(TimestampMixin, Base):
    __tablename__ = "bot_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    task_type = Column(SAEnum(BotTaskType), nullable=False)
    status = Column(SAEnum(BotTaskStatus), default=BotTaskStatus.PENDING, nullable=False, index=True)
    payload = Column(Text, default="{}", nullable=False)  # Serialized JSON payload
    priority = Column(Integer, default=0, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error_log = Column(Text, nullable=True)

    session = relationship("ChatSession", back_populates="bot_tasks")


class SessionEventLog(TimestampMixin, Base):
    __tablename__ = "session_event_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(SAEnum(SessionEventType), nullable=False)
    actor_tg_id = Column(BigInteger, nullable=True)
    event_data = Column(Text, default="{}", nullable=False)  # Serialized JSON payload

    session = relationship("ChatSession", back_populates="event_logs")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    sender = Column(String(20), nullable=False)  # 'client', 'operator', 'bot'
    message = Column(Text, nullable=False)
    media_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProcessedUpdate(Base):
    __tablename__ = "processed_updates"

    id = Column(Integer, primary_key=True, index=True)
    update_id = Column(BigInteger, unique=True, nullable=False, index=True)
    processed_at = Column(DateTime, default=datetime.utcnow)


# =========================
# SALES
# =========================

class InternetSale(UpdatedAtMixin, Base):
    __tablename__ = "internet_sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True)
    period_id = Column(Integer, ForeignKey("report_periods.id", ondelete="SET NULL"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id", ondelete="SET NULL"), nullable=True)
    operator_tg_id = Column(BigInteger, ForeignKey("users.tg_id", ondelete="SET NULL"), nullable=True)
    rate_plan_id = Column(Integer, ForeignKey("rate_plans.id", ondelete="SET NULL"), nullable=True)

    branch_name_raw = Column(String(255), nullable=True)
    dealer_name_raw = Column(String(255), nullable=True)
    department_name_raw = Column(String(255), nullable=True)
    standard_type = Column(String(255), nullable=True)
    navi_user = Column(String(120), nullable=False, index=True)
    rt_lc_state = Column(String(50), nullable=True)
    msisdn = Column(String(100), nullable=False, index=True)
    rate_plan_raw = Column(String(255), nullable=True)
    sale_amount = Column(BigInteger, default=0, nullable=False)
    sale_quantity = Column(Integer, nullable=True)
    activation_date = Column(Date, nullable=True)
    row_number = Column(Integer, nullable=True)
    source = Column(SAEnum(SaleSource), default=SaleSource.EXCEL_IMPORT, nullable=False)
    status = Column(SAEnum(SaleStatus), default=SaleStatus.CONFIRMED, nullable=False, index=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)


class MobileSale(UpdatedAtMixin, Base):
    __tablename__ = "mobile_sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True)
    period_id = Column(Integer, ForeignKey("report_periods.id", ondelete="SET NULL"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    dealer_id = Column(Integer, ForeignKey("dealers.id", ondelete="SET NULL"), nullable=True)
    sale_point_id = Column(Integer, ForeignKey("sale_points.id", ondelete="SET NULL"), nullable=True)
    operator_tg_id = Column(BigInteger, ForeignKey("users.tg_id", ondelete="SET NULL"), nullable=True)
    rate_plan_id = Column(Integer, ForeignKey("rate_plans.id", ondelete="SET NULL"), nullable=True)

    branch_name_raw = Column(String(255), nullable=True)
    dealer_name_raw = Column(String(255), nullable=True)
    sale_point_name_raw = Column(String(255), nullable=True)
    navi_user = Column(String(120), nullable=False, index=True)
    rt_lc_state = Column(String(50), nullable=True)
    msisdn = Column(String(100), nullable=False, index=True)
    rate_plan_raw = Column(String(255), nullable=True)
    charged_amount = Column(BigInteger, default=0, nullable=False)
    sale_quantity = Column(Integer, nullable=True)
    activation_date = Column(Date, nullable=True)
    row_number = Column(Integer, nullable=True)
    source = Column(SAEnum(SaleSource), default=SaleSource.EXCEL_IMPORT, nullable=False)
    status = Column(SAEnum(SaleStatus), default=SaleStatus.CONFIRMED, nullable=False, index=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
