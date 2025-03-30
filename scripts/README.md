# PolicyPulse Scripts

This directory contains scripts for managing the PolicyPulse application, particularly for fetching and analyzing legislative bills.

## Scripts Overview

### 1. `fetch_initial_bills.py`

This script fetches bills from the LegiScan API, saves them to the database, and runs AI analysis on them.

#### Features:
- Fetches bills from both US Congress and Texas legislature
- Saves bills to the database with proper sanitization of text content
- Runs AI analysis on the bills
- Provides detailed error handling and reporting
- Supports filtering by jurisdiction (US-only or TX-only)
- Includes dry-run mode for testing
- Allows retrying previously failed analyses
- Supports custom AI models

#### Usage:
```bash
# Basic usage (fetch 6 bills and analyze them)
python scripts/fetch_initial_bills.py

# Fetch 10 bills but skip analysis
python scripts/fetch_initial_bills.py --limit 10 --no-analysis

# Fetch only US Congress bills
python scripts/fetch_initial_bills.py --us-only

# Fetch only Texas bills
python scripts/fetch_initial_bills.py --tx-only

# Retry previously failed analyses
python scripts/fetch_initial_bills.py --retry-failed --no-analysis

# Dry run (simulate without saving to database)
python scripts/fetch_initial_bills.py --dry-run

# Use a specific AI model
python scripts/fetch_initial_bills.py --model "gpt-4o"
```

### 2. `check_api_key.py`

This script checks if the LegiScan API key is properly set in the environment variables.

#### Usage:
```bash
python scripts/check_api_key.py
```

### 3. `fix_enum_values.py`

This script checks and fixes enum values in the database to match the code.

#### Usage:
```bash
python scripts/fix_enum_values.py
```

### 4. `test_sanitize_text.py`

This script tests the improved `sanitize_text` function to ensure it properly handles NUL characters and other problematic content.

#### Usage:
```bash
python scripts/test_sanitize_text.py
```

## Recent Improvements

### 1. Fixed NUL Character Issue

The scripts now properly handle NUL characters and other control characters in bill text, which previously caused database errors, especially with Congressional bills.

### 2. Enhanced Error Handling

- Better tracking of failed operations
- Detailed error reporting
- Ability to continue processing other bills when one fails

### 3. Improved AI Analysis

- Progress tracking for AI analysis
- Better error handling during analysis
- Option to retry previously failed analyses

### 4. Added New Features

- Filtering by jurisdiction (US-only or TX-only)
- Dry-run mode for testing
- Support for custom AI models
- Detailed summary reporting

## Troubleshooting

If you encounter issues with the scripts, check the following:

1. **Database Connection**: Ensure the database is running and accessible.
2. **API Key**: Verify that the LegiScan API key is correctly set in the environment variables.
3. **Text Sanitization**: If you still encounter issues with text content, check the `sanitize_text` function in `app/legiscan_api.py`.
4. **AI Analysis**: If AI analysis fails, check the OpenAI API key and model availability.

## Development

When making changes to these scripts, please ensure:

1. Proper error handling is maintained
2. Text content is properly sanitized before database operations
3. Changes are tested thoroughly, especially with Congressional bills
4. Documentation is updated to reflect any changes