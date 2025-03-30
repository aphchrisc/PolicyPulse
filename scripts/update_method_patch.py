
# Replace the _update_or_insert_text method with this version
def _update_or_insert_text(self, existing: Optional[LegislationText], attrs: Dict[str, Any]) -> None:
    """Update existing text record or insert new one."""
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
