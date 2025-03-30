#!/usr/bin/env python
"""
run_test.py

Script to load environment variables and run the impact ratings test.
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check if OpenAI API key is set
if not os.environ.get("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY environment variable is not set.")
    print("Please set it in your .env file or environment variables.")
    sys.exit(1)

# Get command line arguments
args = sys.argv[1:]

# Run the test script with the provided arguments
cmd = ["python", "scripts/test_impact_ratings.py"] + args
result = subprocess.run(cmd)

# Exit with the same code as the test script
sys.exit(result.returncode)
