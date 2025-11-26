"""Committee lookup system for matching transaction data with committee information."""

import csv
import logging
import os
import re
import requests
from typing import Dict, List, Optional, Any
from collections import defaultdict
from bs4 import BeautifulSoup
from datetime import datetime

from .base import SunScraper, HTTPError, ParseError
from .utils import strip_breaks

logger = logging.getLogger(__name__)


def normalize_committee_name(name: str, lowercase: bool = False) -> str:
    """
    Normalize a committee name for matching purposes.
    
    Removes extra spaces, standardizes case, and handles common variations.
    
    Args:
        name: Committee name string to normalize
        lowercase: Whether to convert to lowercase (for case-insensitive matching)
        
    Returns:
        Normalized name string
    """
    if not name:
        return ""
    
    # Remove common suffixes/designations (but keep them for some matching strategies)
    name = re.sub(r'\s+(PC|PAC|INC|LLC|CORP|CORPORATION|COMMITTEE)\s*$', '', name, flags=re.IGNORECASE)
    
    # Standardize case and remove extra spaces
    name = ' '.join(name.split())
    name = name.strip()
    
    if lowercase:
        name = name.lower()
    
    return name


def get_search_variants(search_term: str) -> List[str]:
    """
    Get search variants for a committee name, handling truncation issues.
    
    When a name is truncated at 50 chars, it might cut off mid-word.
    This function creates variants that handle partial words at the end.
    
    Args:
        search_term: The search term (may be truncated)
        
    Returns:
        List of search variants to try
    """
    normalized = normalize_committee_name(search_term, lowercase=True)
    variants = [normalized]
    
    # If the search term appears to be truncated (ends with a partial word),
    # create a variant without the last word
    words = normalized.split()
    if len(words) > 1:
        last_word = words[-1]
        # Check if last word is very short (likely truncated at 50 char limit)
        if len(last_word) <= 3:
            variant = ' '.join(words[:-1])
            if variant:
                variants.append(variant)
    
    return variants




