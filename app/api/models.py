"""
API Models

This module contains all the Pydantic models used for request and response validation
in the PolicyPulse API.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, root_validator
from enum import Enum

from app.models.enums import (
    BillStatusEnum,
    ImpactLevelEnum,
    ImpactCategoryEnum,
    GovtTypeEnum
)

# -----------------------------------------------------------------------------
# User API models
# -----------------------------------------------------------------------------
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    
    class Config:
        orm_mode = True

class UserPreferencesUpdate(BaseModel):
    notification_enabled: Optional[bool] = None
    theme: Optional[str] = None
    default_state: Optional[str] = None
    
class UserPreferencesResponse(BaseModel):
    id: int
    user_id: int
    notification_enabled: bool
    theme: str
    default_state: str
    
    class Config:
        orm_mode = True

# -----------------------------------------------------------------------------
# Bill API models
# -----------------------------------------------------------------------------
class BillResponse(BaseModel):
    id: int
    bill_id: int
    state: str
    bill_number: str
    title: str
    description: Optional[str]
    status: str
    bill_type: str
    progress: Optional[str]
    url: Optional[str]
    last_updated: datetime
    
    class Config:
        orm_mode = True

class BillDetailResponse(BaseModel):
    """API response model for bill detail"""
    id: int
    external_id: str
    govt_type: Optional[str] = None
    govt_source: Optional[str] = None
    bill_number: str
    title: str
    description: Optional[str] = None
    bill_status: Optional[str] = None
    bill_introduced_date: Optional[datetime] = None
    bill_last_action_date: Optional[datetime] = None
    bill_status_date: Optional[datetime] = None
    last_api_check: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    url: Optional[str] = None
    state_link: Optional[str] = None
    sponsors: Optional[List[Dict[str, Any]]] = []
    latest_text: Optional[Dict[str, Any]] = {}
    analysis: Optional[Dict[str, Any]] = {}
    priority: Optional[Dict[str, Any]] = {}
    impact_ratings: Optional[List[Dict[str, Any]]] = []
    implementation_requirements: Optional[List[Dict[str, Any]]] = []
    jurisdiction: Optional[str] = None
    
    class Config:
        """Pydantic model configuration"""
        # Allow any extra fields that might be in the data
        extra = "allow"
        # Skip validation for fields not explicitly specified in the model
        validate_assignment = False
        # Use from_attributes instead of orm_mode in Pydantic v2
        from_attributes = True
        
        schema_extra = {
            "example": {
                "id": 123,
                "external_id": "US_117_hr1234",
                "govt_type": "federal",
                "govt_source": "US Congress",
                "bill_number": "HR 1234",
                "title": "Example Bill Title",
                "description": "This is an example bill description.",
                "bill_status": "Introduced",
                "bill_introduced_date": "2023-01-15T00:00:00",
                "bill_last_action_date": "2023-02-01T00:00:00",
                "bill_status_date": "2023-02-01T00:00:00",
                "last_api_check": "2023-03-01T12:30:45",
                "created_at": "2023-01-16T09:12:34",
                "updated_at": "2023-03-01T12:30:45",
                "last_updated": "2023-03-01T12:30:45",
                "url": "https://example.com/bills/123",
                "state_link": "https://congress.gov/bill/117th-congress/house-bill/1234",
                "jurisdiction": "US Congress"
            }
        }
    
    # Add model validator to handle data before Pydantic validation
    @root_validator(pre=True)
    def normalize_data(cls, values):
        """
        Normalize data before validation to handle various field inconsistencies
        """
        # Create a copy to avoid modifying the input
        data = dict(values)
        
        # Handle datetime fields
        date_fields = [
            "bill_introduced_date", "bill_last_action_date", "bill_status_date",
            "last_api_check", "created_at", "updated_at", "last_updated"
        ]
        
        for field in date_fields:
            if field in data and data[field] is not None:
                # Ensure the field is in ISO format string if it's not already
                if isinstance(data[field], datetime):
                    data[field] = data[field].isoformat()
                # If it's a string but not in ISO format, try to parse it
                elif isinstance(data[field], str) and not data[field].endswith('Z') and 'T' not in data[field]:
                    try:
                        # Try to parse the date string and convert to ISO format
                        dt = datetime.strptime(data[field], '%Y-%m-%d')
                        data[field] = dt.isoformat()
                    except ValueError:
                        # If parsing fails, keep the original value
                        pass
        
        # Handle last_updated field
        if "last_updated" not in data:
            if "updated_at" in data and data["updated_at"]:
                data["last_updated"] = data["updated_at"]
            elif "created_at" in data and data["created_at"]:
                data["last_updated"] = data["created_at"]
        
        # Handle jurisdiction field
        if "jurisdiction" not in data:
            if "govt_source" in data and data["govt_source"]:
                data["jurisdiction"] = data["govt_source"]
            elif "state" in data and data["state"]:
                data["jurisdiction"] = data["state"]
        
        # Handle bill_status field
        if "bill_status" not in data and "status" in data:
            data["bill_status"] = data["status"]
        
        # Handle latest_text field if it exists
        if "latest_text" in data and data["latest_text"]:
            if isinstance(data["latest_text"], dict):
                # Ensure text field exists
                if "text" not in data["latest_text"] and "text_content" in data["latest_text"]:
                    data["latest_text"]["text"] = data["latest_text"]["text_content"]
        
        return data

class BillSearchParams(BaseModel):
    state: Optional[str] = None
    query: Optional[str] = None
    status: Optional[str] = None
    bill_type: Optional[str] = None
    progress: Optional[str] = None
    subjects: Optional[List[str]] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = 50
    offset: int = 0

# -----------------------------------------------------------------------------
# Analysis API models
# -----------------------------------------------------------------------------
class AnalysisRequestAPI(BaseModel):
    bill_id: Optional[int] = None
    text_content: Optional[str] = None
    analysis_type: str = "STANDARD"
    
    @field_validator('bill_id', 'text_content')
    def validate_input(cls, v, values, **kwargs):
        if 'bill_id' not in values and 'text_content' not in values:
            raise ValueError("Either bill_id or text_content must be provided")
        return v

class BookmarkCreate(BaseModel):
    bill_id: int
    notes: Optional[str] = None

class BookmarkResponse(BaseModel):
    id: int
    user_id: int
    bill_id: int
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        orm_mode = True

class BookmarkUpdate(BaseModel):
    notes: Optional[str] = None

# -----------------------------------------------------------------------------
# User Preferences models
# -----------------------------------------------------------------------------
class UserPrefsPayload(BaseModel):
    """Request model for user preferences."""
    keywords: List[str] = Field(default_factory=list, description="User-defined keywords for tracking legislation")
    health_focus: List[str] = Field(default_factory=list, description="Health department focus areas")
    local_govt_focus: List[str] = Field(default_factory=list, description="Local government focus areas")
    regions: List[str] = Field(default_factory=list, description="Texas regions of interest")

    @field_validator('keywords', 'health_focus', 'local_govt_focus', 'regions')
    def validate_string_lists(cls, v):
        """Validate that list items are non-empty strings."""
        if not all(isinstance(item, str) and item.strip() for item in v):
            raise ValueError("All list items must be non-empty strings")
        return [item.strip() for item in v]

    class Config:
        json_schema_extra = {
            "example": {
                "keywords": ["healthcare", "funding", "education"],
                "health_focus": ["mental health", "preventative care"],
                "local_govt_focus": ["zoning", "public safety"],
                "regions": ["Central Texas", "Gulf Coast"]
            }
        }

# -----------------------------------------------------------------------------
# Search models
# -----------------------------------------------------------------------------
class UserSearchPayload(BaseModel):
    """Request/response model for search history."""
    query: str = Field(..., min_length=1, description="Search query string")
    results: Dict[str, Any] = Field(default_factory=dict, description="Search result metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "healthcare funding",
                "results": {"total_hits": 42, "search_time_ms": 156}
            }
        }

# -----------------------------------------------------------------------------
# AI Analysis models
# -----------------------------------------------------------------------------
class AIAnalysisPayload(BaseModel):
    """Request model for AI analysis options."""
    model_name: Optional[str] = Field(None, description="Name of the AI model to use for analysis")
    focus_areas: Optional[List[str]] = Field(None, description="Specific areas to focus the analysis on")
    force_refresh: bool = Field(False, description="Whether to force a refresh of existing analysis")

    @field_validator('model_name')
    def validate_model_name(cls, v):
        """Validate that the model name is a recognized model."""
        if v is not None:
            valid_models = ["gpt-4o", "gpt-4o-2024-08-06", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
            if v not in valid_models and not v.startswith(tuple(valid_models)):
                raise ValueError(f"Model name '{v}' is not a recognized model. Valid options include: {', '.join(valid_models)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "model_name": "gpt-4o",
                "focus_areas": ["public health", "local government"],
                "force_refresh": False
            }
        }

class AnalysisOptions(BaseModel):
    """Options for controlling analysis behavior."""
    deep_analysis: bool = Field(False, description="Whether to perform a more thorough analysis")
    texas_focus: bool = Field(True, description="Whether to focus analysis on Texas impacts")
    focus_areas: Optional[List[str]] = Field(None, description="Specific areas to focus the analysis on")
    model_name: Optional[str] = Field(None, description="Name of the AI model to use for analysis")

    @field_validator('focus_areas')
    def validate_focus_areas(cls, v):
        """Validate that focus areas are valid."""
        if v is not None:
            valid_areas = ["public health", "local government", "economic", "environmental", "healthcare", 
                           "social services", "education", "infrastructure", "justice"]
            for area in v:
                if area.lower() not in valid_areas:
                    raise ValueError(f"'{area}' is not a recognized focus area")
        return v

    @field_validator('model_name')
    def validate_model_name(cls, v):
        """Validate that the model name is a recognized model."""
        if v is not None:
            valid_models = ["gpt-4o", "gpt-4o-2024-08-06", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
            if v not in valid_models and not v.startswith(tuple(valid_models)):
                raise ValueError(f"Model name '{v}' is not a recognized model. Valid options include: {', '.join(valid_models)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "deep_analysis": True,
                "texas_focus": True,
                "focus_areas": ["public health", "municipal governments"],
                "model_name": "gpt-4o"
            }
        }

# -----------------------------------------------------------------------------
# Date and filtering models
# -----------------------------------------------------------------------------
class DateRange(BaseModel):
    """Model representing a date range for filtering."""
    start_date: str = Field(..., pattern="^\\d{4}-\\d{2}-\\d{2}$", description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., pattern="^\\d{4}-\\d{2}-\\d{2}$", description="End date in YYYY-MM-DD format")

    @field_validator('end_date')
    def end_date_must_be_after_start_date(cls, v, values):
        """Validate that end date is after start date."""
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v

    @field_validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        """Validate that dates are in a valid format."""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError as e:
            raise ValueError(f"Invalid date format: {v}. Expected YYYY-MM-DD") from e

class BillSearchFilters(BaseModel):
    """Model for search filters."""
    bill_status: Optional[List[str]] = Field(None, description="Filter by bill status values")
    impact_category: Optional[List[str]] = Field(None, description="Filter by impact category")
    impact_level: Optional[List[str]] = Field(None, description="Filter by impact level")
    govt_type: Optional[List[str]] = Field(None, description="Filter by government type")
    date_range: Optional[DateRange] = Field(None, description="Filter by date range")
    reviewed_only: Optional[bool] = Field(None, description="Filter to only include reviewed legislation")

    @field_validator('bill_status')
    def validate_bill_status(cls, v):
        """Validate bill status values."""
        if v is not None:
            valid_statuses = [status.value for status in BillStatusEnum]
            for status in v:
                if status not in valid_statuses:
                    raise ValueError(f"Invalid bill_status: {status}. Valid values: {', '.join(valid_statuses)}")
        return v

    @field_validator('impact_category')
    def validate_impact_category(cls, v):
        """Validate impact category values."""
        if v is not None:
            valid_categories = [cat.value for cat in ImpactCategoryEnum]
            for category in v:
                if category not in valid_categories:
                    raise ValueError(f"Invalid impact_category: {category}. Valid values: {', '.join(valid_categories)}")
        return v

    @field_validator('impact_level')
    def validate_impact_level(cls, v):
        """Validate impact level values."""
        if v is not None:
            valid_levels = [level.value for level in ImpactLevelEnum]
            for level in v:
                if level not in valid_levels:
                    raise ValueError(f"Invalid impact_level: {level}. Valid values: {', '.join(valid_levels)}")
        return v

    @field_validator('govt_type')
    def validate_govt_type(cls, v):
        """Validate government type values."""
        if v is not None:
            valid_types = [gtype.value for gtype in GovtTypeEnum]
            for gtype in v:
                if gtype not in valid_types:
                    raise ValueError(f"Invalid govt_type: {gtype}. Valid values: {', '.join(valid_types)}")
        return v

class BillSearchQuery(BaseModel):
    """Advanced search parameters."""
    query: str = Field("", description="Search query string")
    filters: BillSearchFilters = Field(
        default_factory=lambda: BillSearchFilters(
            bill_status=None,
            impact_category=None,
            impact_level=None,
            govt_type=None,
            date_range=None,
            reviewed_only=None
        ),
        description="Search filters"
    )
    sort_by: str = Field("relevance", description="Field to sort results by")
    sort_dir: str = Field("desc", description="Sort direction (asc or desc)")
    limit: int = Field(50, description="Maximum number of results to return", ge=1, le=100)
    offset: int = Field(0, description="Number of results to skip", ge=0)

    @field_validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort field is supported."""
        valid_sort_fields = ["relevance", "date", "updated", "status", "title", "priority"]
        if v not in valid_sort_fields:
            raise ValueError(f"sort_by must be one of: {', '.join(valid_sort_fields)}")
        return v

    @field_validator('sort_dir')
    def validate_sort_dir(cls, v):
        """Ensure sort direction is valid."""
        if v not in ['asc', 'desc']:
            raise ValueError('sort_dir must be either "asc" or "desc"')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "healthcare funding",
                "filters": {
                    "bill_status": ["introduced", "passed"],
                    "impact_category": ["public_health"],
                    "impact_level": ["high", "critical"],
                    "govt_type": ["federal", "state"],
                    "date_range": {
                        "start_date": "2023-01-01",
                        "end_date": "2023-12-31"
                    },
                    "reviewed_only": True
                },
                "sort_by": "priority",
                "sort_dir": "desc",
                "limit": 20,
                "offset": 0
            }
        }

