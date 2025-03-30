#!/usr/bin/env python3
"""
Script to fix the text content handling in the legislation_text table.
This script:
1. Ensures text content is properly encoded as binary before saving to the database
2. Adds a function to convert string content to bytes when needed
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_url():
    """Get the database URL from environment variables."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    return db_url

def fix_text_content_handling():
    """Fix the text content handling in the legislation_text table."""
    db_url = get_db_url()
    
    try:
        # Create engine
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # 1. Check if any text content needs to be converted to binary
        logger.info("Checking for text content that needs to be converted to binary...")
        
        # First, let's check the column type
        result = session.execute(text("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'legislation_text' AND column_name = 'text_content'
        """))
        
        column_type = result.scalar()
        logger.info(f"Current text_content column type: {column_type}")
        
        if column_type and column_type.lower() == 'bytea':
            logger.info("Column is already BYTEA type, checking for string content...")
            
            # Get all legislation_text records
            result = session.execute(text("""
                SELECT id, is_binary, content_type 
                FROM legislation_text
            """))
            
            records = result.fetchall()
            logger.info(f"Found {len(records)} legislation_text records")
            
            # Update the _update_or_insert_text method in app/legiscan_api.py
            logger.info("Creating a patch for app/legiscan_api.py...")
            
            patch_content = """
# Add this function to app/legiscan_api.py
def _ensure_binary_content(self, content, is_binary):
    \"\"\"
    Ensure content is in the correct format (bytes for binary content).
    
    Args:
        content: The content to check/convert
        is_binary: Whether the content should be treated as binary
        
    Returns:
        Content in the correct format
    \"\"\"
    if content is None:
        return None
        
    if is_binary:
        # If it should be binary but is a string, encode it
        if isinstance(content, str):
            return content.encode('utf-8', errors='replace')
        # If it's already bytes, return as-is
        elif isinstance(content, bytes):
            return content
        # Otherwise, convert to string then bytes
        else:
            return str(content).encode('utf-8', errors='replace')
    else:
        # If it should be text but is bytes, decode it
        if isinstance(content, bytes):
            return content.decode('utf-8', errors='replace')
        # If it's already a string, return as-is
        elif isinstance(content, str):
            return content
        # Otherwise, convert to string
        else:
            return str(content)
"""
            
            # Write the patch to a file
            patch_file = os.path.join(os.path.dirname(__file__), "legiscan_api_patch.py")
            with open(patch_file, "w") as f:
                f.write(patch_content)
            
            logger.info(f"Patch written to {patch_file}")
            
            # Update the _update_or_insert_text method
            update_method_patch = """
# Replace the _update_or_insert_text method with this version
def _update_or_insert_text(self, existing: Optional[LegislationText], attrs: Dict[str, Any]) -> None:
    \"\"\"Update existing text record or insert new one.\"\"\"
    # Handle binary content properly
    if 'text_content' in attrs:
        # Get the is_binary flag
        is_binary = attrs.get('is_binary', False)
        
        # Ensure content is in the correct format
        attrs['text_content'] = self._ensure_binary_content(attrs['text_content'], is_binary)
        
        # Set content_type if not already set
        if is_binary and ('content_type' not in attrs or not attrs['content_type']):
            if isinstance(attrs['text_content'], bytes):
                attrs['content_type'] = self._detect_content_type(attrs['text_content'])
            else:
                attrs['content_type'] = 'text/plain'
                
        # Set file_size if not already set
        if 'file_size' not in attrs or not attrs['file_size']:
            if attrs['text_content'] is not None:
                if isinstance(attrs['text_content'], bytes):
                    attrs['file_size'] = len(attrs['text_content'])
                elif isinstance(attrs['text_content'], str):
                    attrs['file_size'] = len(attrs['text_content'].encode('utf-8'))
                else:
                    attrs['file_size'] = 0
                    
        # Set text_metadata if not already set
        if 'text_metadata' not in attrs or not attrs['text_metadata']:
            if attrs['text_content'] is not None:
                if is_binary:
                    attrs['text_metadata'] = {
                        'is_binary': True,
                        'content_type': attrs.get('content_type', 'application/octet-stream'),
                        'size_bytes': attrs.get('file_size', 0)
                    }
                else:
                    attrs['text_metadata'] = {
                        'is_binary': False,
                        'encoding': 'utf-8',
                        'size_bytes': attrs.get('file_size', 0)
                    }
    
    if existing:
        for k, v in attrs.items():
            setattr(existing, k, v)
    else:
        new_text = LegislationText(**attrs)
        self.db_session.add(new_text)
"""
            
            # Write the update method patch to a file
            update_method_file = os.path.join(os.path.dirname(__file__), "update_method_patch.py")
            with open(update_method_file, "w") as f:
                f.write(update_method_patch)
            
            logger.info(f"Update method patch written to {update_method_file}")
            
            # Create a script to apply the patches
            apply_script = """#!/bin/bash
# Apply the patches to app/legiscan_api.py

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Path to the legiscan_api.py file
LEGISCAN_API_FILE="../app/legiscan_api.py"

# Check if the file exists
if [ ! -f "$SCRIPT_DIR/$LEGISCAN_API_FILE" ]; then
    echo "Error: $LEGISCAN_API_FILE not found"
    exit 1
fi

# Add the _ensure_binary_content method
echo "Adding _ensure_binary_content method..."
cat "$SCRIPT_DIR/legiscan_api_patch.py" >> "$SCRIPT_DIR/$LEGISCAN_API_FILE"

# Replace the _update_or_insert_text method
echo "Replacing _update_or_insert_text method..."
sed -i.bak '/def _update_or_insert_text/,/self.db_session.add(new_text)/c\\
# Method replaced by fix_text_content_handling.py\\
'"$(cat "$SCRIPT_DIR/update_method_patch.py")" "$SCRIPT_DIR/$LEGISCAN_API_FILE"

echo "Patches applied successfully"
"""
            
            # Write the apply script to a file
            apply_script_file = os.path.join(os.path.dirname(__file__), "apply_patches.sh")
            with open(apply_script_file, "w") as f:
                f.write(apply_script)
            
            # Make the script executable
            os.chmod(apply_script_file, 0o755)
            
            logger.info(f"Apply script written to {apply_script_file}")
            logger.info("Run the apply script to apply the patches")
            
        else:
            logger.info(f"Column type is {column_type}, not BYTEA. Run fix_legislation_text_table.py first.")
        
        # Close the session
        session.close()
        
    except Exception as e:
        logger.error(f"Error fixing text content handling: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting text content handling fix")
    fix_text_content_handling()
    logger.info("Fix completed successfully")