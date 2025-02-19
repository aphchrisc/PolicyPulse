from typing import Dict, List
from datetime import datetime
import json
from models import User, UserPreference, SearchHistory, LegislationTracker, init_db
from sqlalchemy.orm.session import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy import or_, text
import logging

logger = logging.getLogger(__name__)

class DataStore:
    def __init__(self):
        """Initialize database connection with retry logic"""
        self._init_db_connection()

    def _init_db_connection(self, max_retries=3):
        """Initialize database connection with retry mechanism"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                self.db = init_db()
                self.db_session = self.db  # Add this line to fix the missing db_session attribute
                logger.info("Database connection established successfully")
                return
            except OperationalError as e:
                retry_count += 1
                logger.warning(f"Database connection attempt {retry_count} failed: {e}")
                if retry_count == max_retries:
                    logger.error("Failed to establish database connection after maximum retries")
                    raise
                import time
                time.sleep(2 ** retry_count)  # Exponential backoff

    def _ensure_connection(self):
        """Ensure database connection is active, reconnect if needed"""
        try:
            # Test the connection using SQLAlchemy's text() function
            self.db.execute(text("SELECT 1"))
        except (OperationalError, SQLAlchemyError) as e:
            logger.warning(f"Database connection lost, attempting to reconnect: {e}")
            self._init_db_connection()

    def save_user_preferences(self, preferences: Dict, email: str = "default@user.com") -> bool:
        """Save user preferences to database with connection retry"""
        try:
            self._ensure_connection()
            user = self.db.query(User).filter_by(email=email).first()
            if not user:
                user = User(email=email)
                self.db.add(user)
                self.db.flush()
            if user.preferences:
                user.preferences.keywords = preferences.get('keywords', [])
                user.preferences.updated_at = datetime.utcnow()
            else:
                preference = UserPreference(
                    user_id=user.id,
                    keywords=preferences.get('keywords', [])
                )
                self.db.add(preference)
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error saving preferences: {e}")
            self.db.rollback()
            return False

    def get_user_preferences(self, email: str = "default@user.com") -> Dict:
        """Get user preferences with connection retry"""
        try:
            self._ensure_connection()
            user = self.db.query(User).filter_by(email=email).first()
            if user and user.preferences:
                return {'keywords': user.preferences.keywords}
            return {'keywords': []}
        except SQLAlchemyError as e:
            logger.error(f"Error loading preferences: {e}")
            return {'keywords': []}

    def add_search_history(self, search_data: Dict, email: str = "default@user.com") -> bool:
        """Add new search to history with connection retry"""
        try:
            self._ensure_connection()
            user = self.db.query(User).filter_by(email=email).first()
            if not user:
                user = User(email=email)
                self.db.add(user)
                self.db.flush()
            search = SearchHistory(
                user_id=user.id,
                query=search_data.get('query', ''),
                results=search_data.get('results', {})
            )
            self.db.add(search)
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error adding to history: {e}")
            self.db.rollback()
            return False

    def get_search_history(self, email: str = "default@user.com") -> List[Dict]:
        """Get search history from database with connection retry"""
        try:
            self._ensure_connection()
            user = self.db.query(User).filter_by(email=email).first()
            if not user:
                return []
            history = self.db.query(SearchHistory).filter_by(user_id=user.id)\
                .order_by(SearchHistory.timestamp.desc()).all()
            return [{
                'query': item.query,
                'timestamp': item.timestamp.isoformat(),
                'results': item.results
            } for item in history]
        except SQLAlchemyError as e:
            logger.error(f"Error loading history: {e}")
            return []

    def track_legislation(self, bill_data: Dict) -> bool:
        """Track new legislation or update existing one with enhanced error handling"""
        try:
            self._ensure_connection()
            bill = self.db.query(LegislationTracker)\
                .filter_by(bill_number=bill_data['number']).first()

            # Prepare the bill data with standardized format
            bill_attributes = {
                'congress': bill_data.get('congress'),
                'bill_type': bill_data.get('type', '').upper(),
                'bill_number': bill_data['number'],
                'title': bill_data.get('title', ''),
                'status': bill_data.get('last_action_text', ''),
                'introduced_date': datetime.strptime(bill_data.get('introduced_date', ''), '%Y-%m-%d') if bill_data.get('introduced_date') else None,
                'raw_api_response': bill_data.get('raw_response', {}),
                'bill_text': bill_data.get('bill_text', ''),
                'analysis': bill_data.get('analysis', {}),
                'last_updated': datetime.utcnow()
            }

            if bill:
                # Update existing bill preserving analysis if not provided
                if not bill_attributes['analysis'] and bill.analysis:
                    bill_attributes['analysis'] = bill.analysis
                # Update existing bill
                for key, value in bill_attributes.items():
                    setattr(bill, key, value)
                logger.info(f"Updated existing bill {bill_data['number']}")
            else:
                # Create new bill
                bill = LegislationTracker(**bill_attributes)
                self.db.add(bill)
                logger.info(f"Created new bill {bill_data['number']}")

            self.db.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error tracking legislation: {e}")
            self.db.rollback()
            return False

    def get_tracked_legislation(self) -> List[Dict]:
        """Get all tracked legislation with enhanced error handling and analysis status"""
        try:
            self._ensure_connection()
            bills = self.db.query(LegislationTracker)\
                .order_by(LegislationTracker.last_updated.desc()).all()
            return [{
                'number': bill.bill_number,
                'congress': bill.congress,
                'type': bill.bill_type,
                'title': bill.title,
                'status': bill.status,
                'introduced_date': bill.introduced_date.isoformat() if bill.introduced_date else None,
                'last_updated': bill.last_updated.isoformat(),
                'analysis': bill.analysis,
                'has_analysis': bool(bill.analysis),
                'analysis_timestamp': bill.analysis_timestamp.isoformat() if bill.analysis_timestamp else None,
                'bill_text': bill.bill_text,
                'raw_response': bill.raw_api_response,
                'public_health_impact': bill.public_health_impact,
                'local_gov_impact': bill.local_gov_impact,
                'public_health_reasoning': bill.public_health_reasoning,
                'local_gov_reasoning': bill.local_gov_reasoning,
            } for bill in bills]
        except SQLAlchemyError as e:
            logger.error(f"Error getting tracked legislation: {e}")
            return []

    def get_bills_by_keywords(self, keywords: List[str]) -> List[Dict]:
        """Search for bills with enhanced error handling"""
        try:
            self._ensure_connection()
            query = self.db.query(LegislationTracker)
            filters = [LegislationTracker.title.ilike(f"%{keyword}%") for keyword in keywords]
            if filters:
                query = query.filter(or_(*filters))
            bills = query.all()
            return [{
                'number': bill.bill_number,
                'congress': bill.congress,
                'type': bill.bill_type,
                'title': bill.title,
                'status': bill.status,
                'introduced_date': bill.introduced_date.isoformat() if bill.introduced_date else None,
                'last_updated': bill.last_updated.isoformat(),
                'analysis': bill.analysis,
                'bill_text': bill.bill_text,
                'raw_response': bill.raw_api_response
            } for bill in bills]
        except SQLAlchemyError as e:
            logger.error(f"Error searching bills: {e}")
            return []

    def update_bill_analysis(self, bill_number: str, analysis: Dict) -> bool:
        """Update bill analysis with enhanced error handling and timestamp"""
        try:
            self._ensure_connection()
            bill = self.db.query(LegislationTracker).filter_by(bill_number=bill_number).first()
            if not bill:
                logger.warning(f"Bill {bill_number} not found for analysis update")
                return False
            bill.analysis = analysis
            bill.analysis_timestamp = datetime.utcnow()  # Add timestamp for analysis
            bill.last_updated = datetime.utcnow()
            self.db.commit()
            logger.info(f"Updated analysis for bill {bill_number}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating bill analysis: {e}")
            self.db.rollback()
            return False

    def get_bill_analysis(self, bill_number: str) -> Dict:
        """Get bill analysis with status information"""
        try:
            self._ensure_connection()
            bill = self.db.query(LegislationTracker).filter_by(bill_number=bill_number).first()
            if not bill:
                logger.warning(f"Bill {bill_number} not found")
                return {}
            return {
                'analysis': bill.analysis,
                'has_analysis': bool(bill.analysis),
                'analysis_timestamp': bill.analysis_timestamp.isoformat() if hasattr(bill, 'analysis_timestamp') and bill.analysis_timestamp else None,
                'last_updated': bill.last_updated.isoformat() if bill.last_updated else None
            }
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving bill analysis: {e}")
            return {}

    def get_stored_analysis(self, bill_number: str) -> Dict:
        """Get stored analysis for a bill from the database"""
        try:
            self._ensure_connection()
            bill = self.db.query(LegislationTracker).filter_by(bill_number=bill_number).first()
            if bill and bill.analysis:
                return bill.analysis
            return None
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving stored analysis: {e}")
            return None

    def get_bill_by_number(self, bill_number: str) -> Dict:
        """Get a single bill by its number with enhanced error handling"""
        try:
            self._ensure_connection()
            bill = self.db.query(LegislationTracker).filter_by(bill_number=bill_number).first()
            if not bill:
                logger.warning(f"Bill {bill_number} not found")
                return {}
            return {
                'number': bill.bill_number,
                'congress': bill.congress,
                'type': bill.bill_type,
                'title': bill.title,
                'status': bill.status,
                'introduced_date': bill.introduced_date.isoformat() if bill.introduced_date else None,
                'last_updated': bill.last_updated.isoformat(),
                'analysis': bill.analysis,
                'bill_text': bill.bill_text,
                'raw_response': bill.raw_api_response,
                'public_health_impact': bill.public_health_impact,
                'local_gov_impact': bill.local_gov_impact
            }
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving bill by number: {e}")
            return {}

    def update_law_status(self, bill_number: str, law_data: Dict) -> bool:
        """Update a bill's law status and progression history"""
        try:
            self._ensure_connection()
            bill = self.db.query(LegislationTracker).filter_by(bill_number=bill_number).first()
            if not bill:
                logger.warning(f"Bill {bill_number} not found for law status update")
                return False

            # Update law-related fields
            bill.law_number = law_data.get('law_number')
            bill.law_type = law_data.get('law_type')
            bill.law_enacted_date = datetime.strptime(law_data.get('enacted_date', ''), '%Y-%m-%d') if law_data.get('enacted_date') else None
            bill.law_description = law_data.get('description')
            bill.progression_history = law_data.get('progression_history', [])
            bill.last_updated = datetime.utcnow()

            self.db.commit()
            logger.info(f"Updated law status for bill {bill_number}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating law status: {e}")
            self.db.rollback()
            return False

    def get_enacted_laws(self) -> List[Dict]:
        """Get all bills that have become laws"""
        try:
            self._ensure_connection()
            laws = self.db.query(LegislationTracker)\
                .filter(LegislationTracker.law_number.isnot(None))\
                .order_by(LegislationTracker.law_enacted_date.desc()).all()
            return [{
                'bill_number': law.bill_number,
                'congress': law.congress,
                'bill_type': law.bill_type,
                'title': law.title,
                'law_number': law.law_number,
                'law_type': law.law_type,
                'enacted_date': law.law_enacted_date.isoformat() if law.law_enacted_date else None,
                'description': law.law_description,
                'progression_history': law.progression_history,
                'analysis': law.analysis,
                'public_health_impact': law.public_health_impact,
                'local_gov_impact': law.local_gov_impact,
                'public_health_reasoning': law.public_health_reasoning,
                'local_gov_reasoning': law.local_gov_reasoning,
            } for law in laws]
        except SQLAlchemyError as e:
            logger.error(f"Error getting enacted laws: {e}")
            return []

    def get_law_progression(self, bill_number: str) -> Dict:
        """Get the progression history of a bill that became law"""
        try:
            self._ensure_connection()
            bill = self.db.query(LegislationTracker).filter_by(bill_number=bill_number).first()
            if not bill or not bill.law_number:
                return {}
            return {
                'bill_number': bill.bill_number,
                'law_number': bill.law_number,
                'law_type': bill.law_type,
                'enacted_date': bill.law_enacted_date.isoformat() if bill.law_enacted_date else None,
                'progression_history': bill.progression_history,
                'analysis': bill.analysis
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting law progression: {e}")
            return {}