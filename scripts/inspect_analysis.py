# scripts/inspect_analysis.py
import os
import json
import requests # Use requests library to make HTTP calls
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
BILL_ID_TO_INSPECT = 36# Bill ID from the user's example
# Assuming the backend runs locally on port 8000 by default
BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_ENDPOINT = f"{BACKEND_BASE_URL}/api/legislation/{BILL_ID_TO_INSPECT}/"
# --- End Configuration ---

print(f"Attempting to fetch API response for Bill ID: {BILL_ID_TO_INSPECT}")
print(f"API Endpoint: {API_ENDPOINT}")

try:
    # Make the GET request to the API endpoint
    response = requests.get(API_ENDPOINT, timeout=15) # Add timeout

    # Check if the request was successful
    if response.status_code == 200:
        print(f"\n--- API Response (Status Code: {response.status_code}) ---")
        try:
            # Attempt to parse JSON and print prettified
            response_json = response.json()
            print(json.dumps(response_json, indent=2))
        except json.JSONDecodeError:
            print("Error: Could not decode JSON response.")
            print("Raw Response Text:")
            print(response.text)
        print("------------------------------------")

    else:
        print(f"\n--- API Request Failed (Status Code: {response.status_code}) ---")
        print("Response Headers:")
        print(json.dumps(dict(response.headers), indent=2))
        print("\nResponse Body:")
        try:
            # Try to print JSON error response prettified
            error_json = response.json()
            print(json.dumps(error_json, indent=2))
        except json.JSONDecodeError:
            # Print raw text if not JSON
            print(response.text)
        print("------------------------------------")


except requests.exceptions.ConnectionError as e:
    print(f"\n--- Connection Error ---")
    print(f"Could not connect to the backend API at {BACKEND_BASE_URL}.")
    print("Please ensure the backend server is running.")
    print(f"Error details: {e}")
    print("------------------------")

except requests.exceptions.Timeout:
    print(f"\n--- Timeout Error ---")
    print(f"The request to {API_ENDPOINT} timed out.")
    print("---------------------")

except requests.exceptions.RequestException as e:
    print(f"\n--- Request Error ---")
    print(f"An error occurred during the API request: {e}")
    print("---------------------")

except Exception as e:
    print(f"\n--- Unexpected Error ---")
    print(f"An unexpected error occurred: {e}")
    print("------------------------")