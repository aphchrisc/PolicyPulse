#!/usr/bin/env python
"""
validate_env.py

Script to validate that all required environment variables are set
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_environment():
    """Validate that all required environment variables are set."""
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API key for AI analysis features",
        "LEGISCAN_API_KEY": "LegiScan API key for legislation data"
    }
    
    # Database variables are also required but have defaults in set_env.sh
    db_vars = {
        "DB_HOST": "Database host",
        "DB_PORT": "Database port",
        "DB_USER": "Database user",
        "DB_PASSWORD": "Database password",
        "DB_NAME": "Database name"
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.environ.get(var):
            missing_vars.append(f"{var} ({description})")
    
    # Check database variables but just warn about them
    missing_db_vars = []
    for var, description in db_vars.items():
        if not os.environ.get(var):
            missing_db_vars.append(f"{var} ({description})")
    
    if missing_vars:
        logger.error("The following required environment variables are not set:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        logger.info("\nPlease set these variables in your .env file or environment.")
        logger.info("You can copy .env.template to .env and fill in your API keys.")
        return False
    
    if missing_db_vars:
        logger.warning("The following database environment variables are not set:")
        for var in missing_db_vars:
            logger.warning(f"  - {var}")
        logger.info("These variables have defaults in set_env.sh, but you may want to set them explicitly.")
    
    logger.info("✅ All required environment variables are set")
    return True

if __name__ == "__main__":
    logger.info("Validating environment variables...")
    if not validate_environment():
        sys.exit(1)
    sys.exit(0)