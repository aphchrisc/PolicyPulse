
# Add this function to app/legiscan_api.py
def _ensure_binary_content(self, content, is_binary):
    """
    Ensure content is in the correct format (bytes for binary content).
    
    Args:
        content: The content to check/convert
        is_binary: Whether the content should be treated as binary
        
    Returns:
        Content in the correct format
    """
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
