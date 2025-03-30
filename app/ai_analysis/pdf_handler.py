"""
PDF handling module for the legislative analysis system.

This module provides functionality for handling PDF files in the legislative analysis system,
including detection, extraction, and processing for use with OpenAI's vision-enabled models.
"""

import base64
import logging
import re
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

def is_pdf_content(content: bytes) -> bool:
    """
    Check if the binary content is a PDF file.
    
    Args:
        content: Binary content to check
        
    Returns:
        True if the content appears to be a PDF, False otherwise
    """
    return content.startswith(b'%PDF-')

def encode_pdf_for_vision(pdf_content: bytes) -> str:
    """
    Encode PDF content as base64 for use with vision-enabled models.
    
    Args:
        pdf_content: Raw PDF bytes
        
    Returns:
        Base64-encoded data URL for the PDF with the correct MIME type
    """
    if not isinstance(pdf_content, bytes):
        raise ValueError("PDF content must be bytes")
        
    # Encode the PDF as base64 with the correct application/pdf MIME type
    base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
    return f"data:application/pdf;base64,{base64_pdf}"

def prepare_vision_message(content: bytes, prompt: str) -> Dict[str, Any]:
    """
    Prepare a message for vision-enabled models that can handle PDFs.
    
    Args:
        content: Binary PDF content
        prompt: The prompt to send with the content
        
    Returns:
        Message object for the API call
    """
    if not is_pdf_content(content):
        raise ValueError("Content is not a PDF")
        
    encoded_pdf = encode_pdf_for_vision(content)
    
    return {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": encoded_pdf
                }
            },
            {
                "type": "text",
                "text": prompt
            }
        ]
    }

def _import_pdf_dependencies():
    """
    Import all dependencies needed for PDF processing.
    
    This function isolates the imports to avoid making them global dependencies.
    The system can work even if these libraries are not installed, with appropriate error handling.
    
    Returns:
        Tuple containing (pypdf2, bytesio) modules
        
    Raises:
        ImportError: If required libraries are not installed
    """
    # These imports are intentionally inside the function to make them optional
    # pylint: disable=import-outside-toplevel
    import PyPDF2
    from io import BytesIO
    return PyPDF2, BytesIO

def _process_pdf_text_extraction(pdf_content: bytes) -> str:
    """
    Process PDF content and extract text.
    
    This function handles the actual PDF processing logic, including:
    - Importing necessary dependencies
    - Creating file objects
    - Extracting text from all pages
    - Combining and processing the extracted text
    
    Args:
        pdf_content: Binary PDF content
        
    Returns:
        Extracted text as a string
        
    Raises:
        ImportError: If required libraries are not installed
        ValueError: If the content is not a valid PDF
    """
    # Import dependencies dynamically
    pypdf2, bytesio = _import_pdf_dependencies()
    
    # Verify it's actually a PDF
    if not is_pdf_content(pdf_content):
        raise ValueError("Content is not a valid PDF")
        
    # Create a file-like object from the bytes
    pdf_file = bytesio(pdf_content)
    
    # Create a PDF reader object
    pdf_reader = pypdf2.PdfReader(pdf_file)
    
    # Extract text from all pages
    text_content = []
    for page_num, page in enumerate(pdf_reader.pages):
        text_content.append(page.extract_text() or "")
        
    # Combine all pages with newlines between them
    full_text = "\n\n".join(text_content)
    
    # If we couldn't extract any text, provide a meaningful message
    if not full_text.strip():
        logger.warning("PDF text extraction yielded empty result")
        return "[PDF contains no extractable text - may be scanned or image-based]"
        
    return full_text

def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extract text from a PDF file as a fallback mechanism.
    Uses PyPDF2 to extract text content from binary PDF data.
    
    Args:
        pdf_content: Binary PDF content
        
    Returns:
        Extracted text as a string
        
    Raises:
        ValueError: If the content is not a valid PDF or text extraction fails
    """
    try:
        return _process_pdf_text_extraction(pdf_content)
        
    except ImportError:
        logger.error("PyPDF2 library not installed. Cannot extract text from PDF.")
        return "[PDF text extraction unavailable - PyPDF2 not installed]"
        
    except (ValueError, IOError) as e:
        logger.error("Error extracting text from PDF: %s", str(e))
        return f"[PDF text extraction failed: {str(e)}]"
        
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Keep broader exception as final fallback for robustness
        logger.error("Unexpected error extracting text from PDF: %s", str(e))
        return f"[PDF text extraction failed: {str(e)}]"

def get_pdf_metadata(pdf_content: bytes) -> Dict[str, Any]:
    """
    Extract metadata from a PDF file.
    
    Args:
        pdf_content: Binary PDF content
        
    Returns:
        Dictionary of metadata
    """
    # Check if it's actually a PDF
    if not is_pdf_content(pdf_content):
        return {"is_pdf": False}

    # Extract PDF version from header
    version_match = re.search(rb'%PDF-(\d+\.\d+)', pdf_content[:1024])
    version = version_match[1].decode('utf-8') if version_match else "unknown"

    return {
        "is_pdf": True,
        "size_bytes": len(pdf_content),
        "pdf_version": version,
        "content_type": "application/pdf"
    }

def process_pdf_for_analysis(pdf_content: bytes, prompt: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Process a PDF file for analysis, preparing it for the OpenAI API and extracting metadata.
    
    Args:
        pdf_content: Binary PDF content
        prompt: The prompt to use for analysis
        
    Returns:
        Tuple of (message for API, metadata about the PDF)
    """
    metadata = get_pdf_metadata(pdf_content)
    
    if not metadata["is_pdf"]:
        raise ValueError("Content is not a PDF")
    
    message = prepare_vision_message(pdf_content, prompt)
    
    return message, metadata
