# File: congress_api.py

import os
import logging
from typing import List, Dict, Any, Union, Optional, cast
import requests
from datetime import datetime, timedelta
import time
import json
from models import LegislationTracker, init_db
from sqlalchemy import and_

logger = logging.getLogger(__name__)

class CongressAPI:
    def __init__(self) -> None:
        self.base_url: str = "https://api.congress.gov/v3"
        self.api_key: Optional[str] = os.environ.get("CONGRESS_API_KEY")
        if not self.api_key:
            raise ValueError("Congress.gov API key not found in environment variables")
        self.last_request: datetime = datetime.now()
        self.rate_limit_delay: float = 1.0  # Minimum seconds between requests
        self.db_session = init_db()

    def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Union[Dict[str, Any], List[Any]]:
        if not self.api_key:
            raise ValueError("Congress.gov API key not found in environment variables")

        # Rate limiting: ensure a minimum delay between requests
        time_since_last = (datetime.now() - self.last_request).total_seconds()
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)

        params = params or {}
        params["api_key"] = self.api_key
        params["format"] = "json"
        url = f"{self.base_url}/{endpoint}"
        logger.info(f"Making request to {url} with params: {params}")
        try:
            response = requests.get(url, params=params, timeout=30)
            self.last_request = datetime.now()
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as http_err:
                if response.status_code == 404:
                    logger.warning(f"Resource not found at {url}: {response.text}")
                    return {}  # type: ignore
                else:
                    logger.error(f"HTTP error occurred: {http_err}")
                    raise
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise

    def fetch_new_legislation(
        self, days_back: int = 7, limit: int = 20, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Fetch new legislation with progress tracking and resume capability."""
        try:
            current_year = datetime.now().year
            congress_number = ((current_year - 1789) // 2) + 1
            start_date = datetime.now() - timedelta(days=days_back)
            logger.info(
                f"Fetching legislation from {start_date.strftime('%Y-%m-%d')} to present (limit: {limit}, offset: {offset})"
            )

            # Save progress for resume capability
            try:
                with open("fetch_progress.json", "w") as f:
                    json.dump(
                        {"offset": offset, "last_updated": datetime.now().isoformat()}, f
                    )
            except Exception as e:
                logger.warning(f"Could not save progress: {e}")

            params = {
                "fromDateTime": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sort": "updateDate desc",
                "limit": limit,
                "offset": offset,
            }

            response = self._make_request(f"bill/{congress_number}", params)
            # Cast response to a dict if possible
            resp_dict: Dict[str, Any] = response if isinstance(response, dict) else {}
            bills_data = []
            if "bills" in resp_dict:
                bills = resp_dict["bills"]
                if isinstance(bills, dict) and "bill" in bills:
                    bills_data = bills["bill"]
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
                    congress = bill.get("congress")
                    bill_type = (bill.get("type") or "").upper()
                    bill_number = bill.get("number")

                    if not (congress and bill_type and bill_number):
                        logger.warning(f"Missing required identifiers for bill: {bill}")
                        continue

                    # Use an explicit check for None for the query
                    existing = (
                        self.db_session.query(LegislationTracker)
                        .filter_by(congress=congress, bill_type=bill_type, bill_number=bill_number)
                        .filter(LegislationTracker.last_updated >= start_date)  # type: ignore
                        .first()
                    )
                    if existing is not None:
                        logger.info(f"Skipping already processed bill {bill_number}")
                        continue

                    logger.info(
                        f"Processing bill {index}/{total_in_batch}: {congress}/{bill_type}/{bill_number}"
                    )
                    bill_info = self._get_bill_details(congress, bill_type, bill_number)
                    if not bill_info:
                        logger.warning(f"Could not fetch details for bill {bill_number}")
                        continue

                    summaries = self._get_bill_summaries(congress, bill_type, bill_number)
                    bill_info["summaries"] = summaries

                    formatted_bill = self._format_bill_data(bill_info)
                    if formatted_bill.get("title") and formatted_bill.get("number"):
                        new_bills.append(formatted_bill)
                        logger.info(f"Successfully processed bill {bill_number}")
                        try:
                            self.db_session.commit()
                        except Exception as commit_error:
                            logger.error(f"Error committing bill {bill_number}: {commit_error}")
                            self.db_session.rollback()
                    else:
                        logger.warning(
                            f"Skipping bill {bill_number} due to missing title or number"
                        )
                except Exception as e:
                    logger.error(f"Error processing bill {bill.get('number', 'unknown')}: {str(e)}")
                    self.db_session.rollback()
                    continue

            logger.info(
                f"Completed batch: {len(new_bills)}/{total_in_batch} bills processed successfully"
            )
            return new_bills

        except Exception as e:
            logger.error(f"Error in fetch_new_legislation: {str(e)}")
            return []

    def _get_bill_details(self, congress: int, bill_type: str, bill_number: str) -> Dict[str, Any]:
        """Retrieve detailed information for a given bill."""
        try:
            response = self._make_request(f"bill/{congress}/{bill_type.lower()}/{bill_number}")
            resp_dict: Dict[str, Any] = response if isinstance(response, dict) else {}
            if "bill" in resp_dict:
                bill_data = resp_dict["bill"]
                logger.info(f"Retrieved details for bill {bill_number}: {list(bill_data.keys())}")
                return bill_data
            logger.warning(f"Unexpected bill details format for {bill_number}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching bill details for {bill_number}: {e}")
            return {}

    def _get_bill_summaries(self, congress: int, bill_type: str, bill_number: str) -> List[Any]:
        """Retrieve bill summaries."""
        try:
            response = self._make_request(f"bill/{congress}/{bill_type.lower()}/{bill_number}/summaries")
            resp_dict: Dict[str, Any] = response if isinstance(response, dict) else {}
            logger.info(f"Bill {bill_number} summaries response: {resp_dict}")

            if not isinstance(resp_dict, dict):
                logger.warning(f"Unexpected summaries response type for {bill_number}: {type(resp_dict)}")
                return []

            summaries = resp_dict.get("summaries", [])
            if isinstance(summaries, list):
                logger.info(f"Found {len(summaries)} summaries for bill {bill_number}")
                return summaries
            elif isinstance(summaries, dict):
                bill_summaries = summaries.get("billSummaries", [])
                logger.info(f"Found {len(bill_summaries)} summaries in billSummaries for {bill_number}")
                return bill_summaries if isinstance(bill_summaries, list) else []
            logger.warning(f"No valid summaries found for bill {bill_number}")
            return []
        except Exception as e:
            logger.error(f"Error fetching summaries for bill {bill_number}: {e}")
            return []

    def _format_bill_data(self, bill_info: Dict[str, Any]) -> Dict[str, Any]:
        """Format raw bill data into a standard dictionary."""
        try:
            formatted_bill: Dict[str, Any] = {
                "congress": bill_info.get("congress"),
                "type": (bill_info.get("type") or "").upper(),
                "number": bill_info.get("number"),
                "title": bill_info.get("title", ""),
                "introduced_date": bill_info.get("introducedDate", ""),
                "last_action_date": "",
                "last_action_text": "",
                "sponsors": [],
                "summary": "",
                "summaries": [],
                "raw_response": bill_info,
            }

            latest_action = bill_info.get("latestAction", {})
            if latest_action:
                formatted_bill["last_action_date"] = latest_action.get("actionDate", "")
                formatted_bill["last_action_text"] = latest_action.get("text", "")

            sponsors = bill_info.get("sponsors", [])
            if sponsors:
                formatted_bill["sponsors"] = [
                    sponsor.get("name", "")
                    for sponsor in sponsors
                    if isinstance(sponsor, dict) and sponsor.get("name")
                ]

            if bill_info.get("summaries"):
                if isinstance(bill_info["summaries"], list) and bill_info["summaries"]:
                    summary_text = bill_info["summaries"][0].get("text", "")
                    if summary_text:
                        parts = summary_text.split("\n", 1)
                        formatted_bill["summary"] = (
                            parts[0][:300] + "..."
                            if len(parts[0]) > 300
                            else parts[0]
                        )
                formatted_bill["summaries"] = bill_info["summaries"]

            logger.info(f"Formatted bill {formatted_bill.get('number')} with fields: {list(formatted_bill.keys())}")
            return formatted_bill
        except Exception as e:
            logger.error(f"Error formatting bill data: {str(e)}")
            return {}

    def get_bill_text_and_formats(self, congress: int, bill_type: str, bill_number: str) -> Dict[str, Any]:
        """Retrieve the full text and available document formats for a bill."""
        try:
            response = self._make_request(f"bill/{congress}/{bill_type.lower()}/{bill_number}/text")
            # Cast response to a dict if possible
            resp_dict: Dict[str, Any] = response if isinstance(response, dict) else {}
            if not resp_dict or "textVersions" not in resp_dict:
                logger.warning(f"No text versions found for bill {bill_number}")
                return {"text": None, "formats": {}}
            text_versions = resp_dict["textVersions"]
            if not text_versions:
                logger.warning(f"Empty text versions for bill {bill_number}")
                return {"text": None, "formats": {}}

            # Prioritize the enrolled version (final version that becomes law)
            enrolled_version = next(
                (version for version in text_versions if version.get("type") == "Enrolled Bill"),
                None,
            )
            version_to_use = enrolled_version if enrolled_version else text_versions[0]

            result: Dict[str, Any] = {"text": None, "formats": {}}
            if version_to_use:
                for fmt in version_to_use.get("formats", []):
                    fmt_type = fmt.get("type")
                    url = fmt.get("url")
                    if fmt_type and url:
                        result["formats"][fmt_type] = url
                        if fmt_type == "Formatted Text" and result["text"] is None:
                            try:
                                text_response = requests.get(url, timeout=30)
                                if text_response.ok:
                                    result["text"] = text_response.text
                            except requests.exceptions.RequestException as req_e:
                                logger.error(f"Error fetching formatted text from {url}: {req_e}")
            return result

        except Exception as e:
            logger.error(f"Error fetching bill text and formats: {e}")
            return {"text": None, "formats": {}}

    def get_total_bill_count(self, days_back: int) -> int:
        """
        Return the total number of bills available from the API based on the given time window.
        """
        try:
            current_year = datetime.now().year
            congress_number = ((current_year - 1789) // 2) + 1
            start_date = datetime.now() - timedelta(days=days_back)
            params = {
                "fromDateTime": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sort": "updateDate desc",
                "limit": 1,
                "offset": 0,
            }
            response = self._make_request(f"bill/{congress_number}", params)
            logger.info(f"Bill count API response: {response}")

            if not isinstance(response, dict):
                logger.error(f"Unexpected response type: {type(response)}")
                return 0

            if "pagination" in response:
                return int(response["pagination"].get("count", 0))

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

    def fetch_and_save_full_bill_data(
        self, congress: int, bill_type: str, bill_number: str
    ) -> Dict[str, Any]:
        """Fetch complete bill data and store it in the database."""
        try:
            logger.info(f"Fetching full data for bill {congress}/{bill_type}/{bill_number}")
            full_bill_data = self.fetch_full_bill_data(congress, bill_type, bill_number)
            if not full_bill_data.get("details"):
                logger.warning(f"No details found for bill {bill_number}")
                return {}

            logger.info(f"Fetching bill text for {bill_number}")
            bill_text = self.get_bill_text_and_formats(congress, bill_type, bill_number).get("text")
            if bill_text:
                logger.info(f"Retrieved bill text for {bill_number} ({len(bill_text)} characters)")
            else:
                logger.warning(f"No bill text found for {bill_number}")

            formatted_bill: Dict[str, Any] = {
                "congress": congress,
                "type": bill_type.upper(),
                "number": bill_number,
                "title": full_bill_data.get("details", {}).get("title", ""),
                "introduced_date": full_bill_data.get("details", {}).get("introducedDate", ""),
                "last_action_date": "",
                "last_action_text": "",
                "sponsors": [],
                "summary": "",
                "raw_response": full_bill_data,
                "bill_text": bill_text or "",
            }

            latest_action = full_bill_data.get("details", {}).get("latestAction", {})
            if latest_action:
                formatted_bill["last_action_date"] = latest_action.get("actionDate", "")
                formatted_bill["last_action_text"] = latest_action.get("text", "")
                logger.info(f"Latest action for {bill_number}: {formatted_bill['last_action_text']}")

            sponsors = full_bill_data.get("details", {}).get("sponsors", [])
            if sponsors:
                formatted_bill["sponsors"] = [
                    sponsor.get("name", "")
                    for sponsor in sponsors
                    if isinstance(sponsor, dict) and sponsor.get("name")
                ]
                logger.info(f"Found {len(formatted_bill['sponsors'])} sponsors for {bill_number}")

            summaries = full_bill_data.get("summaries", [])
            if summaries and isinstance(summaries, list) and summaries:
                summary_text = summaries[0].get("text", "")
                if summary_text:
                    parts = summary_text.split("\n", 1)
                    formatted_bill["summary"] = (
                        parts[0][:300] + "..."
                        if len(parts[0]) > 300
                        else parts[0]
                    )
                    logger.info(f"Added summary for {bill_number}")

            current_time = datetime.now()
            # Safely parse introduced_date
            introduced_date: Optional[datetime] = None
            date_str = formatted_bill.get("introduced_date", "")
            if date_str:
                try:
                    introduced_date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    logger.warning(f"Unable to parse introduced_date '{date_str}' for bill {bill_number}")

            try:
                existing_bill = (
                    self.db_session.query(LegislationTracker)
                    .filter(
                        and_(
                            LegislationTracker.congress == congress,
                            LegislationTracker.bill_type == bill_type.upper(),
                            LegislationTracker.bill_number == bill_number,
                        )
                    )
                    .first()
                )

                if existing_bill is not None:
                    existing_bill.title = formatted_bill["title"]
                    existing_bill.status = f"{formatted_bill['last_action_date']}: {formatted_bill['last_action_text']}"  # type: ignore
                    existing_bill.introduced_date = introduced_date  # type: ignore
                    existing_bill.raw_api_response = formatted_bill["raw_response"]
                    existing_bill.bill_text = formatted_bill["bill_text"]
                    existing_bill.last_updated = current_time  # type: ignore
                    if not formatted_bill.get("analysis") and (existing_bill.analysis is not None):
                        formatted_bill["analysis"] = existing_bill.analysis

                    logger.info(f"Updated existing bill {bill_number}")
                else:
                    new_bill = LegislationTracker(
                        congress=congress,
                        bill_type=bill_type.upper(),
                        bill_number=bill_number,
                        title=formatted_bill["title"],
                        status=f"{formatted_bill['last_action_date']}: {formatted_bill['last_action_text']}",  # type: ignore
                        introduced_date=introduced_date,  # type: ignore
                        raw_api_response=formatted_bill["raw_response"],
                        bill_text=formatted_bill["bill_text"],
                        first_stored_date=current_time,
                        last_updated=current_time,  # type: ignore
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

    def fetch_full_bill_data(self, congress: int, bill_type: str, bill_number: str) -> Dict[str, Any]:
        """Retrieve full bill data from the API."""
        full_data: Dict[str, Any] = {}
        try:
            details_response = self._make_request(f"bill/{congress}/{bill_type.lower()}/{bill_number}")
            full_data["details"] = (
                details_response.get("bill", {}) if isinstance(details_response, dict) else {}
            )
        except Exception as e:
            logger.error(f"Error fetching bill details: {e}")
            full_data["details"] = {}
        # (Additional endpoints omitted for brevity)
        return full_data

    def check_updates(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Check for recent bills matching specified keywords and fetch full data for them."""
        new_bills = self.fetch_new_legislation(days_back=1)
        matching_bills = []
        for bill in new_bills:
            title = bill.get("title", "").lower()
            if any(keyword.lower() in title for keyword in keywords):
                full_bill = self.fetch_and_save_full_bill_data(bill["congress"], bill["type"], bill["number"])
                matching_bills.append(full_bill)
        return matching_bills

    def _format_bill(self, bill: Dict[str, Any]) -> Dict[str, Any]:
        """Alternate helper to format bill data."""
        try:
            formatted_bill: Dict[str, Any] = {
                "congress": bill.get("congress"),
                "type": (bill.get("type") or "").lower(),
                "number": bill.get("number"),
                "title": bill.get("title", ""),
                "introduced_date": bill.get("introducedDate", ""),
                "last_action_date": "",
                "last_action_text": "",
                "sponsors": [],
                "summary": "",
            }
            latest_action = bill.get("latestAction", {})
            if latest_action:
                formatted_bill["last_action_date"] = latest_action.get("actionDate", "")
                formatted_bill["last_action_text"] = latest_action.get("text", "")
            sponsors = bill.get("sponsors", [])
            formatted_bill["sponsors"] = [
                sponsor.get("name", "")
                for sponsor in sponsors
                if isinstance(sponsor, dict) and sponsor.get("name")
            ]
            summaries = bill.get("summaries")
            if summaries and isinstance(summaries, list) and summaries:
                full_summary = summaries[0].get("text", "")
                if full_summary:
                    parts = full_summary.split("\n", 1)
                    formatted_bill["summary"] = (
                        parts[0][:300] + "..." if len(parts[0]) > 300 else parts[0]
                    )
            elif bill.get("summary"):
                formatted_bill["summary"] = bill.get("summary")
            logger.info(f"Formatted bill {formatted_bill.get('number')} with fields: {list(formatted_bill.keys())}")
            return formatted_bill
        except Exception as e:
            logger.error(f"Error formatting bill data: {str(e)}")
            return {}

    def get_law_details(self, congress: int, law_type: str, law_number: str) -> Dict[str, Any]:
        """Fetch details for a specific law."""
        try:
            formatted_law_type = law_type.lower().replace(" ", "")
            response = self._make_request(f"law/{congress}/{formatted_law_type}/{law_number}")
            resp_dict: Dict[str, Any] = response if isinstance(response, dict) else {}
            logger.info(f"Law details response: {resp_dict}")

            if "law" in resp_dict:
                law_data = resp_dict["law"]
                logger.info(f"Retrieved law details for {law_type} {law_number}")

                bill_number = law_data.get("billNumber")
                bill_type = law_data.get("billType")
                if bill_number and bill_type:
                    logger.info(f"Fetching text for associated bill {bill_type} {bill_number}")
                    bill_text = self.get_bill_text_and_formats(congress, bill_type, bill_number).get("text")
                    if bill_text:
                        law_data["bill_text"] = bill_text
                        logger.info(f"Retrieved bill text for law {law_number}")
                    else:
                        logger.warning(f"Could not retrieve bill text for law {law_number}")
                        bill_details = self._get_bill_details(congress, bill_type, bill_number)
                        if bill_details:
                            law_data["bill_details"] = bill_details
                            summaries = self._get_bill_summaries(congress, bill_type, bill_number)
                            if summaries:
                                law_data["bill_text"] = summaries[0].get("text", "")
                                logger.info(f"Using bill summary as fallback for law {law_number}")

                return law_data

            logger.warning(f"Unexpected law details format for {law_number}")
            return {}

        except Exception as e:
            logger.error(f"Error fetching law details: {e}")
            return {}

    def track_bill_to_law_progression(
        self, congress: int, bill_type: str, bill_number: str
    ) -> Dict[str, Any]:
        """Track a bill’s progression to becoming a law."""
        try:
            bill_details = self._get_bill_details(congress, bill_type, bill_number)
            if not bill_details:
                return {"status": "error", "message": "Bill not found"}

            latest_action = bill_details.get("latestAction", {})
            law_info = {}
            if bill_details.get("isPrivate") is not None:
                law_type = "private" if bill_details.get("isPrivate") else "public"
                law_number = bill_details.get("lawNumber")
                if law_number:
                    law_info = self.get_law_details(congress, law_type, law_number)

            progression_data: Dict[str, Any] = {
                "bill_info": bill_details,
                "became_law": bool(law_info),
                "law_info": law_info,
                "progression_history": [],
            }

            try:
                actions_response = self._make_request(f"bill/{congress}/{bill_type.lower()}/{bill_number}/actions")
                if isinstance(actions_response, dict) and "actions" in actions_response:
                    actions = actions_response["actions"]
                    progression_data["progression_history"] = [
                        {
                            "date": action.get("actionDate"),
                            "text": action.get("text"),
                            "type": action.get("type"),
                            "chamber": action.get("chamber"),
                        }
                        for action in actions
                    ]
            except Exception as e:
                logger.error(f"Error fetching bill actions: {e}")

            return progression_data

        except Exception as e:
            logger.error(f"Error tracking bill to law progression: {e}")
            return {"status": "error", "message": str(e)}

    def get_recent_laws(self, days_back: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recently enacted laws and store them in the database."""
        try:
            current_year = datetime.now().year
            congress_number = ((current_year - 1789) // 2) + 1

            params = {
                "fromDateTime": (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sort": "updateDate desc",
                "limit": limit,
                "offset": 0,
            }

            response = self._make_request(f"law/{congress_number}", params)
            logger.info(f"Law API Response: {response}")
            laws_data: List[Dict[str, Any]] = []

            if isinstance(response, dict) and "bills" in response:
                bills = response["bills"]
                for bill in bills:
                    if "laws" in bill:
                        for law in bill["laws"]:
                            bill_content = self.get_bill_text_and_formats(
                                congress=bill.get("congress"),
                                bill_type=(bill.get("type") or "").upper(),
                                bill_number=bill.get("number", "")
                            )
                            formatted_law: Dict[str, Any] = {
                                "congress": bill.get("congress"),
                                "type": law.get("type", ""),
                                "number": law.get("number", ""),
                                "title": bill.get("title", ""),
                                "enacted_date": bill.get("latestAction", {}).get("actionDate", ""),
                                "bill_number": bill.get("number"),
                                "bill_type": (bill.get("type") or "").upper(),
                                "description": bill.get("latestAction", {}).get("text", ""),
                                "bill_text": bill_content.get("text"),
                                "document_formats": bill_content.get("formats"),
                                "raw_response": bill,
                            }

                            try:
                                current_time = datetime.now()
                                existing_law = (
                                    self.db_session.query(LegislationTracker)
                                    .filter(
                                        and_(
                                            LegislationTracker.congress == formatted_law["congress"],
                                            LegislationTracker.bill_type == formatted_law["bill_type"],
                                            LegislationTracker.bill_number == formatted_law["bill_number"],
                                        )
                                    )
                                    .first()
                                )
                                if existing_law is not None:
                                    existing_law.title = formatted_law["title"]
                                    existing_law.status = f"Enacted as {law.get('type', '')} {law.get('number', '')}"
                                    existing_law.raw_api_response = formatted_law["raw_response"]
                                    existing_law.bill_text = formatted_law["bill_text"]
                                    existing_law.document_formats = formatted_law["document_formats"]
                                    existing_law.last_updated = current_time
                                    # Add proper law fields
                                    existing_law.law_number = law.get("number")
                                    existing_law.law_type = law.get("type")
                                    existing_law.law_enacted_date = datetime.strptime(formatted_law["enacted_date"], "%Y-%m-%d") if formatted_law.get("enacted_date") else None
                                    existing_law.law_description = formatted_law["description"]
                                    logger.info(f"Updated existing law record for {formatted_law['bill_number']} with law number {law.get('number')}")
                                else:
                                    new_law = LegislationTracker(
                                        congress=formatted_law["congress"],
                                        bill_type=formatted_law["bill_type"],
                                        bill_number=formatted_law["bill_number"],
                                        title=formatted_law["title"],
                                        status=f"Enacted as {law.get('type', '')} {law.get('number', '')}",
                                        introduced_date=None,
                                        raw_api_response=formatted_law["raw_response"],
                                        bill_text=formatted_law["bill_text"],
                                        first_stored_date=current_time,
                                        last_updated=current_time,
                                        document_formats=formatted_law.get("document_formats"),
                                        law_number=law.get("number"),
                                        law_type=law.get("type"),
                                        law_enacted_date=datetime.strptime(formatted_law["enacted_date"], "%Y-%m-%d") if formatted_law.get("enacted_date") else None,
                                        law_description = formatted_law["description"]
                                    )
                                    self.db_session.add(new_law)
                                    logger.info(f"Created new law record for {formatted_law['bill_number']}")

                                self.db_session.commit()
                                laws_data.append(formatted_law)
                                logger.info(f"Successfully processed and stored law: {formatted_law['bill_number']}")
                            except Exception as db_error:
                                logger.error(f"Database error processing law {formatted_law.get('bill_number', 'unknown')}: {str(db_error)}")
                                self.db_session.rollback()

            return laws_data

        except Exception as e:
            logger.error(f"Error in get_recent_laws: {str(e)}")
            return []

    def _format_bill(self, bill: Dict[str, Any]) -> Dict[str, Any]:
        """Alternate helper to format bill data."""
        try:
            formatted_bill: Dict[str, Any] = {
                "congress": bill.get("congress"),
                "type": (bill.get("type") or "").lower(),
                "number": bill.get("number"),
                "title": bill.get("title", ""),
                "introduced_date": bill.get("introducedDate", ""),
                "last_action_date": "",
                "last_action_text": "",
                "sponsors": [],
                "summary": "",
            }
            latest_action = bill.get("latestAction", {})
            if latest_action:
                formatted_bill["last_action_date"] = latest_action.get("actionDate", "")
                formatted_bill["last_action_text"] = latest_action.get("text", "")
            sponsors = bill.get("sponsors", [])
            formatted_bill["sponsors"] = [
                sponsor.get("name", "")
                for sponsor in sponsors
                if isinstance(sponsor, dict) and sponsor.get("name")
            ]
            summaries = bill.get("summaries")
            if summaries and isinstance(summaries, list) and summaries:
                full_summary = summaries[0].get("text", "")
                if full_summary:
                    parts = full_summary.split("\n", 1)
                    formatted_bill["summary"] = (
                        parts[0][:300] + "..." if len(parts[0]) > 300 else parts[0]
                    )
            elif bill.get("summary"):
                formatted_bill["summary"] = bill.get("summary")
            logger.info(f"Formatted bill {formatted_bill.get('number')} with fields: {list(formatted_bill.keys())}")
            return formatted_bill
        except Exception as e:
            logger.error(f"Error formatting bill data: {str(e)}")
            return {}

    def get_law_details(self, congress: int, law_type: str, law_number: str) -> Dict[str, Any]:
        """Fetch details for a specific law."""
        try:
            formatted_law_type = law_type.lower().replace(" ", "")
            response = self._make_request(f"law/{congress}/{formatted_law_type}/{law_number}")
            resp_dict: Dict[str, Any] = response if isinstance(response, dict) else {}
            logger.info(f"Law details response: {resp_dict}")

            if "law" in resp_dict:
                law_data = resp_dict["law"]
                logger.info(f"Retrieved law details for {law_type} {law_number}")

                bill_number = law_data.get("billNumber")
                bill_type = law_data.get("billType")
                if bill_number and bill_type:
                    logger.info(f"Fetching text for associated bill {bill_type} {bill_number}")
                    bill_text = self.get_bill_text_and_formats(congress, bill_type, bill_number).get("text")
                    if bill_text:
                        law_data["bill_text"] = bill_text
                        logger.info(f"Retrieved bill text for law {law_number}")
                    else:
                        logger.warning(f"Could not retrieve bill text for law {law_number}")
                        bill_details = self._get_bill_details(congress, bill_type, bill_number)
                        if bill_details:
                            law_data["bill_details"] = bill_details
                            summaries = self._get_bill_summaries(congress, bill_type, bill_number)
                            if summaries:
                                law_data["bill_text"] = summaries[0].get("text", "")
                                logger.info(f"Using bill summary as fallback for law {law_number}")

                return law_data

            logger.warning(f"Unexpected law details format for {law_number}")
            return {}

        except Exception as e:
            logger.error(f"Error fetching law details: {e}")
            return {}

    def track_bill_to_law_progression(
        self, congress: int, bill_type: str, bill_number: str
    ) -> Dict[str, Any]:
        """Track a bill’s progression to becoming a law."""
        try:
            bill_details = self._get_bill_details(congress, bill_type, bill_number)
            if not bill_details:
                return {"status": "error", "message": "Bill not found"}

            latest_action = bill_details.get("latestAction", {})
            law_info = {}
            if bill_details.get("isPrivate") is not None:
                law_type = "private" if bill_details.get("isPrivate") else "public"
                law_number = bill_details.get("lawNumber")
                if law_number:
                    law_info = self.get_law_details(congress, law_type, law_number)

            progression_data: Dict[str, Any] = {
                "bill_info": bill_details,
                "became_law": bool(law_info),
                "law_info": law_info,
                "progression_history": [],
            }

            try:
                actions_response = self._make_request(f"bill/{congress}/{bill_type.lower()}/{bill_number}/actions")
                if isinstance(actions_response, dict) and "actions" in actions_response:
                    actions = actions_response["actions"]
                    progression_data["progression_history"] = [
                        {
                            "date": action.get("actionDate"),
                            "text": action.get("text"),
                            "type": action.get("type"),
                            "chamber": action.get("chamber"),
                        }
                        for action in actions
                    ]
            except Exception as e:
                logger.error(f"Error fetching bill actions: {e}")

            return progression_data

        except Exception as e:
            logger.error(f"Error tracking bill to law progression: {e}")
            return {"status": "error", "message": str(e)}

    def get_recent_laws(self, days_back: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recently enacted laws and store them in the database."""
        try:
            current_year = datetime.now().year
            congress_number = ((current_year - 1789) // 2) + 1

            params = {
                "fromDateTime": (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sort": "updateDate desc",
                "limit": limit,
                "offset": 0,
            }

            response = self._make_request(f"law/{congress_number}", params)
            logger.info(f"Law API Response: {response}")
            laws_data: List[Dict[str, Any]] = []

            if isinstance(response, dict) and "bills" in response:
                bills = response["bills"]
                for bill in bills:
                    if "laws" in bill:
                        for law in bill["laws"]:
                            bill_content = self.get_bill_text_and_formats(
                                congress=bill.get("congress"),
                                bill_type=(bill.get("type") or "").upper(),
                                bill_number=bill.get("number", "")
                            )
                            formatted_law: Dict[str, Any] = {
                                "congress": bill.get("congress"),
                                "type": law.get("type", ""),
                                "number": law.get("number", ""),
                                "title": bill.get("title", ""),
                                "enacted_date": bill.get("latestAction", {}).get("actionDate", ""),
                                "bill_number": bill.get("number"),
                                "bill_type": (bill.get("type") or "").upper(),
                                "description": bill.get("latestAction", {}).get("text", ""),
                                "bill_text": bill_content.get("text"),
                                "document_formats": bill_content.get("formats"),
                                "raw_response": bill,
                            }

                            try:
                                current_time = datetime.now()
                                existing_law = (
                                    self.db_session.query(LegislationTracker)
                                    .filter(
                                        and_(
                                            LegislationTracker.congress == formatted_law["congress"],
                                            LegislationTracker.bill_type == formatted_law["bill_type"],
                                            LegislationTracker.bill_number == formatted_law["bill_number"],
                                        )
                                    )
                                    .first()
                                )
                                if existing_law is not None:
                                    existing_law.title = formatted_law["title"]
                                    existing_law.status = f"Enacted as {law.get('type', '')} {law.get('number', '')}"
                                    existing_law.raw_api_response = formatted_law["raw_response"]
                                    existing_law.bill_text = formatted_law["bill_text"]
                                    existing_law.document_formats = formatted_law["document_formats"]
                                    existing_law.last_updated = current_time
                                    # Add proper law fields
                                    existing_law.law_number = law.get("number")
                                    existing_law.law_type = law.get("type")
                                    existing_law.law_enacted_date = datetime.strptime(formatted_law["enacted_date"], "%Y-%m-%d") if formatted_law.get("enacted_date") else None
                                    existing_law.law_description = formatted_law["description"]
                                    logger.info(f"Updated existing law record for {formatted_law['bill_number']} with law number {law.get('number')}")
                                else:
                                    new_law = LegislationTracker(
                                        congress=formatted_law["congress"],
                                        bill_type=formatted_law["bill_type"],
                                        bill_number=formatted_law["bill_number"],
                                        title=formatted_law["title"],
                                        status=f"Enacted as {law.get('type', '')} {law.get('number', '')}",
                                        introduced_date=None,
                                        raw_api_response=formatted_law["raw_response"],
                                        bill_text=formatted_law["bill_text"],
                                        first_stored_date=current_time,
                                        last_updated=current_time,
                                        document_formats=formatted_law.get("document_formats"),
                                        law_number=law.get("number"),
                                        law_type=law.get("type"),
                                        law_enacted_date=datetime.strptime(formatted_law["enacted_date"], "%Y-%m-%d") if formatted_law.get("enacted_date") else None,
                                        law_description = formatted_law["description"]
                                    )
                                    self.db_session.add(new_law)
                                    logger.info(f"Created new law record for {formatted_law['bill_number']}")

                                self.db_session.commit()
                                laws_data.append(formatted_law)
                                logger.info(f"Successfully processed and stored law: {formatted_law['bill_number']}")
                            except Exception as db_error:
                                logger.error(f"Database error processing law {formatted_law.get('bill_number', 'unknown')}: {str(db_error)}")
                                self.db_session.rollback()

            return laws_data

        except Exception as e:
            logger.error(f"Error in get_recent_laws: {str(e)}")
            return []

    def _format_bill(self, bill: Dict[str, Any]) -> Dict[str, Any]:
        """Alternate helper to format bill data."""
        try:
            formatted_bill: Dict[str, Any] = {
                "congress": bill.get("congress"),
                "type": (bill.get("type") or "").lower(),
                "number": bill.get("number"),
                "title": bill.get("title", ""),
                "introduced_date": bill.get("introducedDate", ""),
                "last_action_date": "",
                "last_action_text": "",
                "sponsors": [],
                "summary": "",
            }
            latest_action = bill.get("latestAction", {})
            if latest_action:
                formatted_bill["last_action_date"] = latest_action.get("actionDate", "")
                formatted_bill["last_action_text"] = latest_action.get("text", "")
            sponsors = bill.get("sponsors", [])
            formatted_bill["sponsors"] = [
                sponsor.get("name", "")
                for sponsor in sponsors
                if isinstance(sponsor, dict) and sponsor.get("name")
            ]
            summaries = bill.get("summaries")
            if summaries and isinstance(summaries, list) and summaries:
                full_summary = summaries[0].get("text", "")
                if full_summary:
                    parts = full_summary.split("\n", 1)
                    formatted_bill["summary"] = (
                        parts[0][:300] + "..." if len(parts[0]) > 300 else parts[0]
                    )
            elif bill.get("summary"):
                formatted_bill["summary"] = bill.get("summary")
            logger.info(f"Formatted bill {formatted_bill.get('number')} with fields: {list(formatted_bill.keys())}")
            return formatted_bill
        except Exception as e:
            logger.error(f"Error formatting bill data: {str(e)}")
            return {}

    def get_law_details(self, congress: int, law_type: str, law_number: str) -> Dict[str, Any]:
        """Fetch details for a specific law."""
        try:
            formatted_law_type = law_type.lower().replace(" ", "")
            response = self._make_request(f"law/{congress}/{formatted_law_type}/{law_number}")
            resp_dict: Dict[str, Any] = response if isinstance(response, dict) else {}
            logger.info(f"Law details response: {resp_dict}")

            if "law" in resp_dict:
                law_data = resp_dict["law"]
                logger.info(f"Retrieved law details for {law_type} {law_number}")

                bill_number = law_data.get("billNumber")
                bill_type = law_data.get("billType")
                if bill_number and bill_type:
                    logger.info(f"Fetching text for associated bill {bill_type} {bill_number}")
                    bill_text = self.get_bill_text_and_formats(congress, bill_type, bill_number).get("text")
                    if bill_text:
                        law_data["bill_text"] = bill_text
                        logger.info(f"Retrieved bill text for law {law_number}")
                    else:
                        logger.warning(f"Could not retrieve bill text for law {law_number}")
                        bill_details = self._get_bill_details(congress, bill_type, bill_number)
                        if bill_details:
                            law_data["bill_details"] = bill_details
                            summaries = self._get_bill_summaries(congress, bill_type, bill_number)
                            if summaries:
                                law_data["bill_text"] = summaries[0].get("text", "")
                                logger.info(f"Using bill summary as fallback for law {law_number}")

                return law_data

            logger.warning(f"Unexpected law details format for {law_number}")
            return {}

        except Exception as e:
            logger.error(f"Error fetching law details: {e}")
            return {}

    def track_bill_to_law_progression(
        self, congress: int, bill_type: str, bill_number: str
    ) -> Dict[str, Any]:
        """Track a bill’s progression to becoming a law."""
        try:
            bill_details = self._get_bill_details(congress, bill_type, bill_number)
            if not bill_details:
                return {"status": "error", "message": "Bill not found"}

            latest_action = bill_details.get("latestAction", {})
            law_info = {}
            if bill_details.get("isPrivate") is not None:
                law_type = "private" if bill_details.get("isPrivate") else "public"
                law_number = bill_details.get("lawNumber")
                if law_number:
                    law_info = self.get_law_details(congress, law_type, law_number)

            progression_data: Dict[str, Any] = {
                "bill_info": bill_details,
                "became_law": bool(law_info),
                "law_info": law_info,
                "progression_history": [],
            }

            try:
                actions_response = self._make_request(f"bill/{congress}/{bill_type.lower()}/{bill_number}/actions")
                if isinstance(actions_response, dict) and "actions" in actions_response:
                    actions = actions_response["actions"]
                    progression_data["progression_history"] = [
                        {
                            "date": action.get("actionDate"),
                            "text": action.get("text"),
                            "type": action.get("type"),
                            "chamber": action.get("chamber"),
                        }
                        for action in actions
                    ]
            except Exception as e:
                logger.error(f"Error fetching bill actions: {e}")

            return progression_data

        except Exception as e:
            logger.error(f"Error tracking bill to law progression: {e}")
            return {"status": "error", "message": str(e)}

    def get_recent_laws(self, days_back: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recently enacted laws and store them in the database."""
        try:
            current_year = datetime.now().year
            congress_number = ((current_year - 1789) // 2) + 1

            params = {
                "fromDateTime": (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sort": "updateDate desc",
                "limit": limit,
                "offset": 0,
            }

            response = self._make_request(f"law/{congress_number}", params)
            logger.info(f"Law API Response: {response}")
            laws_data: List[Dict[str, Any]] = []

            if isinstance(response, dict) and "bills" in response:
                bills = response["bills"]
                for bill in bills:
                    if "laws" in bill:
                        for law in bill["laws"]:
                            bill_content = self.get_bill_text_and_formats(
                                congress=bill.get("congress"),
                                bill_type=(bill.get("type") or "").upper(),
                                bill_number=bill.get("number", "")
                            )
                            formatted_law: Dict[str, Any] = {
                                "congress": bill.get("congress"),
                                "type": law.get("type", ""),
                                "number": law.get("number", ""),
                                "title": bill.get("title", ""),
                                "enacted_date": bill.get("latestAction", {}).get("actionDate", ""),
                                "bill_number": bill.get("number"),
                                "bill_type": (bill.get("type") or "").upper(),
                                "description": bill.get("latestAction", {}).get("text", ""),
                                "bill_text": bill_content.get("text"),
                                "document_formats": bill_content.get("formats"),
                                "raw_response": bill,
                            }

                            try:
                                current_time = datetime.now()
                                existing_law = (
                                    self.db_session.query(LegislationTracker)
                                    .filter(
                                        and_(
                                            LegislationTracker.congress == formatted_law["congress"],
                                            LegislationTracker.bill_type == formatted_law["bill_type"],
                                            LegislationTracker.bill_number == formatted_law["bill_number"],
                                        )
                                    )
                                    .first()
                                )
                                if existing_law is not None:
                                    existing_law.title = formatted_law["title"]
                                    existing_law.status = f"Enacted as {law.get('type', '')} {law.get('number', '')}"
                                    existing_law.raw_api_response = formatted_law["raw_response"]
                                    existing_law.bill_text = formatted_law["bill_text"]
                                    existing_law.document_formats = formatted_law["document_formats"]
                                    existing_law.last_updated = current_time
                                    # Add proper law fields
                                    existing_law.law_number = law.get("number")
                                    existing_law.law_type = law.get("type")
                                    existing_law.law_enacted_date = datetime.strptime(formatted_law["enacted_date"], "%Y-%m-%d") if formatted_law.get("enacted_date") else None
                                    existing_law.law_description = formatted_law["description"]
                                    logger.info(f"Updated existing law record for {formatted_law['bill_number']} with law number {law.get('number')}")
                                else:
                                    new_law = LegislationTracker(
                                        congress=formatted_law["congress"],
                                        bill_type=formatted_law["bill_type"],
                                        bill_number=formatted_law["bill_number"],
                                        title=formatted_law["title"],
                                        status=f"Enacted as {law.get('type', '')} {law.get('number', '')}",
                                        introduced_date=None,
                                        raw_api_response=formatted_law["raw_response"],
                                        bill_text=formatted_law["bill_text"],
                                        first_stored_date=current_time,
                                        last_updated=current_time,
                                        document_formats=formatted_law.get("document_formats"),
                                        law_number=law.get("number"),
                                        law_type=law.get("type"),
                                        law_enacted_date=datetime.strptime(formatted_law["enacted_date"], "%Y-%m-%d") if formatted_law.get("enacted_date") else None,
                                        law_description = formatted_law["description"]
                                    )
                                    self.db_session.add(new_law)
                                    logger.info(f"Created new law record for {formatted_law['bill_number']}")

                                self.db_session.commit()
                                laws_data.append(formatted_law)
                                logger.info(f"Successfully processed and stored law: {formatted_law['bill_number']}")
                            except Exception as db_error:
                                logger.error(f"Database error processing law {formatted_law.get('bill_number', 'unknown')}: {str(db_error)}")
                                self.db_session.rollback()

            return laws_data

        except Exception as e:
            logger.error(f"Error in get_recent_laws: {str(e)}")
            return []

    def _format_bill(self, bill: Dict[str, Any]) -> Dict[str, Any]:
        """Alternate helper to format bill data."""
        try:
            formatted_bill: Dict[str, Any] = {
                "congress": bill.get("congress"),
                "type": (bill.get("type") or "").lower(),
                "number": bill.get("number"),
                "title": bill.get("title", ""),
                "introduced_date": bill.get("introducedDate", ""),
                "last_action_date": "",
                "last_action_text": "",
                "sponsors": [],
                "summary": "",
            }
            latest_action = bill.get("latestAction", {})
            if latest_action:
                formatted_bill["last_action_date"] = latest_action.get("actionDate", "")
                formatted_bill["last_action_text"] = latest_action.get("text", "")
            sponsors = bill.get("sponsors", [])
            formatted_bill["sponsors"] = [
                sponsor.get("name", "")
                for sponsor in sponsors
                if isinstance(sponsor, dict) and sponsor.get("name")
            ]
            summaries = bill.get("summaries")
            if summaries and isinstance(summaries, list) and summaries:
                full_summary = summaries[0].get("text", "")
                if full_summary:
                    parts = full_summary.split("\n", 1)
                    formatted_bill["summary"] = (
                        parts[0][:300] + "..." if len(parts[0]) > 300 else parts[0]
                    )
            elif bill.get("summary"):
                formatted_bill["summary"] = bill.get("summary")
            logger.info(f"Formatted bill {formatted_bill.get('number')} with fields: {list(formatted_bill.keys())}")
            return formatted_bill
        except Exception as e:
            logger.error(f"Error formatting bill data: {str(e)}")
            return {}

    def get_law_details(self, congress: int, law_type: str, law_number: str) -> Dict[str, Any]:
        """Fetch details for a specific law."""
        try:
            formatted_law_type = law_type.lower().replace(" ", "")
            response = self._make_request(f"law/{congress}/{formatted_law_type}/{law_number}")
            resp_dict: Dict[str, Any] = response if isinstance(response, dict) else {}
            logger.info(f"Law details response: {resp_dict}")

            if "law" in resp_dict:
                law_data = resp_dict["law"]
                logger.info(f"Retrieved law details for {law_type} {law_number}")

                bill_number = law_data.get("billNumber")
                bill_type = law_data.get("billType")
                if bill_number and bill_type:
                    logger.info(f"Fetching text for associated bill {bill_type} {bill_number}")
                    bill_text = self.get_bill_text_and_formats(congress, bill_type, bill_number).get("text")
                    if bill_text:
                        law_data["bill_text"] = bill_text
                        logger.info(f"Retrieved bill text for law {law_number}")
                    else:
                        logger.warning(f"Could not retrieve bill text for law {law_number}")
                        bill_details = self._get_bill_details(congress, bill_type, bill_number)
                        if bill_details:
                            law_data["bill_details"] = bill_details
                            summaries = self._get_bill_summaries(congress, bill_type, bill_number)
                            if summaries:
                                law_data["bill_text"] = summaries[0].get("text", "")
                                logger.info(f"Using bill summary as fallback for law {law_number}")

                return law_data

            logger.warning(f"Unexpected law details format for {law_number}")
            return {}

        except Exception as e:
            logger.error(f"Error fetching law details: {e}")
            return {}

    def track_bill_to_law_progression(
        self, congress: int, bill_type: str, bill_number: str
    ) -> Dict[str, Any]:
        """Track a bill’s progression to becoming a law."""
        try:
            bill_details = self._get_bill_details(congress, bill_type, bill_number)
            if not bill_details:
                return {"status": "error", "message": "Bill not found"}

            latest_action = bill_details.get("latestAction", {})
            law_info = {}
            if bill_details.get("isPrivate") is not None:
                law_type = "private" if bill_details.get("isPrivate") else "public"
                law_number = bill_details.get("lawNumber")
                if law_number:
                    law_info = self.get_law_details(congress, law_type, law_number)

            progression_data: Dict[str, Any] = {
                "bill_info": bill_details,
                "became_law": bool(law_info),
                "law_info": law_info,
                "progression_history": [],
            }

            try:
                actions_response = self._make_request(f"bill/{congress}/{bill_type.lower()}/{bill_number}/actions")
                if isinstance(actions_response, dict) and "actions" in actions_response:
                    actions = actions_response["actions"]
                    progression_data["progression_history"] = [
                        {
                            "date": action.get("actionDate"),
                            "text": action.get("text"),
                            "type": action.get("type"),
                            "chamber": action.get("chamber"),
                        }
                        for action in actions
                    ]
            except Exception as e:
                logger.error(f"Error fetching bill actions: {e}")

            return progression_data

        except Exception as e:
            logger.error(f"Error tracking bill to law progression: {e}")
            return {"status": "error", "message": str(e)}

    def get_recent_laws(self, days_back: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recently enacted laws and store them in the database."""
        try:
            current_year = datetime.now().year
            congress_number = ((current_year - 1789) // 2) + 1

            params = {
                "fromDateTime": (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sort": "updateDate desc",
                "limit": limit,
                "offset": 0,
            }

            response = self._make_request(f"law/{congress_number}", params)
            logger.info(f"Law API Response: {response}")
            laws_data: List[Dict[str, Any]] = []

            if isinstance(response, dict) and "bills" in response:
                bills = response["bills"]
                for bill in bills:
                    if "laws" in bill:
                        for law in bill["laws"]:
                            bill_content = self.get_bill_text_and_formats(
                                congress=bill.get("congress"),
                                bill_type=(bill.get("type") or "").upper(),
                                bill_number=bill.get("number", "")
                            )
                            formatted_law: Dict[str, Any] = {
                                "congress": bill.get("congress"),
                                "type": law.get("type", ""),
                                "number": law.get("number", ""),
                                "title": bill.get("title", ""),
                                "enacted_date": bill.get("latestAction", {}).get("actionDate", ""),
                                "bill_number": bill.get("number"),
                                "bill_type": (bill.get("type") or "").upper(),
                                "description": bill.get("latestAction", {}).get("text", ""),
                                "bill_text": bill_content.get("text"),
                                "document_formats": bill_content.get("formats"),
                                "raw_response": bill,
                            }

                            try:
                                current_time = datetime.now()
                                existing_law = (
                                    self.db_session.query(LegislationTracker)
                                    .filter(
                                        and_(
                                            LegislationTracker.congress == formatted_law["congress"],
                                            LegislationTracker.bill_type == formatted_law["bill_type"],
                                            LegislationTracker.bill_number == formatted_law["bill_number"],
                                        )
                                    )
                                    .first()
                                )
                                if existing_law is not None:
                                    existing_law.title = formatted_law["title"]
                                    existing_law.status = f"Enacted as {law.get('type', '')} {law.get('number', '')}"
                                    existing_law.raw_api_response = formatted_law["raw_response"]
                                    existing_law.bill_text = formatted_law["bill_text"]
                                    existing_law.document_formats = formatted_law["document_formats"]
                                    existing_law.last_updated = current_time
                                    # Add proper law fields
                                    existing_law.law_number = law.get("number")
                                    existing_law.law_type = law.get("type")
                                    existing_law.law_enacted_date = datetime.strptime(formatted_law["enacted_date"], "%Y-%m-%d") if formatted_law.get("enacted_date") else None
                                    existing_law.law_description = formatted_law["description"]
                                    logger.info(f"Updated existing law record for {formatted_law['bill_number']} with law number {law.get('number')}")
                                else:
                                    new_law = LegislationTracker(
                                        congress=formatted_law["congress"],
                                        bill_type=formatted_law["bill_type"],
                                        bill_number=formatted_law["bill_number"],
                                        title=formatted_law["title"],
                                        status=f"Enacted as {law.get('type', '')} {law.get('number', '')}",
                                        introduced_date=None,
                                        raw_api_response=formatted_law["raw_response"],
                                        bill_text=formattedlaw["bill_text"],
                                        first_stored_date=current_time,
                                        last_updated=current_time,
                                        document_formats=formatted_law.get("document_formats"),
                                        law_number=law.get("number"),
                                        law_type=law.get("type"),
                                        law_enacted_date=datetime.strptime(formatted_law["enacted_date"], "%Y-%m-%d") if formatted_law.get("enacted_date") else None,
                                        law_description = formatted_law["description"]
                                    )
                                    self.db_session.add(new_law)
                                    logger.info(f"Created new law record for {formatted_law['bill_number']}")

                                self.db_session.commit()
                                laws_data.append(formatted_law)
                                logger.info(f"Successfully processed and stored law: {formatted_law['bill_number']}")
                            except Exception as db_error:
                                logger.error(f"Database error processing law {formatted_law.get('bill_number', 'unknown')}: {str(db_error)}")
                                self.db_session.rollback()

            return laws_data

        except Exception as e:
            logger.error(f"Error in get_recent_laws: {str(e)}")
            return []

    def _format_bill(self, bill: Dict[str, Any]) -> Dict[str, Any]:
        """Alternate helper to format bill data."""
        try:
            formatted_bill: Dict[str, Any] = {
                "congress": bill.get("congress"),
                "type": (bill.get("type") or "").lower(),
                "number": bill.get("number"),
                "title": bill.get("title", ""),
                "introduced_date": bill.get("introducedDate", ""),
                "last_action_date": "",
                "last_action_text": "",
                "sponsors": [],
                "summary": "",
            }
            latest_action = bill.get("latestAction", {})
            if latest_action:
                formatted_bill["last_action_date"] = latest_action.get("actionDate", "")
                formatted_bill["last_action_text"] = latest_action.get("text", "")
            sponsors = bill.get("sponsors", [])
            formatted_bill["sponsors"] = [
                sponsor.get("name", "")
                for sponsor in sponsors
                if isinstance(sponsor, dict) and sponsor.get("name")
            ]
            summaries = bill.get("summaries")
            if summaries and isinstance(summaries, list) and summaries:
                full_summary = summaries[0].get("text", "")
                if full_summary:
                    parts = full_summary.split("\n", 1)
                    formatted_bill["summary"] = (
                        parts[0][:300] + "..." if len(parts[0]) > 300 else parts[0]
                    )
            elif bill.get("summary"):
                formatted_bill["summary"] = bill.get("summary")
            logger.info(f"Formatted bill {formatted_bill.get('number')} with fields: {list(formatted_bill.keys())}")
            return formatted_bill
        except Exception as e:
            logger.error(f"Error formatting bill data: {str(e)}")
            return {}

    def get_law_details(self, congress: int, law_type: str, law_number: str) -> Dict[str, Any]:
        """Fetch details for a specific law."""
        try:
            formatted_law_type = law_type.lower().replace(" ", "")
            response = self._make_request(f"law/{congress}/{formatted_law_type}/{law_number}")
            resp_dict: Dict[str, Any] = response if isinstance(response, dict) else {}
            logger.info(f"Law details response: {resp_dict}")

            if "law" in resp_dict:
                law_data = resp_dict["law"]
                logger.info(f"Retrieved law details for {law_type} {law_number}")

                bill_number = law_data.get("billNumber")
                bill_type = law_data.get("billType")
                if bill_number and bill_type:
                    logger.info(f"Fetching text for associated bill {bill_type} {bill_number}")
                    bill_text = self.get_bill_text_and_formats(congress, bill_type, bill_number).get("text")
                    if bill_text:
                        law_data["bill_text"] = bill_text
                        logger.info(f"Retrieved bill text for law {law_number}")
                    else:
                        logger.warning(f"Could not retrieve bill text for law {law_number}")
                        bill_details = self._get_bill_details(congress, bill_type, bill_number)
                        if bill_details:
                            law_data["bill_details"] = bill_details
                            summaries = self._get_bill_summaries(congress, bill_type, bill_number)
                            if summaries:
                                law_data["bill_text"] = summaries[0].get("text", "")
                                logger.info(f"Using bill summary as fallback for law {law_number}")

                return law_data

            logger.warning(f"Unexpected law details format for {law_number}")
            return {}

        except Exception as e:
            logger.error(f"Error fetching law details: {e}")
            return {}

    def track_bill_to_law_progression(
        self, congress: int, bill_type: str, bill_number: str
    ) -> Dict[str, Any]:
        """Track a bill’s progression to becoming a law."""
        try:
            bill_details = self._get_bill_details(congress, bill_type, bill_number)
            if not bill_details:
                return {"status": "error", "message": "Bill not found"}

            latest_action = bill_details.get("latestAction", {})
            law_info = {}
            if bill_details.get("isPrivate") is not None:
                law_type = "private" if bill_details.get("isPrivate") else "public"
                law_number = bill_details.get("lawNumber")
                if law_number:
                    law_info = self.get_law_details(congress, law_type, law_number)

            progression_data: Dict[str, Any] = {
                "bill_info": bill_details,
                "became_law": bool(law_info),
                "law_info": law_info,
                "progression_history": [],
            }

            try:
                actions_response = self._make_request(f"bill/{congress}/{bill_type.lower()}/{bill_number}/actions")
                if isinstance(actions_response, dict) and "actions" in actions_response:
                    actions = actions_response["actions"]
                    progression_data["progression_history"] = [
                        {
                            "date": action.get("actionDate"),
                            "text": action.get("text"),
                            "type": action.get("type"),
                            "chamber": action.get("chamber"),
                        }
                        for action in actions
                    ]
            except Exception as e:
                logger.error(f"Error fetching bill actions: {e}")

            return progression_data

        except Exception as e:
            logger.error(f"Error tracking bill to law progression: {e}")
            return {"status": "error", "message": str(e)}

    def get_recent_laws(self, days_back: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recently enacted laws and store them in the database."""
        try:
            current_year = datetime.now().year
            congress_number = ((current_year - 1789) // 2) + 1

            params = {
                "fromDateTime": (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sort": "updateDate desc",
                "limit": limit,
                "offset": 0,
            }

            response = self._make_request(f"law/{congress_number}", params)
            logger.info(f"Law API Response: {response}")
            laws_data: List[Dict[str, Any]] = []

            if isinstance(response, dict) and "bills" in response:
                bills = response["bills"]
                for bill in bills:
                    if "laws" in bill:
                        for law in bill["laws"]:
                            bill_content = self.get_bill_text_and_formats(
                                congress=bill.get("congress"),
                                bill_type=(bill.get("type") or "").upper(),
                                bill_number=bill.get("number", "")
                            )
                            formatted_law: Dict[str, Any] = {
                                "congress": bill.get("congress"),
                                "type": law.get("type", ""),
                                "number": law.get("number", ""),
                                "title": bill.get("title", ""),
                                "enacted_date": bill.get("latestAction", {}).get("actionDate", ""),
                                "bill_number": bill.get("number"),
                                "bill_type": (bill.get("type") or "").upper(),
                                "description": bill.get("latestAction", {}).get("text", ""),
                                "bill_text": bill_content.get("text"),
                                "document_formats": bill_content.get("formats"),
                                "raw_response": bill,
                            }

                            try:
                                current_time = datetime.now()
                                existing_law = (
                                    self.db_session.query(LegislationTracker)
                                    .filter(
                                        and_(
                                            LegislationTracker.congress == formatted_law["congress"],
                                            LegislationTracker.bill_type == formatted_law["bill_type"],
                                            LegislationTracker.bill_number == formatted_law["bill_number"],
                                        )
                                    )
                                    .first()
                                )
                                if existing_law is not None:
                                    existing_law.title = formatted_law["title"]
                                    existing_law.status = f"Enacted as {law.get('type', '')} {law.get('number', '')}"
                                    existing_law.raw_api_response = formatted_law["raw_response"]
                                    existing_law.bill_text = formatted_law["bill_text"]
                                    existing_law.document_formats = formatted_law["document_formats"]
                                    existing_law.last_updated = current_time
                                    # Add proper law fields
                                    existing_law.law_number = law.get("number")
                                    existing_law.law_type = law.get("type")
                                    existing_law.law_enacted_date = datetime.strptime(formatted_law["enacted_date"], "%Y-%m-%d") if formatted_law.get("enacted_date") else None
                                    existing_law.law_description = formatted_law["description"]
                                    logger.info(f"Updated existing law record for {formatted_law['bill_number']} with law number {law.get('number')}")
                                else:
                                    new_law = LegislationTracker(
                                        congress=formatted_law["congress"],
                                        bill_type=formatted_law["bill_type"],
                                        bill_number=formatted_law["bill_number"],
                                        title=formatted_law["title"],
                                        status=f"Enacted as {law.get('type', '')} {law.get('number', '')}",
                                        introduced_date=None,
                                        raw_api_response=formatted_law["raw_response"],
                                        bill_text=formatted_law["bill_text"],
                                        first_stored_date=current_time,
                                        last_updated=current_time,
                                        document_formats=formatted_law.get("document_formats"),
                                        law_number=law.get("number"),
                                        law_type=law.get("type"),
                                        law_enacted_date=datetime.strptime(formatted_law["enacted_date"], "%Y-%m-%d") if formatted_law.get("enacted_date") else None,
                                        law_description = formatted_law["description"]
                                    )
                                    self.db_session.add(new_law)
                                    logger.info(f"Created new law record for {formatted_law['bill_number']}")

                                self.db_session.commit()
                                laws_data.append(formatted_law)
                                logger.info(f"Successfully processed and stored law: {formatted_law['bill_number']}")
                            except Exception as db_error:
                                logger.error(f"Database error processing law {formatted_law.get('bill_number', 'unknown')}: {str(db_error)}")
                                self.db_session.rollback()

            return laws_data

        except Exception as e:
            logger.error(f"Error in get_recent_laws: {str(e)}")
            return []

    def _format_bill(self, bill: Dict[str, Any]) -> Dict[str, Any]:
        """Alternate helper to format bill data."""
        try:
            formatted_bill: Dict[str, Any] = {
                "congress": bill.get("congress"),
                "type": (bill.get("type") or "").lower(),
                "number": bill.get("number"),
                "title": bill.get("title", ""),
                "introduced_date": bill.get("introducedDate", ""),
                "last_action_date": "",
                "last_action_text": "",
                "sponsors": [],
                "summary": "",
            }
            latest_action = bill.get("latestAction", {})
            if latest_action:
                formatted_bill["last_action_date"] = latest_action.get("actionDate", "")
                formatted_bill["last_action_text"] = latest_action.get("text", "")
            sponsors = bill.get("sponsors", [])
            formatted_bill["sponsors"] = [
                sponsor.get("name", "")
                for sponsor in sponsors
                if isinstance(sponsor, dict) and sponsor.get("name")
            ]
            summaries = bill.get("summaries")
            if summaries and isinstance(summaries, list) and summaries:
                full_summary = summaries[0].get("text", "")
                if full_summary:
                    parts = full_summary.split("\n", 1)
                    formatted_bill["summary"] = (
                        parts[0][:300] + "..." if len(parts[0]) > 300 else parts[0]
                    )
            elif bill.get("summary"):
                formatted_bill["summary"] = bill.get("summary")
            logger.info(f"Formatted bill {formatted_bill.get('number')} with fields: {list(formatted_bill.keys())}")
            return formatted_bill
        except Exception as e:
            logger.error(f"Error formatting bill data: {str(e)}")
            return {}

    def get_law_details(self, congress: int, law_type: str, law_number: str) -> Dict[str, Any]:
        """Fetch details for a specific law."""
        try:
            formatted_law_type = law_type.lower().replace(" ", "")
            response = self._make_request(f"law/{congress}/{formatted_law_type}/{law_number}")
            resp_dict: Dict[str, Any] = response if isinstance(response, dict) else {}
            logger.info(f"Law details response: {resp_dict}")

            if "law" in resp_dict:
                law_data = resp_dict["law"]
                logger.info(f"Retrieved law details for {law_type} {law_number}")

                bill_number = law_data.get("billNumber")
                bill_type = law_data.get("billType")
                if bill_number and bill_type:
                    logger.info(f"Fetching text for associated bill {bill_type} {bill_number}")
                    bill_text = self.get_bill_text_and_formats(congress, bill_type, bill_number).get("text")
                    if bill_text:
                        law_data["bill_text"] = bill_text
                        logger.info(f"Retrieved bill text for law {law_number}")
                    else:
                        logger.warning(f"Could not retrieve bill text for law {law_number}")
                        bill_details = self._get_bill_details(congress, bill_type, bill_number)
                        if bill_details:
                            law_data["bill_details"] = bill_details
                            summaries = self._get_bill_summaries(congress, bill_type, bill_number)
                            if summaries:
                                law_data["bill_text"] = summaries[0].get("text", "")
                                logger.info(f"Using bill summary as fallback for law {law_number}")

                return law_data

            logger.warning(f"Unexpected law details format for {law_number}")
            return {}

        except Exception as e:
            logger.error(f"Error fetching law details: {e}")
            return {}

    def track_bill_to_law_progression(
        self, congress: int, bill_type: str, bill_number: str
    ) -> Dict[str, Any]:
        """Track a bill’s progression to becoming a law."""
        try:
            bill_details = self._get_bill_details(congress, bill_type, bill_number)
            if not bill_details:
                return {"status": "error", "message": "Bill not found"}

            latest_action = bill_details.get("latestAction", {})
            law_info = {}
            if bill_details.get("isPrivate") is not None:
                law_type = "private" if bill_details.get("isPrivate") else "public"
                law_number = bill_details.get("lawNumber")
                if law_number:
                    law_info = self.get_law_details(congress, law_type, law_number)

            progression_data: Dict[str, Any] = {
                "bill_info": bill_details,
                "became_law": bool(law_info),
                "law_info": law_info,
                "progression_history": [],
            }

            try:
                actions_response = self._make_request(f"bill/{congress}/{bill_type.lower()}/{bill_number}/actions")
                if isinstance(actions_response, dict) and "actions" in actions_response:
                    actions = actions_response["actions"]
                    progression_data["progression_history"] = [
                        {
                            "date": action.get("actionDate"),
                            "text": action.get("text"),
                            "type": action.get("type"),
                            "chamber": action.get("chamber"),
                        }
                        for action in actions
                    ]
            except Exception as e:
                logger.error(f"Error fetching bill actions: {e}")

            return progression_data

        except Exception as e:
            logger.error(f"Error tracking bill to law progression: {e}")
            return {"status": "error", "message": str(e)}