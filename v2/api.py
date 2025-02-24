"""
api.py

A production-ready FastAPI application that exposes REST endpoints for:
 - Users & Preferences
 - Legislation listing, search, detail
 - Triggering AI-based analysis on a Legislation record
 - Basic CORS setup for React

Requirements:
   pip install fastapi uvicorn sqlalchemy openai psycopg2

Run:
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 1) Import your custom modules
from data_store import DataStore
from ai_analysis import AIAnalysis

# 2) Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 3) Prepare the FastAPI application
app = FastAPI(title="LegislationAPI", version="1.0.0")

# 4) Allow requests from a React dev server or your domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],  # update if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5) Provide a single DataStore instance for the whole app
#    We'll create it at startup and close it on shutdown if desired.
data_store: DataStore = None


@app.on_event("startup")
def startup_event():
    global data_store
    data_store = DataStore(max_retries=3)
    logger.info("DataStore initialized on startup.")


@app.on_event("shutdown")
def shutdown_event():
    if data_store:
        data_store.close()
        logger.info("DataStore closed on shutdown.")


# -----------------------------------------------------------------------------
# Models for request/response bodies (Pydantic)
# -----------------------------------------------------------------------------
class UserPrefsPayload(BaseModel):
    keywords: List[str] = []


class UserSearchPayload(BaseModel):
    query: str
    results: Dict[str, Any] = {}


class AIAnalysisPayload(BaseModel):
    """
    Optional request model if you want to specify a different model name 
    or something for the AI analysis. Otherwise the default from your 
    AIAnalysis config is used.
    """
    model_name: Optional[str] = None


# -----------------------------------------------------------------------------
# Dependencies
# -----------------------------------------------------------------------------
def get_data_store() -> DataStore:
    """
    A simple FastAPI dependency that yields the global data_store.
    """
    if not data_store:
        raise HTTPException(status_code=500, detail="DataStore not initialized.")
    return data_store


# -----------------------------------------------------------------------------
# Health Check
# -----------------------------------------------------------------------------
@app.get("/health", tags=["Utility"])
def health_check():
    """
    Basic health endpoint to verify the API is alive.
    """
    return {"status": "ok", "message": "Legislation API up and running"}


# -----------------------------------------------------------------------------
# User & Preferences
# -----------------------------------------------------------------------------
@app.post("/users/{email}/preferences", tags=["User"])
def update_user_preferences(
    email: str,
    prefs: UserPrefsPayload,
    store: DataStore = Depends(get_data_store)
):
    """
    Update or create user preferences for the given email.
    """
    success = store.save_user_preferences(email, prefs.dict())
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update preferences.")
    return {"status": "success", "message": f"Preferences updated for {email}"}


@app.get("/users/{email}/preferences", tags=["User"])
def get_user_preferences(
    email: str,
    store: DataStore = Depends(get_data_store)
):
    """
    Retrieve user preferences for the given email.
    """
    prefs = store.get_user_preferences(email)
    return {"email": email, "preferences": prefs}


# -----------------------------------------------------------------------------
# Search History
# -----------------------------------------------------------------------------
@app.post("/users/{email}/search", tags=["Search"])
def add_search_history(
    email: str,
    payload: UserSearchPayload,
    store: DataStore = Depends(get_data_store)
):
    """
    Add search history item for a user.
    """
    ok = store.add_search_history(email, payload.query, payload.results)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to add search history.")
    return {"status": "success", "message": f"Search recorded for {email}"}


@app.get("/users/{email}/search", tags=["Search"])
def get_search_history(
    email: str,
    store: DataStore = Depends(get_data_store)
):
    """
    Retrieve search history for a user.
    """
    history = store.get_search_history(email)
    return {"email": email, "history": history}


# -----------------------------------------------------------------------------
# Legislation Endpoints
# -----------------------------------------------------------------------------
@app.get("/legislation", tags=["Legislation"])
def list_legislation(
    limit: int = 50,
    offset: int = 0,
    store: DataStore = Depends(get_data_store)
):
    """
    Returns a list of legislation records (paged).
    """
    records = store.list_legislation(limit=limit, offset=offset)
    return {"count": len(records), "items": records}


@app.get("/legislation/{leg_id}", tags=["Legislation"])
def get_legislation_detail(
    leg_id: int,
    store: DataStore = Depends(get_data_store)
):
    """
    Retrieve a single legislation record with detail, including
    latest text and analysis if present.
    """
    details = store.get_legislation_details(leg_id)
    if not details:
        raise HTTPException(status_code=404, detail="Legislation not found")
    return details


@app.get("/legislation/search", tags=["Legislation"])
def search_legislation(
    keywords: str,
    store: DataStore = Depends(get_data_store)
):
    """
    Search for legislation whose title or description contains the given keywords (comma-separated).
    Example: /legislation/search?keywords=health,education
    """
    kws = [kw.strip() for kw in keywords.split(",") if kw.strip()]
    if not kws:
        return {"count": 0, "items": []}
    results = store.find_legislation_by_keywords(kws)
    return {"count": len(results), "items": results}


# -----------------------------------------------------------------------------
# AI Analysis Endpoint
# -----------------------------------------------------------------------------
@app.post("/legislation/{leg_id}/analysis", tags=["Analysis"])
def analyze_legislation_ai(
    leg_id: int,
    payload: AIAnalysisPayload = Body(...),
    store: DataStore = Depends(get_data_store)
):
    """
    Trigger an AI-based structured analysis for the specified Legislation ID.
    Optionally override the model_name.

    This calls the AIAnalysis logic, storing a new LegislationAnalysis version.
    Returns the new analysis record data.
    """
    # We can create a new Session from the store if we want direct AI calls
    db_session = store.db_session

    from ai_analysis import AIAnalysis  # import inside to avoid cyclical import if any
    ai_model = payload.model_name or "gpt-4o-2024-08-06"

    analyzer = AIAnalysis(db_session=db_session, model_name=ai_model)
    try:
        analysis_obj = analyzer.analyze_legislation(legislation_id=leg_id)
        return {
            "analysis_id": analysis_obj.id,
            "analysis_version": analysis_obj.analysis_version,
            "analysis_date": analysis_obj.analysis_date.isoformat()
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error analyzing legislation ID={leg_id} with AI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI analysis failed.")


# -----------------------------------------------------------------------------
# Utility / Maintenance
# -----------------------------------------------------------------------------
@app.post("/maintenance/flush-db", tags=["Maintenance"])
def flush_database(store: DataStore = Depends(get_data_store)):
    """
    Development-only endpoint to flush the entire DB.
    This should NOT be used in production unless you truly want to wipe data!
    """
    ok = store.flush_database()
    if not ok:
        raise HTTPException(status_code=500, detail="Database flush failed.")
    return {"status": "success", "message": "Database flushed (all data removed)."}

