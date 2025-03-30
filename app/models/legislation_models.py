# models/legislation_models.py

from datetime import datetime
from typing import Optional, Union

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float,
    UniqueConstraint, Index, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy_utils import TSVectorType  # Add the missing import

from .base import BaseModel, FlexibleContentType
from .enums import (
    DataSourceEnum,
    GovtTypeEnum,
    BillStatusEnum,
    ImpactLevelEnum,
    ImpactCategoryEnum,
    AmendmentStatusEnum
)

class Legislation(BaseModel):
    """
    Represents a legislative bill along with its metadata and relationships.
    """
    __tablename__ = 'legislation'

    id = Column(Integer, primary_key=True)
    external_id = Column(String(50), nullable=False)
    data_source = Column(
        SQLEnum(DataSourceEnum),
        nullable=False
    )
    govt_type = Column(SQLEnum(GovtTypeEnum), nullable=False)
    govt_source = Column(String(100), nullable=False)
    bill_number = Column(String(50), nullable=False)
    bill_type = Column(String(50), nullable=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    bill_status = Column(SQLEnum(BillStatusEnum),
                          default=BillStatusEnum.new)

    url = Column(Text, nullable=True)
    state_link = Column(Text, nullable=True)

    bill_introduced_date = Column(DateTime, nullable=True)
    bill_last_action_date = Column(DateTime, nullable=True)
    bill_status_date = Column(DateTime, nullable=True)
    last_api_check = Column(DateTime, default=datetime.now(), nullable=True)

    change_hash = Column(String(50), nullable=True)
    raw_api_response = Column(JSONB, nullable=True)

    search_vector = Column(TSVectorType('title', 'description'), nullable=True)

    # Relationships
    analyses = relationship("LegislationAnalysis", back_populates="legislation",
                             cascade="all, delete-orphan")
    texts = relationship("LegislationText", back_populates="legislation",
                          cascade="all, delete-orphan")
    sponsors = relationship("LegislationSponsor", back_populates="legislation",
                             cascade="all, delete-orphan")
    amendments = relationship("Amendment", back_populates="legislation",
                               cascade="all, delete-orphan")
    priority = relationship("LegislationPriority", back_populates="legislation",
                             uselist=False, cascade="all, delete-orphan")
    impact_ratings = relationship("ImpactRating", back_populates="legislation",
                                   cascade="all, delete-orphan")
    implementation_requirements = relationship("ImplementationRequirement",
                                                back_populates="legislation",
                                                cascade="all, delete-orphan")
    alert_history = relationship("AlertHistory", back_populates="legislation",
                                  cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('data_source', 'govt_source', 'bill_number',
                          name='unique_bill_identifier'),
        Index('idx_legislation_status', 'bill_status'),
        Index('idx_legislation_dates', 'bill_introduced_date', 'bill_last_action_date'),
        Index('idx_legislation_change', 'change_hash'),
        Index('idx_legislation_search', 'search_vector', postgresql_using='gin'),
    )

    @property
    def latest_analysis(self) -> Optional["LegislationAnalysis"]:
        if self.analyses:
            return sorted(self.analyses, key=lambda a: a.analysis_version)[-1]
        return None

    @property
    def latest_text(self) -> Optional["LegislationText"]:
        if self.texts:
            return sorted(self.texts, key=lambda t: t.version_num)[-1]
        return None

    @validates('title')
    def validate_title(self, key, value):
        if not value or not value.strip():
            raise ValueError("Legislation title cannot be empty")
        return value


class LegislationAnalysis(BaseModel):
    """
    Stores AI-generated analysis of legislation with versioning.
    """
    __tablename__ = 'legislation_analysis'

    id = Column(Integer, primary_key=True)
    legislation_id = Column(Integer, ForeignKey('legislation.id'), nullable=False)

    analysis_version = Column(Integer, default=1, nullable=False)
    version_tag = Column(String(50), nullable=True)
    previous_version_id = Column(Integer, ForeignKey('legislation_analysis.id'), nullable=True)
    changes_from_previous = Column(JSONB, nullable=True)

    analysis_date = Column(DateTime, default=datetime.utcnow(), nullable=False)

    impact_category = Column(SQLEnum(ImpactCategoryEnum), nullable=True)
    impact = Column(SQLEnum(ImpactLevelEnum), nullable=True)

    summary = Column(Text, nullable=True)
    key_points = Column(JSONB, nullable=True)
    insufficient_text = Column(Boolean, default=False)

    public_health_impacts = Column(JSONB, nullable=True)
    local_gov_impacts = Column(JSONB, nullable=True)
    economic_impacts = Column(JSONB, nullable=True)
    environmental_impacts = Column(JSONB, nullable=True)
    education_impacts = Column(JSONB, nullable=True)
    infrastructure_impacts = Column(JSONB, nullable=True)
    stakeholder_impacts = Column(JSONB, nullable=True)

    recommended_actions = Column(JSONB, nullable=True)
    immediate_actions = Column(JSONB, nullable=True)
    resource_needs = Column(JSONB, nullable=True)
    raw_analysis = Column(JSONB, nullable=True)

    model_version = Column(String(50), nullable=True)
    confidence_score = Column(Float, nullable=True)
    processing_time = Column(Integer, nullable=True)

    legislation = relationship("Legislation", back_populates="analyses")
    child_analyses = relationship("LegislationAnalysis",
                                   backref="parent_analysis",
                                   remote_side=[id])

    __table_args__ = (
        UniqueConstraint('legislation_id', 'analysis_version', name='unique_analysis_version'),
    )

    @validates('analysis_version')
    def validate_analysis_version(self, key, value):
        if not isinstance(value, int) or value <= 0:
            raise ValueError("Analysis version must be a positive integer")
        return value


class LegislationText(BaseModel):
    """
    Stores text content of a legislative bill with version tracking.
    """
    __tablename__ = 'legislation_text'

    id = Column(Integer, primary_key=True)
    legislation_id = Column(Integer, ForeignKey('legislation.id'), nullable=False)
    version_num = Column(Integer, default=1, nullable=False)
    text_type = Column(String(50), nullable=True)

    text_content = Column(FlexibleContentType, nullable=True)
    text_hash = Column(String(50), nullable=True)
    text_date = Column(DateTime, default=datetime.now(), nullable=True)

    text_metadata = Column(JSONB, nullable=True)
    is_binary = Column(Boolean, default=False)
    content_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)

    legislation = relationship("Legislation", back_populates="texts")

    __table_args__ = (
        UniqueConstraint('legislation_id', 'version_num', name='unique_text_version'),
    )

    @validates('version_num')
    def validate_version_num(self, key, value):
        if not isinstance(value, int) or value <= 0:
            raise ValueError("Version number must be a positive integer")
        return value

    def set_content(self, content: Union[str, bytes]) -> None:
        BaseModel.set_content_field(self, content,
                                     'text_content',
                                     'is_binary',
                                     'text_metadata')
        if content is None:
            self.content_type = None
        elif isinstance(content, str):
            self.content_type = "text/plain"
            self.file_size = len(content.encode('utf-8'))
        elif isinstance(content, bytes):
            self.content_type = BaseModel._detect_content_type(content)
            self.file_size = len(content)

    def get_content(self) -> Union[str, bytes]:
        # Get the actual value of text_content, not the Column object
        text_content = getattr(self, 'text_content', None)
        is_binary = getattr(self, 'is_binary', False)
        
        if text_content is None:
            return b"" if is_binary else ""
        
        # Handle binary content properly
        if is_binary:
            # If it's already bytes, return it directly
            if isinstance(text_content, bytes):
                return text_content 
            # If it's a string but should be binary, encode it
            elif isinstance(text_content, str):
                # Try to convert it back to binary
                try:
                    # This might be a string representation of binary data
                    # Try to encode it as bytes
                    return text_content.encode('latin1')
                except Exception:
                    # If encoding fails, return empty bytes
                    return b""
            else:
                # Unknown type, return empty bytes
                return b""
        else:
            # Handle text content
            if isinstance(text_content, str):
                return text_content
            elif isinstance(text_content, bytes):
                # If it's bytes but should be text, decode it
                try:
                    return text_content.decode('utf-8', errors='replace')
                except Exception:
                    return str(text_content) 
            return str(text_content)  # Unknown type, convert to string