# -----------------------------------------------------------------------------
# Priority models
# -----------------------------------------------------------------------------
class SetPriorityPayload(BaseModel):
    """Manual priority setting payload."""
    public_health_relevance: Optional[int] = Field(
        None, description="Public health relevance score (0-100)", ge=0, le=100
    )
    local_govt_relevance: Optional[int] = Field(
        None, description="Local government relevance score (0-100)", ge=0, le=100
    )
    overall_priority: Optional[int] = Field(
        None, description="Overall priority score (0-100)", ge=0, le=100
    )
    notes: Optional[str] = Field(None, description="Reviewer notes")

    @model_validator(mode='after')
    def check_at_least_one_field(self):
        """Ensure at least one field is provided."""
        if all(
            getattr(self, field) is None
            for field in [
                'public_health_relevance',
                'local_govt_relevance',
                'overall_priority',
                'notes',
            ]
        ):
            raise ValueError('At least one field must be provided')
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "public_health_relevance": 85,
                "local_govt_relevance": 70,
                "overall_priority": 80,
                "notes": "Significant impact on local health departments' funding"
            }
        }

# -----------------------------------------------------------------------------
# Response models
# -----------------------------------------------------------------------------
class HealthResponse(BaseModel):
    """Response model for the health check endpoint."""
    status: str = Field(..., description="API status")
    message: str = Field(..., description="Status message")
    version: str = Field(..., description="API version")
    database: Dict[str, Any] = Field(..., description="Database status information including connection status and details")

