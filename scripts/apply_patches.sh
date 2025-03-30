#!/bin/bash
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
sed -i.bak '/def _update_or_insert_text/,/self.db_session.add(new_text)/c\
# Method replaced by fix_text_content_handling.py\
'"$(cat "$SCRIPT_DIR/update_method_patch.py")" "$SCRIPT_DIR/$LEGISCAN_API_FILE"

echo "Patches applied successfully"