class LegislationSponsor(BaseModel):
    """
    Represents a sponsor associated with a legislative bill.
    """
    __tablename__ = 'legislation_sponsors'

    id = Column(Integer, primary_key=True)
    legislation_id = Column(Integer, ForeignKey('legislation.id'), nullable=False)

    sponsor_external_id = Column(String(50), nullable=True)
    sponsor_name = Column(String(255), nullable=False)
    sponsor_title = Column(String(100), nullable=True)
    sponsor_state = Column(String(50), nullable=True)
    sponsor_party = Column(String(50), nullable=True)
    sponsor_type = Column(String(50), nullable=True)

    legislation = relationship("Legislation", back_populates="sponsors")

    @property
    def name(self):
        """
        Provides compatibility with code that expects a 'name' attribute instead of 'sponsor_name'.
        """
        return self.sponsor_name
        
    @property
    def party(self):
        """
        Provides compatibility with code that expects a 'party' attribute instead of 'sponsor_party'.
        """
        return self.sponsor_party
        
    @property
    def state(self):
        """
        Provides compatibility with code that expects a 'state' attribute instead of 'sponsor_state'.
        """
        return self.sponsor_state
        
    @property
    def type(self):
        """
        Provides compatibility with code that expects a 'type' attribute instead of 'sponsor_type'.
        """
        return self.sponsor_type

    @property
    def role(self):
        """
        Provides compatibility with code that expects a 'role' attribute.
        Falls back to sponsor_type or sponsor_title as appropriate.
        """
        # Get the actual attribute values, not the Column objects
        sponsor_type = getattr(self, 'sponsor_type', None)
        sponsor_title = getattr(self, 'sponsor_title', None)
        
        # Return the first non-None value, or "Unknown"
        if sponsor_type is not None:
            return sponsor_type
        elif sponsor_title is not None:
            return sponsor_title
        else:
            return "Unknown"

    @validates('sponsor_name')
    def validate_sponsor_name(self, key, value):
        if not value or not value.strip():
            raise ValueError("Sponsor name cannot be empty")
        return value


