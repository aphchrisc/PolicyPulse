import enum
import os
import time
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text,
    ForeignKey, Boolean, UniqueConstraint, Index, Float, Enum
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy_utils import TSVectorType

Base = declarative_base()

# ---------------------------------------------------------------------------
# 1) Abstract Base with Audit Fields
# ---------------------------------------------------------------------------
class BaseModel(Base):
    """
    Abstract base model that provides audit fields for all inheriting models.
    """
    __abstract__ = True

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(50))
    updated_by = Column(String(50))


# ---------------------------------------------------------------------------
# 2) Enums (DataSource, GovtType, BillStatus, Impact, etc.)
# ---------------------------------------------------------------------------
class DataSourceEnum(enum.Enum):
    """
    Enum for the source of legislative data.
    """
    LEGISCAN = "legiscan"
    CONGRESS_GOV = "congress_gov"
    OTHER = "other"


class GovtTypeEnum(enum.Enum):
    """
    Enum for government types.
    """
    FEDERAL = "federal"
    STATE = "state"
    COUNTY = "county"
    CITY = "city"


class BillStatusEnum(enum.Enum):
    """
    Enum for legislative bill statuses.
    """
    NEW = "new"
    INTRODUCED = "introduced"
    UPDATED = "updated"
    PASSED = "passed"
    DEFEATED = "defeated"
    VETOED = "vetoed"
    ENACTED = "enacted"
    PENDING = "pending"


class ImpactLevelEnum(enum.Enum):
    """
    Enum for overall impact levels.
    """
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ImpactCategoryEnum(enum.Enum):
    """
    Enum for categorizing impacts.
    """
    PUBLIC_HEALTH = "public_health"
    LOCAL_GOV = "local_gov"
    ECONOMIC = "economic"
    # Additional categories can be added as needed.


class SyncStatusEnum(enum.Enum):
    """
    Enum for sync process statuses.
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# ---------------------------------------------------------------------------
# 3) User Models
# ---------------------------------------------------------------------------
class User(BaseModel):
    """
    Represents an application user.
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)

    # relationships
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    searches = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    alert_preferences = relationship("AlertPreference", back_populates="user", cascade="all, delete-orphan")


class UserPreference(BaseModel):
    """
    Stores user preferences such as keywords for filtering or search.
    """
    __tablename__ = 'user_preferences'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    keywords = Column(JSONB)

    user = relationship("User", back_populates="preferences")


class SearchHistory(BaseModel):
    """
    Records search queries and corresponding results for a user.
    """
    __tablename__ = 'search_history'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    query = Column(String)
    results = Column(JSONB)

    user = relationship("User", back_populates="searches")


class AlertPreference(BaseModel):
    """
    Stores alert preferences for a user including notification channels,
    custom keywords, ignore lists, and matching rules.
    """
    __tablename__ = 'alert_preferences'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    email = Column(String(255), nullable=False)
    active = Column(Boolean, default=True)
    alert_channels = Column(JSONB)      # e.g. {'email': true, 'sms': false, ...}
    custom_keywords = Column(JSONB)     # Personal extra keywords for matching
    ignore_list = Column(JSONB)         # Bills to ignore
    alert_rules = Column(JSONB)         # Complex matching rules

    user = relationship("User", back_populates="alert_preferences")


class AlertHistory(BaseModel):
    """
    Logs the history of alerts sent to users for legislative updates.
    """
    __tablename__ = 'alert_history'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    legislation_id = Column(Integer, nullable=False)
    alert_type = Column(String(50))
    alert_content = Column(Text)
    delivery_status = Column(String(50))
    error_message = Column(Text)

    user = relationship("User")


# ---------------------------------------------------------------------------
# 4) Legislation Models
# ---------------------------------------------------------------------------
class Legislation(BaseModel):
    """
    Represents a legislative bill with associated metadata and relationships.
    """
    __tablename__ = 'legislation'
    id = Column(Integer, primary_key=True)
    external_id = Column(String(50), nullable=False)  # LegiScan bill_id
    data_source = Column(Enum(DataSourceEnum), nullable=False)
    govt_type = Column(Enum(GovtTypeEnum), nullable=False)
    govt_source = Column(String(100), nullable=False)  # e.g., "US Congress 119th" or "Texas Legislature 2023"
    bill_number = Column(String(50), nullable=False)
    bill_type = Column(String(50))
    title = Column(Text, nullable=False)
    description = Column(Text)
    bill_status = Column(Enum(BillStatusEnum), default=BillStatusEnum.NEW)
    url = Column(Text)
    state_link = Column(Text)
    bill_introduced_date = Column(DateTime)
    bill_last_action_date = Column(DateTime)
    bill_status_date = Column(DateTime)
    last_api_check = Column(DateTime, default=datetime.utcnow)
    change_hash = Column(String(50))
    raw_api_response = Column(JSONB)
    search_vector = Column(TSVectorType('title', 'description'))

    # relationships
    analyses = relationship("LegislationAnalysis", back_populates="legislation", cascade="all, delete-orphan")
    texts = relationship("LegislationText", back_populates="legislation", cascade="all, delete-orphan")
    sponsors = relationship("LegislationSponsor", back_populates="legislation", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('data_source', 'govt_source', 'bill_number', name='unique_bill_identifier'),
        Index('idx_legislation_status', 'bill_status'),
        Index('idx_legislation_dates', 'bill_introduced_date', 'bill_last_action_date'),
        Index('idx_legislation_change', 'change_hash'),
        Index('idx_legislation_search', 'search_vector', postgresql_using='gin'),
    )

    @property
    def latest_analysis(self):
        """
        Retrieves the most recent analysis object based on the analysis version.
        """
        if self.analyses:
            return sorted(self.analyses, key=lambda x: x.analysis_version)[-1]
        return None

    @property
    def latest_text(self):
        """
        Retrieves the most recent text version based on version number.
        """
        if self.texts:
            return sorted(self.texts, key=lambda x: x.version_num)[-1]
        return None


