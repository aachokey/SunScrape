import re

"""
Utility functions for formatting scraped data
"""


def get_name(text):
    name = re.sub(r'\([^)]*\)', '', text)
    return name.strip()


def get_party(text):
    if "(DEM)" in text:
        return "Democrat"
    elif "(REP)" in text:
        return "Republican"
    else:
        return ""

def strip_spaces(text):
    return text.strip()