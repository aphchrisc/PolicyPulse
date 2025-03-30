# models/enums.py

import enum

class DataSourceEnum(enum.Enum):
    legiscan = "legiscan"
    CONGRESS_GOV = "congress_gov"
    OTHER = "other"

class GovtTypeEnum(enum.Enum):
    federal = "federal"
    state = "state"
    county = "county"
    city = "city"

class BillStatusEnum(enum.Enum):
    new = "new"
    introduced = "introduced"
    updated = "updated"
    passed = "passed"
    defeated = "defeated"
    vetoed = "vetoed"
    enacted = "enacted"
    pending = "pending"

class ImpactLevelEnum(enum.Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"

class ImpactCategoryEnum(enum.Enum):
    public_health = "public_health"
    local_gov = "local_gov"
    economic = "economic"
    environmental = "environmental"
    education = "education"
    infrastructure = "infrastructure"
    healthcare = "healthcare"
    social_services = "social_services"
    justice = "justice"

class AmendmentStatusEnum(enum.Enum):
    proposed = "proposed"
    adopted = "adopted"
    rejected = "rejected"
    withdrawn = "withdrawn"

class NotificationTypeEnum(enum.Enum):
    high_priority = "high_priority"
    new_bill = "new_bill"
    status_change = "status_change"
    analysis_complete = "analysis_complete"

class SyncStatusEnum(enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    partial = "partial"
