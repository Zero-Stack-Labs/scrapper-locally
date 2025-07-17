import re
from typing import Optional


def strip_html_from_text(text: str) -> str:
    """
    Strip HTML tags from text while preserving line breaks and keeping only plain text content.
    
    Args:
        text (str): The input text that may contain HTML tags
        
    Returns:
        str: Clean text with HTML tags removed and line breaks preserved
        
    Example:
        >>> strip_html_from_text('<p>Hello <strong>world</strong></p><p>Second paragraph</p>')
        'Hello world\\n\\nSecond paragraph'
    """
    if not text:
        return text
    
    # Convert HTML line break elements to newlines before removing tags
    clean_text = text
    clean_text = re.sub(r'<br\s*/?>', '\n', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'<p\s*/?>', '\n', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'</p>', '\n', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'<div\s*[^>]*>', '\n', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'</div>', '\n', clean_text, flags=re.IGNORECASE)
    
    # Remove all other HTML tags
    clean_text = re.sub(r'<[^>]+>', '', clean_text)
    
    # Replace common HTML entities
    clean_text = clean_text.replace('&nbsp;', ' ')
    clean_text = clean_text.replace('&amp;', '&')
    clean_text = clean_text.replace('&lt;', '<')
    clean_text = clean_text.replace('&gt;', '>')
    clean_text = clean_text.replace('&quot;', '"')
    clean_text = clean_text.replace('&#39;', "'")
    clean_text = clean_text.replace('&apos;', "'")
    
    # Clean up excessive whitespace while preserving line breaks
    lines = clean_text.split('\n')
    cleaned_lines = [' '.join(line.split()) for line in lines]
    clean_text = '\n'.join(cleaned_lines)
    
    # Remove excessive newlines (more than 2 consecutive)
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    
    return clean_text.strip()


def strip_html_from_text_simple(text: str) -> str:
    """
    Simple HTML tag removal without preserving line breaks.
    
    Args:
        text (str): The input text that may contain HTML tags
        
    Returns:
        str: Clean text with all HTML tags and extra whitespace removed
        
    Example:
        >>> strip_html_from_text_simple('<p>Hello <strong>world</strong></p>')
        'Hello world'
    """
    if not text:
        return text
    
    # Remove all HTML tags
    clean_text = re.sub(r'<[^>]+>', '', text)
    
    # Replace common HTML entities
    clean_text = clean_text.replace('&nbsp;', ' ')
    clean_text = clean_text.replace('&amp;', '&')
    clean_text = clean_text.replace('&lt;', '<')
    clean_text = clean_text.replace('&gt;', '>')
    clean_text = clean_text.replace('&quot;', '"')
    clean_text = clean_text.replace('&#39;', "'")
    clean_text = clean_text.replace('&apos;', "'")
    
    # Clean up extra whitespace
    clean_text = ' '.join(clean_text.split())
    
    return clean_text.strip()