"""
API Routes Package

This package contains all the route modules for the PolicyPulse API.
Each module corresponds to a specific area of functionality.
"""

# Import all routers to make them available when importing from routes
from .health import router as health_router
from .users import router as users_router
from .legislation import router as legislation_router
from .analysis import router as analysis_router
from .dashboard import router as dashboard_router
from .admin import router as admin_router
from .sync import router as sync_router
from .texas import router as texas_router

# Ensure all routers have correct path prefixes
# This helps ensure consistent URL patterns for the frontend
health_router.prefix = "/health"
legislation_router.prefix = "/legislation"
analysis_router.prefix = "/analysis"
dashboard_router.prefix = "/dashboard"
users_router.prefix = "/users"
admin_router.prefix = "/admin"
sync_router.prefix = "/sync"
texas_router.prefix = "/texas"

# Export all routers for easy access
__all__ = [
    'health_router',
    'users_router',
    'legislation_router',
    'analysis_router',
    'dashboard_router',
    'admin_router',
    'sync_router',
    'texas_router',
]