class LegislationAnalysis(BaseModel):
    """
    Stores AI-generated analysis for a legislative bill, including summaries,
    key points, impacts, and recommended actions. Supports versioning for updates.
    """
    __tablename__ = 'legislation_analysis'
    id = Column(Integer, primary_key=True)
    legislation_id = Column(Integer, ForeignKey('legislation.id'), nullable=False)
    analysis_version = Column(Integer, default=1, nullable=False)
    version_tag = Column(String(50))  # e.g., 'initial', 'revised', etc.
    previous_version_id = Column(Integer, ForeignKey('legislation_analysis.id'))
    changes_from_previous = Column(JSONB)
    analysis_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    summary = Column(Text)
    key_points = Column(JSONB)
    public_health_impacts = Column(JSONB)
    local_gov_impacts = Column(JSONB)
    economic_impacts = Column(JSONB)
    stakeholder_impacts = Column(JSONB)
    recommended_actions = Column(JSONB)
    immediate_actions = Column(JSONB)
    resource_needs = Column(JSONB)
    raw_analysis = Column(JSONB)  # Stores the full raw analysis JSON
    model_version = Column(String(50))
    confidence_score = Column(Float)
    processing_time = Column(Integer)  # e.g. milliseconds

    # Simplified impact fields for user-friendly metadata
    impact_category = Column(Enum(ImpactCategoryEnum), nullable=True,
                             doc="Simplified impact category, e.g., public_health, local_gov, economic.")
    impact = Column(Enum(ImpactLevelEnum), nullable=True,
                    doc="Simplified overall impact level, e.g., low, moderate, high, critical.")

    legislation = relationship("Legislation", back_populates="analyses")

    __table_args__ = (
        UniqueConstraint('legislation_id', 'analysis_version', name='unique_analysis_version'),
    )


class LegislationText(BaseModel):
    """
    Stores the text content of a legislative bill, supporting multiple versions.
    """
    __tablename__ = 'legislation_text'
    id = Column(Integer, primary_key=True)
    legislation_id = Column(Integer, ForeignKey('legislation.id'), nullable=False)
    version_num = Column(Integer, default=1)
    text_type = Column(String(50))
    text_content = Column(Text)
    text_hash = Column(String(50))
    text_date = Column(DateTime, default=datetime.utcnow)

    legislation = relationship("Legislation", back_populates="texts")

    __table_args__ = (
        UniqueConstraint('legislation_id', 'version_num', name='unique_text_version'),
    )


class LegislationSponsor(BaseModel):
    """
    Represents a sponsor associated with a legislative bill.
    """
    __tablename__ = 'legislation_sponsors'
    id = Column(Integer, primary_key=True)
    legislation_id = Column(Integer, ForeignKey('legislation.id'), nullable=False)
    sponsor_external_id = Column(String(50))
    sponsor_name = Column(String(255), nullable=False)
    sponsor_title = Column(String(100))
    sponsor_state = Column(String(50))
    sponsor_party = Column(String(50))
    sponsor_type = Column(String(50))

    legislation = relationship("Legislation", back_populates="sponsors")


# ---------------------------------------------------------------------------
# 5) Sync Metadata & Error Tracking
# ---------------------------------------------------------------------------
class SyncMetadata(BaseModel):
    """
    Tracks synchronization metadata for legislative data imports.
    """
    __tablename__ = 'sync_metadata'
    id = Column(Integer, primary_key=True)
    last_sync = Column(DateTime, nullable=False)
    last_successful_sync = Column(DateTime)
    bills_updated = Column(Integer, default=0)
    new_bills = Column(Integer, default=0)
    status = Column(Enum(SyncStatusEnum), nullable=False)
    sync_type = Column(String(50))  # e.g. 'daily', 'manual', etc.
    errors = Column(JSONB)


class SyncError(BaseModel):
    """
    Logs errors that occur during data synchronization processes.
    """
    __tablename__ = 'sync_errors'
    id = Column(Integer, primary_key=True)
    sync_id = Column(Integer, ForeignKey('sync_metadata.id'))
    error_time = Column(DateTime, default=datetime.utcnow)
    error_type = Column(String(50))
    error_message = Column(Text)
    stack_trace = Column(Text)
    resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)


# ---------------------------------------------------------------------------
# 6) DB Init
# ---------------------------------------------------------------------------
def init_db(max_retries=3, initial_delay=1) -> sessionmaker:
    """
    Initialize the database engine/connection with retry logic.
    
    Returns:
        A SQLAlchemy Session factory.
    
    Raises:
        ValueError: If the DATABASE_URL environment variable is not set.
        Exception: The last exception encountered after exhausting retries.
    """
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")

    retry_count = 0
    last_exception = None
    delay = initial_delay

    while retry_count < max_retries:
        try:
            engine = create_engine(database_url)
            connection = engine.connect()
            connection.close()
            # Create tables if they do not exist
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine)
            return Session
        except Exception as e:
            last_exception = e
            time.sleep(delay)
            delay *= 2
            retry_count += 1

    raise last_exception
