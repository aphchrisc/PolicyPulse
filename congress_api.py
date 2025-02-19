import requests
from datetime import datetime, timedelta
import time
import logging
from typing import List, Dict, Optional, Union
import os
import json
from models import LegislationTracker, init_db
from sqlalchemy import and_, desc

logger = logging.getLogger(__name__)

class CongressAPI:
    def __init__(self):
        self.base_url = "https://api.congress.gov/v3"
        self.api_key = os.environ.get("CONGRESS_API_KEY")
        self.last_request = datetime.now()
        self.rate_limit_delay = 1.0  # Minimum seconds between requests; adjust as needed
        self.db_session = init_db()

    def _make_request(self, endpoint: str, params: Dict = None) -> Union[Dict, List]:
        if not self.api_key:
            raise ValueError("Congress.gov API key not found in environment variables")

        # Rate limiting: ensure a minimum delay between requests
        time_since_last = (datetime.now() - self.last_request).total_seconds()
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)

        params = params or {}
        params['api_key'] = self.api_key
        params['format'] = 'json'
        url = f"{self.base_url}/{endpoint}"
        logger.info(f"Making request to {url}")
        try:
            response = requests.get(url, params=params)
            self.last_request = datetime.now()
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as http_err:
                if response.status_code == 404:
                    logger.warning(f"Resource not found at {url}: {response.text}")
                    return {}
                else:
                    logger.error(f"HTTP error occurred: {http_err}")
                    raise
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise

    def fetch_new_legislation(self, days_back: int = 7, limit: int = 20, offset: int = 0) -> List[Dict]:
        """Fetch new legislation with enhanced progress tracking and resume capability"""
        try:
            current_year = datetime.now().year
            congress_number = ((current_year - 1789) // 2) + 1
            start_date = (datetime.now() - timedelta(days=days_back))
            logger.info(f"Fetching legislation from {start_date.strftime('%Y-%m-%d')} to present (limit: {limit}, offset: {offset})")

            # Save the current progress to allow resuming
            try:
                with open('fetch_progress.json', 'w') as f:
                    json.dump({'offset': offset, 'last_updated': datetime.now().isoformat()}, f)
            except Exception as e:
                logger.warning(f"Could not save progress: {e}")

            params = {
                'fromDateTime': start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'sort': 'updateDate desc',
                'limit': limit,
                'offset': offset
            }

            response = self._make_request(f'bill/{congress_number}', params)
            bills_data = []

            if isinstance(response, dict) and 'bills' in response:
                bills = response['bills']
                if isinstance(bills, dict) and 'bill' in bills:
                    bills_data = bills['bill']
                elif isinstance(bills, list):
                    bills_data = bills

            if not bills_data:
                logger.warning(f"No bills found in batch starting at offset {offset}")
                return []

            new_bills = []
            total_in_batch = len(bills_data)
            logger.info(f"Processing batch of {total_in_batch} bills (offset: {offset})")

            for index, bill in enumerate(bills_data, 1):
                try:
                    congress = bill.get('congress')
                    bill_type = bill.get('type', '').upper()
                    bill_number = bill.get('number')

                    if not all([congress, bill_type, bill_number]):
                        logger.warning(f"Missing required identifiers for bill: {bill}")
                        continue

                    # Check if this bill was already processed successfully
                    existing = self.db_session.query(LegislationTracker)\
                        .filter_by(congress=congress, bill_type=bill_type, bill_number=bill_number)\
                        .filter(LegislationTracker.last_updated >= start_date)\
                        .first()

                    if existing:
                        logger.info(f"Skipping already processed bill {bill_number}")
                        continue

                    logger.info(f"Processing bill {index}/{total_in_batch} in current batch: {congress}/{bill_type}/{bill_number}")
                    bill_info = self._get_bill_details(congress, bill_type, bill_number)

                    if not bill_info:
                        logger.warning(f"Could not fetch details for bill {bill_number}")
                        continue

                    summaries = self._get_bill_summaries(congress, bill_type, bill_number)
                    bill_info['summaries'] = summaries

                    formatted_bill = self._format_bill_data(bill_info)
                    if formatted_bill.get('title') and formatted_bill.get('number'):
                        new_bills.append(formatted_bill)
                        logger.info(f"Successfully processed bill {bill_number}")

                        # Commit after each successful bill to ensure it's saved
                        try:
                            self.db_session.commit()
                        except Exception as commit_error:
                            logger.error(f"Error committing bill {bill_number}: {commit_error}")
                            self.db_session.rollback()
                    else:
                        logger.warning(f"Skipping bill {bill_number} due to missing title or number")

                except Exception as e:
                    logger.error(f"Error processing bill {bill.get('number', 'unknown')}: {str(e)}")
                    self.db_session.rollback()
                    continue

            logger.info(f"Completed batch processing: {len(new_bills)}/{total_in_batch} bills successfully processed")
            return new_bills

        except Exception as e:
            logger.error(f"Error in fetch_new_legislation: {str(e)}")
            return []

    def _get_bill_details(self, congress: int, bill_type: str, bill_number: str) -> Dict:
        """Helper method to get bill details with enhanced logging"""
        try:
            response = self._make_request(f'bill/{congress}/{bill_type.lower()}/{bill_number}')
            if isinstance(response, dict) and 'bill' in response:
                bill_data = response['bill']
                logger.info(f"Retrieved details for bill {bill_number} with fields: {list(bill_data.keys())}")
                return bill_data
            logger.warning(f"Unexpected bill details response format for {bill_number}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching bill details for {bill_number}: {e}")
            return {}

    def _get_bill_summaries(self, congress: int, bill_type: str, bill_number: str) -> List:
        """Helper method to get bill summaries with enhanced error handling"""
        try:
            response = self._make_request(f'bill/{congress}/{bill_type.lower()}/{bill_number}/summaries')
            logger.info(f"Bill {bill_number} summaries response: {response}")

            if not isinstance(response, dict):
                logger.warning(f"Unexpected response type for {bill_number} summaries: {type(response)}")
                return []

            summaries = response.get('summaries', [])
            if isinstance(summaries, list):
                logger.info(f"Found {len(summaries)} summaries for bill {bill_number}")
                return summaries
            elif isinstance(summaries, dict):
                bill_summaries = summaries.get('billSummaries', [])
                logger.info(f"Found {len(bill_summaries)} summaries for bill {bill_number} in billSummaries")
                return bill_summaries if isinstance(bill_summaries, list) else []

            logger.warning(f"No valid summaries found for bill {bill_number}")
            return []
        except Exception as e:
            logger.error(f"Error fetching summaries for bill {bill_number}: {e}")
            return []

    def _format_bill_data(self, bill_info: Dict) -> Dict:
        """Helper method to format bill data"""
        try:
            formatted_bill = {
                'congress': bill_info.get('congress'),
                'type': bill_info.get('type', '').upper(),
                'number': bill_info.get('number'),
                'title': bill_info.get('title', ''),
                'introduced_date': bill_info.get('introducedDate', ''),
                'last_action_date': '',
                'last_action_text': '',
                'sponsors': [],
                'summary': '',
                'summaries': [],
                'raw_response': bill_info
            }

            # Handle latest action
            latest_action = bill_info.get('latestAction', {})
            if latest_action:
                formatted_bill['last_action_date'] = latest_action.get('actionDate', '')
                formatted_bill['last_action_text'] = latest_action.get('text', '')

            # Handle sponsors
            sponsors = bill_info.get('sponsors', [])
            if sponsors:
                formatted_bill['sponsors'] = [
                    sponsor.get('name', '')
                    for sponsor in sponsors if isinstance(sponsor, dict) and sponsor.get('name')
                ]

            # Handle summaries
            if bill_info.get('summaries'):
                if isinstance(bill_info['summaries'], list) and bill_info['summaries']:
                    summary_text = bill_info['summaries'][0].get('text', '')
                    if summary_text:
                        parts = summary_text.split('\n', 1)
                        formatted_bill['summary'] = (parts[0][:300] + '...') if len(parts[0]) > 300 else parts[0]
                formatted_bill['summaries'] = bill_info['summaries']

            logger.info(f"Formatted bill {formatted_bill['number']} with fields: {list(formatted_bill.keys())}")
            return formatted_bill
        except Exception as e:
            logger.error(f"Error formatting bill data: {str(e)}")
            return {}

    def get_bill_text(self, congress: int, bill_type: str, bill_number: str) -> Optional[str]:
        """Get the full text of a bill"""
        try:
            response = self._make_request(f'bill/{congress}/{bill_type.lower()}/{bill_number}/text')
            if not response or 'textVersions' not in response:
                return None

            text_versions = response['textVersions']
            if not text_versions:
                return None

            # Look for formatted text first
            for version in text_versions:
                for fmt in version.get('formats', []):
                    if fmt.get('type') == 'Formatted Text':
                        text_response = requests.get(fmt['url'])
                        if text_response.ok:
                            return text_response.text

            # Fall back to any available format
            for version in text_versions:
                for fmt in version.get('formats', []):
                    if 'url' in fmt:
                        text_response = requests.get(fmt['url'])
                        if text_response.ok:
                            return text_response.text

            return None
        except Exception as e:
            logger.error(f"Error fetching bill text: {e}")
            return None

    def get_total_bill_count(self, days_back: int) -> int:
        """
        Returns the total number of bills available from the API based on the time window (days_back).
        """
        try:
            current_year = datetime.now().year
            congress_number = ((current_year - 1789) // 2) + 1
            start_date = (datetime.now() - timedelta(days=days_back))
            params = {
                'fromDateTime': start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'sort': 'updateDate desc',
                'limit': 1,
                'offset': 0
            }

            response = self._make_request(f'bill/{congress_number}', params)
            logger.info(f"Bill count API response: {response}")

            if not isinstance(response, dict):
                logger.error(f"Unexpected response type: {type(response)}")
                return 0

            # The Congress.gov API returns pagination info in the response
            if 'pagination' in response:
                return int(response['pagination'].get('count', 0))

            # Fallback to counting bills if pagination not available
            bills_section = response.get("bills", [])
            if isinstance(bills_section, dict):
                return int(bills_section.get("count", 0))
            elif isinstance(bills_section, list):
                return len(bills_section)

            logger.warning(f"Unexpected bills section format: {type(bills_section)}")
            return 0

        except Exception as e:
            logger.error(f"Error in get_total_bill_count: {str(e)}")
            return 0

    def fetch_and_save_full_bill_data(self, congress: int, bill_type: str, bill_number: str) -> Dict:
        """Fetch and save complete bill data with enhanced logging"""
        try:
            logger.info(f"Fetching complete data for bill {congress}/{bill_type}/{bill_number}")
            full_bill_data = self.fetch_full_bill_data(congress, bill_type, bill_number)

            if not full_bill_data.get("details"):
                logger.warning(f"No details found for bill {bill_number}")
                return {}

            logger.info(f"Fetching bill text for {bill_number}")
            bill_text = self.get_bill_text(congress, bill_type, bill_number)
            if bill_text:
                logger.info(f"Successfully retrieved bill text for {bill_number} ({len(bill_text)} characters)")
            else:
                logger.warning(f"No bill text found for {bill_number}")

            formatted_bill = {
                'congress': congress,
                'type': bill_type.upper(),
                'number': bill_number,
                'title': full_bill_data.get("details", {}).get("title", ""),
                'introduced_date': full_bill_data.get("details", {}).get("introducedDate", ""),
                'last_action_date': "",
                'last_action_text': "",
                'sponsors': [],
                'summary': "",
                'raw_response': full_bill_data,
                'bill_text': bill_text or ""
            }

            # Extract and format additional data
            latest_action = full_bill_data.get("details", {}).get("latestAction", {})
            if latest_action:
                formatted_bill['last_action_date'] = latest_action.get('actionDate', '')
                formatted_bill['last_action_text'] = latest_action.get('text', '')
                logger.info(f"Latest action for {bill_number}: {formatted_bill['last_action_text']}")

            sponsors = full_bill_data.get("details", {}).get("sponsors", [])
            if sponsors:
                formatted_bill['sponsors'] = [
                    sponsor.get('name', '') for sponsor in sponsors 
                    if isinstance(sponsor, dict) and sponsor.get('name')
                ]
                logger.info(f"Found {len(formatted_bill['sponsors'])} sponsors for {bill_number}")

            summaries = full_bill_data.get("summaries", [])
            if summaries and isinstance(summaries, list) and summaries:
                summary_text = summaries[0].get('text', '')
                if summary_text:
                    parts = summary_text.split('\n', 1)
                    formatted_bill['summary'] = (parts[0][:300] + '...') if len(parts[0]) > 300 else parts[0]
                    logger.info(f"Added summary for {bill_number}")

            # Save to database with proper error handling
            current_time = datetime.now()
            try:
                existing_bill = self.db_session.query(LegislationTracker).filter(
                    and_(
                        LegislationTracker.congress == congress,
                        LegislationTracker.bill_type == bill_type.upper(),
                        LegislationTracker.bill_number == bill_number
                    )
                ).first()

                if existing_bill:
                    existing_bill.title = formatted_bill['title']
                    existing_bill.status = f"{formatted_bill['last_action_date']}: {formatted_bill['last_action_text']}"
                    existing_bill.introduced_date = datetime.strptime(formatted_bill['introduced_date'], '%Y-%m-%d') if formatted_bill['introduced_date'] else None
                    existing_bill.raw_api_response = formatted_bill['raw_response']
                    existing_bill.bill_text = formatted_bill['bill_text']
                    existing_bill.last_updated = current_time
                    if not formatted_bill.get('analysis') and existing_bill.analysis:
                        formatted_bill['analysis'] = existing_bill.analysis
                    logger.info(f"Updated existing bill {bill_number}")
                else:
                    new_bill = LegislationTracker(
                        congress=congress,
                        bill_type=bill_type.upper(),
                        bill_number=bill_number,
                        title=formatted_bill['title'],
                        status=f"{formatted_bill['last_action_date']}: {formatted_bill['last_action_text']}",
                        introduced_date=datetime.strptime(formatted_bill['introduced_date'], '%Y-%m-%d') if formatted_bill['introduced_date'] else None,
                        raw_api_response=formatted_bill['raw_response'],
                        bill_text=formatted_bill['bill_text'],
                        first_stored_date=current_time,
                        last_updated=current_time
                    )
                    self.db_session.add(new_bill)
                    logger.info(f"Created new bill record for {bill_number}")

                self.db_session.commit()
                return formatted_bill

            except Exception as db_error:
                logger.error(f"Database error processing bill {bill_number}: {str(db_error)}")
                self.db_session.rollback()
                return {}

        except Exception as e:
            logger.error(f"Error in fetch_and_save_full_bill_data: {str(e)}")
            return {}

    def fetch_full_bill_data(self, congress: int, bill_type: str, bill_number: str) -> Dict:
        full_data = {}
        try:
            details_response = self._make_request(f"bill/{congress}/{bill_type.lower()}/{bill_number}")
            full_data["details"] = details_response.get("bill", {}) if isinstance(details_response, dict) else {}
        except Exception as e:
            logger.error(f"Error fetching bill details: {e}")
            full_data["details"] = {}
        # (Additional endpoints omitted for brevity – see your existing implementation.)
        return full_data

    def check_updates(self, keywords: List[str]) -> List[Dict]:
        new_bills = self.fetch_new_legislation(days_back=1)
        matching_bills = []
        for bill in new_bills:
            title = bill.get('title', '').lower()
            if any(keyword.lower() in title for keyword in keywords):
                full_bill = self.fetch_and_save_full_bill_data(bill['congress'], bill['type'], bill['number'])
                matching_bills.append(full_bill)
        return matching_bills

    def _format_bill(self, bill: Dict) -> Dict:
        try:
            formatted_bill = {
                'congress': bill.get('congress'),
                'type': bill.get('type').lower() if bill.get('type') else "",
                'number': bill.get('number'),
                'title': bill.get('title', ''),
                'introduced_date': bill.get('introducedDate', ''),
                'last_action_date': '',
                'last_action_text': '',
                'sponsors': [],
                'summary': ''
            }
            latest_action = bill.get('latestAction', {})
            if latest_action:
                formatted_bill['last_action_date'] = latest_action.get('actionDate', '')
                formatted_bill['last_action_text'] = latest_action.get('text', '')
            sponsors = bill.get('sponsors', [])
            formatted_bill['sponsors'] = [
                sponsor.get('name', '')
                for sponsor in sponsors if isinstance(sponsor, dict) and sponsor.get('name')
            ]
            summaries = bill.get('summaries')
            if summaries and isinstance(summaries, list) and summaries:
                full_summary = summaries[0].get('text', '')
                if full_summary:
                    parts = full_summary.split('\n', 1)
                    formatted_bill['summary'] = (parts[0][:300] + '...') if len(parts[0]) > 300 else parts[0]
            elif bill.get('summary'):
                formatted_bill['summary'] = bill.get('summary')
            logger.info(f"Formatted bill {formatted_bill['number']} with fields: {list(formatted_bill.keys())}")
            return formatted_bill
        except Exception as e:
            logger.error(f"Error formatting bill data: {str(e)}")
            return {}