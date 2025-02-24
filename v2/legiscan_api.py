"""
legiscan_api.py

Contains the LegiScanAPI class which fetches data from the LegiScan API
and stores/updates it in the local database.
"""

import os
import time
import logging
import requests
import base64
from datetime import datetime, timezone
from typing import Optional, List, Dict

from sqlalchemy.orm import Session
from sqlalchemy import and_

from models import (
    Legislation,
    LegislationText,
    LegislationSponsor,
    DataSourceEnum,
    GovtTypeEnum,
    BillStatusEnum,
)


logger = logging.getLogger(__name__)


# Optional helper for approximate token count (if needed).
# For a large 128k context model, you typically won't chunk
# unless the text is truly huge (over ~100k tokens).
def approximate_token_count(text: str) -> int:
    # A very rough approximation: each 4-5 English words ~ 15-20 characters
    # might be ~ 14 tokens. Or you can integrate an actual tiktoken library.
    return len(text) // 4


class LegiScanAPI:
    def __init__(self, db_session: Session):
        self.api_key = os.environ.get("LEGISCAN_API_KEY")
        if not self.api_key:
            raise ValueError("LEGISCAN_API_KEY not set")
        self.base_url = "https://api.legiscan.com/"
        self.db_session = db_session

        self.last_request = datetime.now(timezone.utc)
        self.rate_limit_delay = 1.0  # in seconds

        # Example: monitoring just US & TX
        self.monitored_jurisdictions = ["US", "TX"]

    def _throttle_request(self):
        elapsed = (datetime.now(timezone.utc) - self.last_request).total_seconds()
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)

    def _make_request(self, operation: str, params: Optional[dict] = None) -> dict:
        self._throttle_request()

        if params is None:
            params = {}
        params["key"] = self.api_key
        params["op"] = operation

        try:
            resp = requests.get(self.base_url, params=params)
            self.last_request = datetime.now(timezone.utc)
            resp.raise_for_status()

            data = resp.json()
            if data.get("status") != "OK":
                err_msg = data.get("alert", {}).get("message", "Unknown error from LegiScan")
                raise ValueError(f"LegiScan API returned error: {err_msg}")

            return data
        except Exception as e:
            logger.error(f"API request error: {e}")
            raise

    # ------------------------------------------------------------------------
    # Common calls to LegiScan
    # ------------------------------------------------------------------------
    def get_session_list(self, state: str) -> List[dict]:
        try:
            data = self._make_request("getSessionList", {"state": state})
            return data.get("sessions", [])
        except Exception as e:
            logger.error(f"get_session_list({state}) failed: {e}")
            return []

    def get_master_list(self, session_id: int) -> dict:
        try:
            data = self._make_request("getMasterList", {"id": session_id})
            return data.get("masterlist", {})
        except Exception as e:
            logger.error(f"get_master_list({session_id}) failed: {e}")
            return {}

    def get_bill(self, bill_id: int) -> Optional[dict]:
        try:
            data = self._make_request("getBill", {"id": bill_id})
            return data.get("bill")
        except Exception as e:
            logger.error(f"get_bill({bill_id}) failed: {e}")
            return None

    def get_bill_text(self, doc_id: int) -> Optional[str]:
        try:
            data = self._make_request("getBillText", {"id": doc_id})
            text_obj = data.get("text", {})
            encoded = text_obj.get("doc")
            if encoded:
                # LegiScan can return PDF or Word doc in base64.
                # If it's textual data, decode to string. For PDF, you might store raw bytes.
                return base64.b64decode(encoded).decode("utf-8", errors="ignore")
            return None
        except Exception as e:
            logger.error(f"get_bill_text({doc_id}) failed: {e}")
            return None

    # ------------------------------------------------------------------------
    # DB Save/Update
    # ------------------------------------------------------------------------
    def save_bill_to_db(self, bill_data: dict) -> Optional[Legislation]:
        """
        Upsert logic for a given bill from LegiScan.
        """
        try:
            # Check if we are monitoring this state
            if bill_data.get("state") not in self.monitored_jurisdictions:
                return None

            # Convert LegiScan's "state" to GovtTypeEnum
            govt_type = GovtTypeEnum.FEDERAL if bill_data["state"] == "US" else GovtTypeEnum.STATE
            external_id = str(bill_data["bill_id"])

            existing = self.db_session.query(Legislation).filter(
                and_(
                    Legislation.data_source == DataSourceEnum.LEGISCAN,
                    Legislation.external_id == external_id
                )
            ).first()

            # Map the status numeric ID to your BillStatusEnum
            new_status = self._map_bill_status(bill_data.get("status"))

            # Build the upsert attributes
            attrs = {
                "external_id": external_id,
                "data_source": DataSourceEnum.LEGISCAN,
                "govt_type": govt_type,
                "govt_source": bill_data.get("session", {}).get("session_name", "Unknown Session"),
                "bill_number": bill_data.get("bill_number", ""),
                "bill_type": bill_data.get("bill_type"),
                "title": bill_data.get("title", ""),
                "description": bill_data.get("description", ""),
                "bill_status": new_status,
                "url": bill_data.get("url"),
                "state_link": bill_data.get("state_link"),
                "change_hash": bill_data.get("change_hash"),
                "raw_api_response": bill_data,
            }
            # Convert date strings if available
            introduced_str = bill_data.get("introduced_date", "")
            if introduced_str:
                attrs["bill_introduced_date"] = datetime.strptime(introduced_str, "%Y-%m-%d")
            status_str = bill_data.get("status_date", "")
            if status_str:
                attrs["bill_status_date"] = datetime.strptime(status_str, "%Y-%m-%d")
            last_action_str = bill_data.get("last_action_date", "")
            if last_action_str:
                attrs["bill_last_action_date"] = datetime.strptime(last_action_str, "%Y-%m-%d")

            if existing:
                for k, v in attrs.items():
                    setattr(existing, k, v)
                bill_obj = existing
            else:
                bill_obj = Legislation(**attrs)
                self.db_session.add(bill_obj)

            self.db_session.flush()  # to get bill_obj.id

            # Sponsors
            self._save_sponsors(bill_obj, bill_data.get("sponsors", []))

            # Bill text if present (LegiScan sometimes includes a `texts` array)
            self._save_legislation_texts(bill_obj, bill_data.get("texts", []))

            self.db_session.commit()
            return bill_obj

        except Exception as e:
            logger.error(f"save_bill_to_db error: {e}")
            self.db_session.rollback()
            return None

    def _save_sponsors(self, bill: Legislation, sponsors: List[dict]):
        # Clear old sponsors
        self.db_session.query(LegislationSponsor).filter(
            LegislationSponsor.legislation_id == bill.id
        ).delete()

        for sp in sponsors:
            sponsor_obj = LegislationSponsor(
                legislation_id=bill.id,
                sponsor_external_id=str(sp.get("people_id", "")),
                sponsor_name=sp.get("name", ""),
                sponsor_title=sp.get("role", ""),
                sponsor_state=sp.get("district", ""),
                sponsor_party=sp.get("party", ""),
                sponsor_type=str(sp.get("sponsor_type", "")),
            )
            self.db_session.add(sponsor_obj)
        self.db_session.flush()

    def _save_legislation_texts(self, bill: Legislation, texts: List[dict]):
        """
        Save text references from the API. 
        If doc is returned, decode it and store in `text_content`.
        """
        for text_info in texts:
            version_num = text_info.get("version", 1)
            existing = self.db_session.query(LegislationText).filter_by(
                legislation_id=bill.id,
                version_num=version_num
            ).first()

            text_date_str = text_info.get("date", "")
            text_date = datetime.utcnow()
            if text_date_str:
                try:
                    text_date = datetime.strptime(text_date_str, "%Y-%m-%d")
                except:
                    pass

            # Attempt to decode doc
            doc_base64 = text_info.get("doc")
            content = None
            if doc_base64:
                try:
                    content = base64.b64decode(doc_base64).decode("utf-8", errors="ignore")
                except:
                    content = None

            attrs = {
                "legislation_id": bill.id,
                "version_num": version_num,
                "text_type": text_info.get("type", ""),
                "text_content": content,
                "text_hash": text_info.get("text_hash"),
                "text_date": text_date,
            }

            if existing:
                for k, v in attrs.items():
                    setattr(existing, k, v)
            else:
                new_text = LegislationText(**attrs)
                self.db_session.add(new_text)

        self.db_session.flush()

    def _map_bill_status(self, status_val) -> BillStatusEnum:
        """
        Example LegiScan numeric -> BillStatusEnum
        1 => introduced, 2,3 => updated, 4 => passed, 5 => vetoed, etc.
        """
        if not status_val:
            return BillStatusEnum.NEW

        mapping = {
            "1": BillStatusEnum.INTRODUCED,
            "2": BillStatusEnum.UPDATED,
            "3": BillStatusEnum.UPDATED,
            "4": BillStatusEnum.PASSED,
            "5": BillStatusEnum.VETOED
        }
        return mapping.get(str(status_val), BillStatusEnum.UPDATED)
