#!/usr/bin/env python3
"""
Script to fix the HTML content handling in the analyzer.
This script:
1. Adds HTML stripping functionality to the analyzer
2. Reduces token count by removing HTML tags
"""

import os
import sys
import logging
import re

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_html_content_handling():
    """Fix the HTML content handling in the analyzer."""
    try:
        # Path to the analyzer.py file
        analyzer_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "ai_analysis", "analyzer.py")
        
        # Check if the file exists
        if not os.path.exists(analyzer_file):
            logger.error(f"Analyzer file not found: {analyzer_file}")
            sys.exit(1)
        
        # Read the current content
        with open(analyzer_file, "r") as f:
            content = f.read()
        
        # Create the HTML stripping function
        html_stripper_function = """
    def _strip_html_tags(self, html_content):
        \"\"\"
        Strip HTML tags from content to reduce token count.
        
        Args:
            html_content: HTML content as string
            
        Returns:
            Plain text content with HTML tags removed
        \"\"\"
        if not html_content or not isinstance(html_content, str):
            return ""
            
        # Check if it looks like HTML
        if "<html" in html_content.lower() or "<body" in html_content.lower() or "<div" in html_content.lower():
            try:
                # Try to use BeautifulSoup if available
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    return soup.get_text(separator=' ', strip=True)
                except ImportError:
                    # Fallback to regex-based stripping
                    # Remove HTML tags
                    text = re.sub(r'<[^>]+>', ' ', html_content)
                    # Remove extra whitespace
                    text = re.sub(r'\\s+', ' ', text)
                    # Remove CSS and JavaScript
                    text = re.sub(r'<style[^>]*>[\\s\\S]*?</style>', '', text)
                    text = re.sub(r'<script[^>]*>[\\s\\S]*?</script>', '', text)
                    return text.strip()
            except Exception as e:
                logger.warning(f"Error stripping HTML tags: {e}")
                # Return a truncated version as fallback
                return html_content[:100000]  # Limit to 100k chars
        else:
            # Not HTML, return as is
            return html_content
"""
        
        # Add the function to the class
        if "_strip_html_tags" not in content:
            # Find the class definition
            class_match = re.search(r'class AIAnalysis[^\n]*:', content)
            if class_match:
                # Insert the function after the class definition
                insert_pos = class_match.end()
                content = content[:insert_pos] + html_stripper_function + content[insert_pos:]
                logger.info("Added _strip_html_tags function to AIAnalysis class")
            else:
                logger.error("Could not find AIAnalysis class definition")
                sys.exit(1)
        else:
            logger.info("_strip_html_tags function already exists")
        
        # Now modify the analyze_legislation method to use the HTML stripping function
        # Find the analyze_legislation method
        analyze_method_match = re.search(r'def analyze_legislation\([^)]*\):[^\n]*\n', content)
        if not analyze_method_match:
            logger.error("Could not find analyze_legislation method")
            sys.exit(1)
        
        # Find where the text content is retrieved
        text_content_match = re.search(r'text_content = [^\n]*\n', content)
        if not text_content_match:
            logger.error("Could not find text_content assignment")
            sys.exit(1)
        
        # Add HTML stripping after text content retrieval
        html_stripping_code = """
            # Strip HTML tags if present to reduce token count
            if text_content and isinstance(text_content, str) and len(text_content) > 10000:
                logger.info(f"Stripping HTML tags from large text content ({len(text_content)} chars)")
                text_content = self._strip_html_tags(text_content)
                logger.info(f"After stripping HTML tags: {len(text_content)} chars")
"""
        
        # Check if the HTML stripping code is already added
        if "Stripping HTML tags" not in content:
            # Insert the HTML stripping code after the text content retrieval
            insert_pos = text_content_match.end()
            content = content[:insert_pos] + html_stripping_code + content[insert_pos:]
            logger.info("Added HTML stripping code to analyze_legislation method")
        else:
            logger.info("HTML stripping code already exists")
        
        # Write the modified content back to the file
        with open(analyzer_file, "w") as f:
            f.write(content)
        
        logger.info(f"Successfully updated {analyzer_file}")
        
        # Create a requirements file for BeautifulSoup
        requirements_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bs4_requirements.txt")
        with open(requirements_file, "w") as f:
            f.write("beautifulsoup4>=4.9.0\n")
        
        logger.info(f"Created requirements file: {requirements_file}")
        logger.info("Run 'pip install -r bs4_requirements.txt' to install BeautifulSoup")
        
    except Exception as e:
        logger.error(f"Error fixing HTML content handling: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting HTML content handling fix")
    fix_html_content_handling()
    logger.info("Fix completed successfully")