import os
from congress_api import CongressAPI
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api():
    """Test Congress.gov API connectivity and data retrieval"""
    try:
        api = CongressAPI()

        # Test recent legislation
        logger.info("Testing recent legislation retrieval...")
        bills = api.get_recent_legislation(days_back=1)

        if bills:
            logger.info(f"Successfully retrieved {len(bills)} bills")
            # Print first bill details for verification
            if len(bills) > 0:
                logger.info("Sample bill details:")
                logger.info(json.dumps(bills[0], indent=2))
            return True
        else:
            logger.warning("No bills retrieved")
            logger.info("Current congress number: %d", ((datetime.now().year - 1789) // 2) + 1)
            return False

    except Exception as e:
        logger.error(f"API test failed: {e}")
        return False

if __name__ == "__main__":
    test_api()