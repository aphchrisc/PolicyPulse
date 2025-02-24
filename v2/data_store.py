"""
data_store.py

Provides a production-ready DataStore class that encapsulates common database 
operations for the legislative tracking system. It uses SQLAlchemy sessions 
from init_db() and manages:

 - User creation & preferences
 - Search history
 - Basic Legislation retrieval (optional expansions as needed)

The DataStore class also handles DB connection retries and ensures
rollback on SQLAlchemy errors.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

# Import your actual models and the init_db factory
from models import (
    init_db,
    User,
    UserPreference,
    SearchHistory,
    Legislation,
    # If you want to do direct queries or updates on analyses:
    LegislationAnalysis,
)

logger = logging.getLogger(__name__)


class DataStore:
    """
    DataStore centralizes your typical application-level DB operations
    (create user, set preferences, retrieve legislation, etc.).
    Useful if you want a single class approach to data access.
    """

    def __init__(self, max_retries: int = 3):
        """
        Initialize the DB connection with basic retry logic.
        :param max_retries: number of attempts to connect
        """
        self.max_retries = max_retries
        self.db_session = None
        self._init_db_connection()

    def _init_db_connection(self):
        """
        Create a Session factory from init_db() and instantiate a Session. 
        Retries on OperationalError if the DB is temporarily unreachable.
        """
        attempt = 0
        while attempt < self.max_retries:
            try:
                session_factory = init_db(max_retries=1)  # init_db has its own retry logic
                self.db_session = session_factory()       # create a Session instance
                logger.info("Database session established successfully.")
                return
            except OperationalError as e:
                attempt += 1
                logger.warning(f"DB connection attempt {attempt} failed: {e}")
                if attempt == self.max_retries:
                    logger.error("Failed to connect to DB after max retries.")
                    raise
                import time
                time.sleep(2 ** attempt)  # Exponential backoff

    def _ensure_connection(self):
        """
        Ensure the connection is still alive by executing a trivial SQL query.
        If the connection fails, re-init DB.
        """
        try:
            self.db_session.execute(text("SELECT 1"))
        except (OperationalError, SQLAlchemyError) as e:
            logger.warning(f"DB connection lost, attempting reconnect: {e}")
            self._init_db_connection()

    # --------------------------------------------------------------------------
    # USER & PREFERENCES
    # --------------------------------------------------------------------------
    def get_or_create_user(self, email: str) -> User:
        """
        Return existing user by email or create a new one if not found.
        Commits the new user to DB.
        """
        self._ensure_connection()
        try:
            user = self.db_session.query(User).filter_by(email=email).first()
            if not user:
                user = User(email=email)
                self.db_session.add(user)
                self.db_session.commit()
            return user
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving/creating user {email}: {e}", exc_info=True)
            self.db_session.rollback()
            raise  # re-raise or handle

    def save_user_preferences(self, email: str, new_prefs: Dict) -> bool:
        """
        Creates or updates a user's preference record. 
        `new_prefs` might contain `{"keywords": [...], ...}` etc.
        """
        self._ensure_connection()
        try:
            user = self.get_or_create_user(email)
            if user.preferences:
                # update existing preferences
                user_pref = user.preferences
                # Example: you might have more fields
                user_pref.keywords = new_prefs.get('keywords', [])
            else:
                # create new user preferences
                user_pref = UserPreference(
                    user_id=user.id,
                    keywords=new_prefs.get('keywords', [])
                )
                self.db_session.add(user_pref)

            self.db_session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error saving preferences for {email}: {e}", exc_info=True)
            self.db_session.rollback()
            return False

    def get_user_preferences(self, email: str) -> Dict:
        """
        Retrieve user preferences as a dictionary. Returns an empty structure if not found.
        """
        self._ensure_connection()
        try:
            user = self.db_session.query(User).filter_by(email=email).first()
            if user and user.preferences:
                return {"keywords": user.preferences.keywords or []}
            else:
                return {"keywords": []}
        except SQLAlchemyError as e:
            logger.error(f"Error loading preferences for {email}: {e}", exc_info=True)
            return {"keywords": []}

    # --------------------------------------------------------------------------
    # SEARCH HISTORY
    # --------------------------------------------------------------------------
    def add_search_history(self, email: str, query_string: str, results_data: dict) -> bool:
        """
        Log the user's search into SearchHistory. `results_data` can store search results as JSONB.
        """
        self._ensure_connection()
        try:
            user = self.get_or_create_user(email)
            new_search = SearchHistory(
                user_id=user.id,
                query=query_string,
                results=results_data
            )
            self.db_session.add(new_search)
            self.db_session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error adding search history for {email}: {e}", exc_info=True)
            self.db_session.rollback()
            return False

    def get_search_history(self, email: str) -> List[Dict]:
        """
        Return the user's search history as a list of dicts with 'query', 'results', 'created_at', etc.
        """
        self._ensure_connection()
        try:
            user = self.db_session.query(User).filter_by(email=email).first()
            if not user:
                return []
            # We assume ordering by creation time descending
            history = self.db_session.query(SearchHistory)\
                .filter_by(user_id=user.id)\
                .order_by(SearchHistory.created_at.desc())\
                .all()

            return [
                {
                    "query": h.query,
                    "results": h.results,
                    "created_at": h.created_at.isoformat()
                }
                for h in history
            ]
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving search history for {email}: {e}", exc_info=True)
            return []

    # --------------------------------------------------------------------------
    # LEGISLATION
    # --------------------------------------------------------------------------
    def list_legislation(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        Retrieve a paginated list of legislation records, returning minimal fields for quick listing.
        """
        self._ensure_connection()
        try:
            query = self.db_session.query(Legislation).order_by(Legislation.updated_at.desc())
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            records = query.all()

            result = []
            for leg in records:
                result.append({
                    "id": leg.id,
                    "external_id": leg.external_id,
                    "govt_source": leg.govt_source,
                    "bill_number": leg.bill_number,
                    "title": leg.title,
                    "bill_status": leg.bill_status.value if leg.bill_status else None,
                    "updated_at": leg.updated_at.isoformat() if leg.updated_at else None,
                })
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error listing legislation: {e}", exc_info=True)
            return []

    def get_legislation_details(self, legislation_id: int) -> Optional[Dict]:
        """
        Retrieve a single Legislation record with more detail, including text & analyses if needed.
        """
        self._ensure_connection()
        try:
            leg = self.db_session.query(Legislation).filter_by(id=legislation_id).first()
            if not leg:
                return None

            # If you want to include the latest text and the latest analysis:
            text_rec = leg.latest_text
            analysis_rec = leg.latest_analysis

            details = {
                "id": leg.id,
                "external_id": leg.external_id,
                "govt_source": leg.govt_source,
                "bill_number": leg.bill_number,
                "title": leg.title,
                "description": leg.description,
                "bill_status": leg.bill_status.value if leg.bill_status else None,
                "bill_introduced_date": leg.bill_introduced_date.isoformat() if leg.bill_introduced_date else None,
                "bill_last_action_date": leg.bill_last_action_date.isoformat() if leg.bill_last_action_date else None,
                "bill_status_date": leg.bill_status_date.isoformat() if leg.bill_status_date else None,
                "last_api_check": leg.last_api_check.isoformat() if leg.last_api_check else None,
                "created_at": leg.created_at.isoformat() if leg.created_at else None,
                "updated_at": leg.updated_at.isoformat() if leg.updated_at else None,
                "latest_text": text_rec.text_content if text_rec else None,
                "analysis": None
            }
            if analysis_rec:
                details["analysis"] = {
                    "id": analysis_rec.id,
                    "analysis_version": analysis_rec.analysis_version,
                    "summary": analysis_rec.summary,
                    "key_points": analysis_rec.key_points,
                    "created_at": analysis_rec.created_at.isoformat() if analysis_rec.created_at else None,
                    "analysis_date": analysis_rec.analysis_date.isoformat() if analysis_rec.analysis_date else None,
                    # etc., or any relevant fields
                }

            return details
        except SQLAlchemyError as e:
            logger.error(f"Error loading details for legislation {legislation_id}: {e}", exc_info=True)
            return None

    def find_legislation_by_keywords(self, keywords: List[str]) -> List[Dict]:
        """
        Performs a naive search for legislation whose title or description 
        contains any of the given keywords (case-insensitive).
        """
        self._ensure_connection()
        try:
            if not keywords:
                return []

            # For robust text search, consider TSVector fields on title/description.
            # For now, just do an OR across each keyword in .title + .description
            or_clauses = []
            for kw in keywords:
                pattern = f"%{kw}%"
                or_clauses.append(Legislation.title.ilike(pattern))
                or_clauses.append(Legislation.description.ilike(pattern))

            if not or_clauses:
                return []

            query = self.db_session.query(Legislation).filter(or_(*or_clauses)).limit(100)
            records = query.all()

            output = []
            for leg in records:
                output.append({
                    "id": leg.id,
                    "bill_number": leg.bill_number,
                    "title": leg.title,
                    "description": leg.description,
                    "bill_status": leg.bill_status.value if leg.bill_status else None
                })
            return output
        except SQLAlchemyError as e:
            logger.error(f"Error searching legislation by keywords {keywords}: {e}", exc_info=True)
            return []

    # --------------------------------------------------------------------------
    # MISC UTILITIES
    # --------------------------------------------------------------------------
    def flush_database(self) -> bool:
        """
        Example method to 'flush' or clear your DB data. 
        Typically you might only do this in dev or test environments!
        """
        self._ensure_connection()
        try:
            # If you want to wipe everything:
            # This approach depends on your model definitions and relationships
            # Typically you'd do `db_session.query(Model).delete()`, etc.
            # Example partial flush:
            self.db_session.query(SearchHistory).delete()
            self.db_session.query(UserPreference).delete()
            self.db_session.query(User).delete()
            self.db_session.query(LegislationAnalysis).delete()
            self.db_session.query(Legislation).delete()
            self.db_session.commit()
            logger.warning("Database flush completed.")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error flushing database: {e}", exc_info=True)
            self.db_session.rollback()
            return False

    def close(self):
        """
        Cleanly close the current DB session if it exists.
        """
        if self.db_session:
            self.db_session.close()
            logger.info("DB session closed.")

