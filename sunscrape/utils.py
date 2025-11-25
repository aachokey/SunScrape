"""Utility functions for formatting scraped data."""

import re
from datetime import datetime
from typing import Optional


def get_name(text: str) -> str:
    """
    Extract candidate/committee name by removing party designation in parentheses.
    
    Args:
        text: Text containing name and optional party designation
        
    Returns:
        Cleaned name string
    """
    name = re.sub(r'\([^)]*\)', '', text)
    return name.strip()


def get_party(text: str) -> str:
    """
    Extract party designation from text.
    
    Args:
        text: Text that may contain party designation
        
    Returns:
        Party name ("Democrat", "Republican") or empty string
    """
    if "(DEM)" in text:
        return "Democrat"
    elif "(REP)" in text:
        return "Republican"
    else:
        return ""


def strip_spaces(text: str) -> str:
    """
    Strip whitespace from text.
    
    Args:
        text: Text to clean
        
    Returns:
        Stripped text
    """
    return text.strip()


def strip_breaks(text: str) -> str:
    """
    Remove line breaks, tabs, and normalize whitespace.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text with normalized whitespace
    """
    text = text.replace('\n', '')
    text = text.replace('\r', '')
    text = text.replace('\t', '')
    text = text.replace('\xa033606', '')
    text = text.replace('  ', ' ')
    text = text.replace('   ', ' ')
    text = re.sub(' +', ' ', text)
    return text.strip()


def toDate(text: str) -> str:
    """
    Convert a date string to ISO format.
    
    Args:
        text: Date string in MM/DD/YYYY format
        
    Returns:
        ISO format date string (YYYY-MM-DD) or empty string if parsing fails
    """
    text = text.strip()

    try:
        dt = datetime.strptime(text, '%m/%d/%Y')
        return dt.date().isoformat()
    except ValueError:
        return ''