class CommitteeLookup:
    """
    Manages committee data for matching with transaction records.
    
    This class loads committee data from CSV files, builds indexes for fast lookup,
    and provides methods to match committee names with transaction recipient/spender names.
    """
    
    def __init__(
        self,
        auto_load: bool = True
    ):
        """
        Initialize committee lookup and automatically load all active committees.
        
        Args:
            auto_load: Whether to automatically download and load all active committees (default: True)
        """
        # Primary storage: account number -> committee data
        self.committees: Dict[str, Dict[str, Any]] = {}
        
        # Index: normalized name (lowercase) -> list of account numbers
        self.name_index: Dict[str, List[str]] = defaultdict(list)
        
        self.total_committees = 0
        
        # Cache for lookups to avoid repeated searches for the same name
        self._lookup_cache: Dict[str, List[Dict[str, Any]]] = {}
        
        # Automatically load all active committees by default
        if auto_load:
            logger.info("Loading active committees...")
            self.load_from_download()
            logger.info(f"✓ Successfully loaded {self.total_committees} active committees")
    
    def load_from_download(self) -> int:
        """
        Download and load active committees from the Florida SOS website.
        
        Returns:
            Number of committees loaded
            
        Raises:
            HTTPError: If download fails
        """
        try:
            # Download to temp file
            temp_file = SunScraper.download_active_committees()
            
            # Load from file
            loaded = self._load_from_file(temp_file)
            
            # Clean up temp file
            try:
                os.remove(temp_file)
            except:
                pass
            
            return loaded
        except Exception as e:
            logger.error(f"Failed to download and load committees: {e}")
            raise
    
    def _load_from_file(self, filepath: str) -> int:
        """
        Load committee data from a CSV file (internal method).
        
        Args:
            filepath: Path to the committee CSV file
            
        Returns:
            Number of committees loaded
            
        Raises:
            IOError: If file cannot be read
            ValueError: If file format is invalid
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                if reader.fieldnames is None:
                    raise ValueError("CSV file has no headers")
                
                # Log fieldnames for debugging (first time only) - helps identify actual fieldnames
                if not hasattr(self, '_fieldnames_logged'):
                    logger.info(f"Committee CSV fieldnames: {reader.fieldnames}")
                    self._fieldnames_logged = True
                
                loaded = 0
                for row in reader:
                    # Use exact fieldname from CSV: 'AcctNum'
                    acct_num = row.get('AcctNum', '').strip()
                    
                    if not acct_num:
                        continue
                    
                    # Use exact fieldname from CSV: 'Committee Name' (with space)
                    committee_name = row.get('Committee Name', '').strip()
                    
                    if not committee_name:
                        continue
                    
                    # Store committee data (all fields preserved)
                    self.committees[acct_num] = dict(row)
                    
                    # Build indexes
                    self._index_committee(acct_num, committee_name)
                    
                    loaded += 1
                
                self.total_committees += loaded
                return loaded
                
        except IOError as e:
            logger.error(f"Failed to read committee file {filepath}: {e}")
            raise IOError(f"Failed to read committee file: {e}") from e
        except Exception as e:
            logger.error(f"Error loading committees from {filepath}: {e}")
            raise ValueError(f"Invalid committee file format: {e}") from e
    
    def _index_committee(self, acct_num: str, committee_name: str) -> None:
        """
        Add a committee to the index.
        
        Args:
            acct_num: Account number (key)
            committee_name: Committee name
        """
        # Index by normalized name (lowercase) for case-insensitive exact matching
        normalized_lower = normalize_committee_name(committee_name, lowercase=True)
        if normalized_lower:
            self.name_index[normalized_lower].append(acct_num)
    
    def find_by_name(
        self,
        name: str,
        use_cache: bool = True,
        fallback_search: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find committees by name using exact matching (case-insensitive), with optional fallback to online search.
        
        Args:
            name: Committee name to search for
            use_cache: Whether to use cached results for repeated lookups. Default: True
            fallback_search: Whether to search online if not found in loaded data. Default: True
            
        Returns:
            List of matching committee dictionaries
        """
        if not name:
            return []
        
        normalized_search = normalize_committee_name(name, lowercase=True)
        if not normalized_search:
            return []
        
        # Check cache first (use lowercase for cache key)
        if use_cache:
            if normalized_search in self._lookup_cache:
                return self._lookup_cache[normalized_search]
        
        matches = []
        seen_accounts = set()
        
        # Exact match on normalized name (case-insensitive)
        if normalized_search in self.name_index:
            for acct_num in self.name_index[normalized_search]:
                if acct_num not in seen_accounts:
                    committee = self.committees[acct_num]
                    matches.append({
                        'committee': committee,
                        'match_method': 'exact',
                        'match_confidence': 1.0,
                        'account': acct_num,
                        'entity_type': 'committee'
                    })
                    seen_accounts.add(acct_num)
        
        # Fallback: search online if not found in loaded data
        if not matches and fallback_search:
            logger.info(f"Committee '{name}' not found in loaded data ({self.total_committees} committees), searching online...")
            online_match = self._search_online(name)
            if online_match:
                matches.append(online_match)
                # Add to cache and indexes for future use
                if online_match['account'] not in self.committees:
                    self.committees[online_match['account']] = online_match['committee']
                    # Use the found name for indexing
                    found_name = online_match['committee'].get('Committee Name') or online_match['committee'].get('Name') or name
                    self._index_committee(online_match['account'], found_name)
                    self.total_committees += 1
                    logger.info(f"  Added '{found_name}' to committee lookup (account: {online_match['account']})")
            else:
                logger.debug(f"  Online search also failed to find '{name}'")
        
        # Cache the result
        if use_cache:
            self._lookup_cache[normalized_search] = matches
        
        return matches
    
    def _search_online(self, committee_name: str) -> Optional[Dict[str, Any]]:
        """
        Search for a committee online using the SOS website search.
        
        This is a fallback when the committee isn't in the loaded data.
        
        Args:
            committee_name: Committee name to search for
            
        Returns:
            Match dictionary with committee data, or None if not found
        """
        search_url = "https://dos.elections.myflorida.com/committees/ComLkupByName.asp"
        
        headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://dos.elections.myflorida.com",
            "referer": "https://dos.elections.myflorida.com/committees/",
        }
        
        data = {
            "searchtype": "1",
            "comName": committee_name[:50],  # Limit to 50 chars
            "LkupTypeName": "L",
            "NameSearchBtn": "Search by Name"
        }
        
        try:
            # Search for committee
            r = requests.post(search_url, headers=headers, data=data, timeout=30)
            r.raise_for_status()
            
            soup = BeautifulSoup(r.content, "html.parser")
            tables = soup.findAll("table")
            if len(tables) < 3:
                return None
            
            committee_table = tables[2]
            rows = committee_table.findAll('tr')
            
            if len(rows) < 2:
                return None
            
            # Find matching committee from search results (case-insensitive)
            # The search form has a 50 char limit, but results show full names
            # We prioritize matches that best match the source data name
            best_match = None
            best_name = None
            best_score = 0.0
            normalized_search = normalize_committee_name(committee_name, lowercase=True)
            # Also normalize the truncated search term (what we actually sent to the form)
            normalized_search_truncated = normalize_committee_name(committee_name[:50], lowercase=True)
            # Get search variants to handle truncation issues
            search_variants = get_search_variants(committee_name[:50])
            
            for row in rows[1:]:
                cells = row.findAll('td')
                if not cells:
                    continue
                name_cell = cells[0]
                link = name_cell.find('a')
                if not link:
                    continue
                
                found_name = link.text.strip()
                url = link.get('href', '')
                if '=' in url:
                    account_num = url.split('=')[1]
                    normalized_found = normalize_committee_name(found_name, lowercase=True)
                    score = 0.0
                    match_type = None
                    
                    # Strategy 1: Exact match (case-insensitive) - highest priority
                    if normalized_found == normalized_search:
                        best_match = account_num
                        best_name = found_name
                        best_score = 1.0
                        match_type = "exact"
                        break  # Perfect match, stop searching
                    
                    # Strategy 2: Found name starts with search term (high priority)
                    # Try all search variants to handle truncation issues
                    for variant in search_variants:
                        if normalized_found.startswith(variant):
                            # Score based on how much of the search term matches
                            score = len(variant) / len(normalized_found) if normalized_found else 0
                            if score > best_score:
                                best_match = account_num
                                best_name = found_name
                                best_score = score
                                match_type = f"starts_with_variant_{search_variants.index(variant)}"
                    
                    # Strategy 3: Search term is contained in found name (lower priority)
                    # Only use this if we don't have a start-of-string match
                    if best_score == 0.0:
                        for variant in search_variants:
                            if variant in normalized_found:
                                # Score based on how much of the search term is in the result
                                score = len(variant) / max(len(normalized_found), len(variant))
                                if score > best_score:
                                    best_match = account_num
                                    best_name = found_name
                                    best_score = score
                                    match_type = f"contains_variant_{search_variants.index(variant)}"
            
            if not best_match:
                return None
            
            # Get committee details
            details = self._get_committee_details_online(best_match)
            if not details:
                return None
            
            # Build committee data dictionary
            committee_address = details.get('address', '').strip()
            committee_data = {
                'AcctNum': best_match,
                'Committee Name': best_name or committee_name,
                'Name': best_name or committee_name,
                'Type': details.get('type', ''),
                'Status': details.get('status', ''),
                'Address': committee_address,
                'Phone': details.get('phone', ''),
                'Chair': details.get('chair', ''),
                'Treasurer': details.get('treasurer', ''),
                'Registered Agent': details.get('registered_agent', ''),
                'Purpose': details.get('purpose', ''),
                'Affiliates': details.get('affiliates', '')
            }
            
            logger.info(f"  ✓ Found committee '{best_name}' online (account: {best_match})")
            
            return {
                'committee': committee_data,
                'match_method': 'online_fallback',
                'match_confidence': 0.9,  # Slightly lower confidence for online matches
                'account': best_match,
                'entity_type': 'committee'
            }
            
        except Exception as e:
            logger.debug(f"Online committee search failed for '{committee_name}': {e}")
            return None
    
    def _get_committee_details_online(self, account_num: str) -> Optional[Dict[str, str]]:
        """
        Get committee details from the SOS website detail page.
        
        Args:
            account_num: Committee account number
            
        Returns:
            Dictionary with committee details, or None if not found
        """
        details_url = f"https://dos.elections.myflorida.com/committees/ComDetail.asp?account={account_num}"
        
        headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "referer": "https://dos.elections.myflorida.com/committees/ComLkupByName.asp",
        }
        
        try:
            r = requests.get(details_url, headers=headers, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            details_table = soup.find("table")
            
            if details_table is None:
                return None
                
            rows = details_table.findAll('tr')
            if len(rows) < 11:
                return None
                
            # Extract address - it's in row 4, column 1
            address_text = strip_breaks(rows[4].findAll('td')[1].text) if len(rows) > 4 and len(rows[4].findAll('td')) > 1 else ''
            
            details: Dict[str, str] = {
                "type": strip_breaks(rows[2].findAll('td')[1].text) if len(rows) > 2 and len(rows[2].findAll('td')) > 1 else '',
                "status": strip_breaks(rows[3].findAll('td')[1].text) if len(rows) > 3 and len(rows[3].findAll('td')) > 1 else '',
                "address": address_text,
                "phone": strip_breaks(rows[5].findAll('td')[1].text) if len(rows) > 5 and len(rows[5].findAll('td')) > 1 else '',
                "chair": strip_breaks(rows[6].findAll('td')[1].text) if len(rows) > 6 and len(rows[6].findAll('td')) > 1 else '',
                "treasurer": strip_breaks(rows[7].findAll('td')[1].text) if len(rows) > 7 and len(rows[7].findAll('td')) > 1 else '',
                "registered_agent": strip_breaks(rows[8].findAll('td')[1].text) if len(rows) > 8 and len(rows[8].findAll('td')) > 1 else '',
                "purpose": strip_breaks(rows[9].findAll('td')[1].text) if len(rows) > 9 and len(rows[9].findAll('td')) > 1 else '',
                "affiliates": strip_breaks(rows[10].findAll('td')[1].text) if len(rows) > 10 and len(rows[10].findAll('td')) > 1 else ''
            }
            
            return details
        except Exception as e:
            logger.debug(f"Failed to fetch committee details for account {account_num}: {e}")
            return None

