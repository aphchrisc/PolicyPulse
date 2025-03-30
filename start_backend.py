#!/usr/bin/env python
"""
start_backend.py

Script to start the backend server with proper environment variable loading.
"""

import os
import sys
import subprocess
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def start_backend():
    """Start the backend server with proper environment variable loading."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Check for required environment variables
    required_vars = [
        'DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME',
        'OPENAI_API_KEY', 'LEGISCAN_API_KEY'
    ]
    
    # Check if each variable is set
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            # Mask API keys for security
            if 'API_KEY' in var:
                masked_value = value[:5] + '...' + value[-5:]
                logger.info(f"{var}: {masked_value}")
            else:
                logger.info(f"{var}: {value}")
        else:
            missing_vars.append(var)
            logger.error(f"{var} is not set!")
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your .env file and try again.")
        sys.exit(1)
    
    # Start the backend server
    logger.info("Starting backend server...")
    cmd = ["python", "-m", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    
    # Pass the environment variables to the subprocess
    env = os.environ.copy()
    
    # Start the server
    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        logger.info("Backend server stopped.")
    except Exception as e:
        logger.error(f"Error starting backend server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    start_backend()