class Amendment(BaseModel):
    """
    Tracks amendments to legislation with a link back to the parent bill.
    """
    __tablename__ = 'amendments'

    id = Column(Integer, primary_key=True)
    amendment_id = Column(String(50), nullable=False)
    legislation_id = Column(Integer, ForeignKey('legislation.id'), nullable=False)

    adopted = Column(Boolean, default=False)
    status = Column(SQLEnum(AmendmentStatusEnum),
                     default=AmendmentStatusEnum.proposed)
    amendment_date = Column(DateTime, nullable=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    amendment_hash = Column(String(50), nullable=True)

    amendment_text = Column(FlexibleContentType, nullable=True)
    amendment_url = Column(String(255), nullable=True)
    state_link = Column(String(255), nullable=True)

    chamber = Column(String(50), nullable=True)
    sponsor_info = Column(JSONB, nullable=True)

    text_metadata = Column(JSONB, nullable=True)
    is_binary_text = Column(Boolean, default=False)

    legislation = relationship("Legislation", back_populates="amendments")

    __table_args__ = (
        Index('idx_amendments_legislation', 'legislation_id'),
        Index('idx_amendments_date', 'amendment_date'),
    )

    def set_amendment_text(self, content: Union[str, bytes]) -> None:
        BaseModel.set_content_field(
            self, content, 'amendment_text', 'is_binary_text', 'text_metadata'
        )


class LegislationPriority(BaseModel):
    """
    Tracks prioritization scores for legislation.
    """
    __tablename__ = 'legislation_priorities'

    id = Column(Integer, primary_key=True)
    legislation_id = Column(Integer, ForeignKey('legislation.id'), nullable=False)

    public_health_relevance = Column(Integer, default=0)
    local_govt_relevance = Column(Integer, default=0)
    overall_priority = Column(Integer, default=0)

    auto_categorized = Column(Boolean, default=False)
    auto_categories = Column(JSONB, nullable=True)

    manually_reviewed = Column(Boolean, default=False)
    manual_priority = Column(Integer, default=0)
    reviewer_notes = Column(Text, nullable=True)
    review_date = Column(DateTime, nullable=True)

    should_notify = Column(Boolean, default=False)
    notification_sent = Column(Boolean, default=False)
    notification_date = Column(DateTime, nullable=True)

    legislation = relationship("Legislation", back_populates="priority")

    __table_args__ = (
        Index('idx_priority_health', 'public_health_relevance'),
        Index('idx_priority_local_govt', 'local_govt_relevance'),
        Index('idx_priority_overall', 'overall_priority'),
    )

    @validates('public_health_relevance', 'local_govt_relevance',
                'overall_priority', 'manual_priority')
    def validate_score(self, key, value):
        if value is None:
            return 0
        if not isinstance(value, int) or not (0 <= value <= 100):
            raise ValueError(f"{key} must be an integer between 0 and 100")
        return value


class ImpactRating(BaseModel):
    """
    Stores specific impact ratings for legislation.
    """
    __tablename__ = 'impact_ratings'

    id = Column(Integer, primary_key=True)
    legislation_id = Column(Integer, ForeignKey('legislation.id'), nullable=False)
    impact_category = Column(SQLEnum(ImpactCategoryEnum), nullable=False)
    impact_level = Column(SQLEnum(ImpactLevelEnum), nullable=False)

    impact_description = Column(Text, nullable=True)
    affected_entities = Column(JSONB, nullable=True)
    confidence_score = Column(Float, nullable=True)

    is_ai_generated = Column(Boolean, default=True)
    reviewed_by = Column(String(100), nullable=True)
    review_date = Column(DateTime, nullable=True)

    legislation = relationship("Legislation", back_populates="impact_ratings")

    @validates('confidence_score')
    def validate_confidence_score(self, key, value):
        if value is None:
            return None
        if not isinstance(value, (int, float)) or not (0 <= value <= 1):
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return float(value)


class ImplementationRequirement(BaseModel):
    """
    Captures specific implementation requirements and timelines for legislation.
    """
    __tablename__ = 'implementation_requirements'

    id = Column(Integer, primary_key=True)
    legislation_id = Column(Integer, ForeignKey('legislation.id'), nullable=False)

    requirement_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    estimated_cost = Column(String(100), nullable=True)
    funding_provided = Column(Boolean, default=False)
    implementation_deadline = Column(DateTime, nullable=True)
    entity_responsible = Column(String(100), nullable=True)

    legislation = relationship("Legislation",
                                back_populates="implementation_requirements")

    @validates('requirement_type', 'description')
    def validate_required_fields(self, key, value):
        if not value or not str(value).strip():
            raise ValueError(f"{key} cannot be empty")
        return value