class UserPreferencesAPIResponse(BaseModel):
    """Response model for user preferences API."""
    email: str = Field(..., description="User email")
    preferences: Dict[str, Any] = Field(..., description="User preferences")

class SearchHistoryResponse(BaseModel):
    """Response model for search history."""
    email: str = Field(..., description="User email")
    history: List[Dict[str, Any]] = Field(..., description="Search history items")

class LegislationListResponse(BaseModel):
    """Response model for legislation listing endpoints."""
    count: int = Field(..., description="Number of items returned")
    items: List[Dict[str, Any]] = Field(..., description="Legislation items")
    page_info: Dict[str, Any] = Field(default_factory=dict, description="Pagination metadata")
    facets: Optional[Dict[str, Any]] = Field(None, description="Search facets for filtering")

class AnalysisStatusResponse(BaseModel):
    """Response model for analysis status."""
    status: str = Field(..., description="Analysis status (processing or completed)")
    message: Optional[str] = Field(None, description="Status message")
    legislation_id: int = Field(..., description="Legislation ID")
    analysis_id: Optional[int] = Field(None, description="Analysis ID if completed")
    analysis_version: Optional[str] = Field(None, description="Analysis version if completed")
    analysis_date: Optional[str] = Field(None, description="Analysis date if completed")
    insufficient_text: Optional[bool] = Field(None, description="Flag indicating if the bill text was insufficient for detailed analysis")

