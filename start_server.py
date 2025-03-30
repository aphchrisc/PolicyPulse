import os
import sys
import uvicorn
import logging
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

def check_api_keys():
    # Check if required API keys are present
    legiscan_key = os.getenv("LEGISCAN_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    print(f"LEGISCAN_API_KEY loaded: {'Yes' if legiscan_key else 'No'}")
    print(f"OPENAI_API_KEY loaded: {'Yes' if openai_key else 'No'}")
    
    return legiscan_key is not None and openai_key is not None

def start_server(port=8000, reload=False, debug=False):
    """Start the FastAPI server with the specified configuration."""
    # Check API keys before starting
    check_api_keys()
    
    print(f"Starting server on port {port} (IPv4 only)...")
    
    # Configure log level based on debug flag
    log_level = "debug" if debug else "info"
    
    # Configure server with improved settings for chunked responses
    # Use 127.0.0.1 instead of 0.0.0.0 to force IPv4 only
    uvicorn.run(
        "app.api.app:app",
        host="127.0.0.1",
        port=port,
        reload=reload,
        log_level=log_level,
        timeout_keep_alive=30,  # Reduce keep-alive timeout
        limit_concurrency=20,   # Limit concurrent connections
        timeout_graceful_shutdown=10,
        http="h11",
        loop="asyncio",
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the API server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    start_server(port=args.port, reload=args.reload, debug=args.debug)