class AnalysisHistoryResponse(BaseModel):
    """Response model for analysis history."""
    legislation_id: int = Field(..., description="Legislation ID")
    analysis_count: int = Field(..., description="Number of analyses")
    analyses: List[Dict[str, Any]] = Field(..., description="Analysis history items")

class PriorityUpdateResponse(BaseModel):
    """Response model for priority updates."""
    status: str = Field(..., description="Update status")
    message: str = Field(..., description="Status message")
    priority: Dict[str, Any] = Field(..., description="Updated priority values")

class SyncStatusResponse(BaseModel):
    """Response model for sync status."""
    sync_history: List[Dict[str, Any]] = Field(..., description="Sync history records")
    count: int = Field(..., description="Number of sync records")

class ErrorResponse(BaseModel):
    """Standardized error response model."""
    status: str = Field("error", description="Error status")
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Any] = Field(None, description="Additional error details")
    timestamp: str = Field(..., description="Error timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "code": "VALIDATION_ERROR",
                "message": "Input validation error",
                "details": [{"field": "email", "error": "Invalid email format"}],
                "timestamp": "2023-06-01T12:34:56Z"
            }
        }

# Export all models
__all__ = [
    # User models
    'UserCreate', 'UserResponse', 'UserPreferencesUpdate', 'UserPreferencesResponse',
    # Bill models
    'BillResponse', 'BillDetailResponse', 'BillSearchParams',
    # Analysis models
    'AnalysisRequestAPI', 'BookmarkCreate', 'BookmarkResponse', 'BookmarkUpdate',
    # User preferences models
    'UserPrefsPayload',
    # Search models
    'UserSearchPayload',
    # AI Analysis models
    'AIAnalysisPayload', 'AnalysisOptions',
    # Date and filtering models
    'DateRange', 'BillSearchFilters', 'BillSearchQuery',
    # Priority models
    'SetPriorityPayload',
    # Response models
    'HealthResponse', 'UserPreferencesAPIResponse', 'SearchHistoryResponse',
    'LegislationListResponse', 'AnalysisStatusResponse', 'AnalysisHistoryResponse',
    'PriorityUpdateResponse', 'SyncStatusResponse', 'ErrorResponse'
]
