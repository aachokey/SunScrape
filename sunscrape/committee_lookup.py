"""Committee lookup system for matching transaction data with committee information."""

import csv
import logging
import re
import requests
from typing import Dict, List, Optional, Any
from collections import defaultdict
from bs4 import BeautifulSoup

from .base import SunScraper, HTTPError, ParseError

logger = logging.getLogger(__name__)


def normalize_committee_name(name: str) -> str:
    """
    Normalize a committee name for matching purposes.
    
    Removes extra spaces, standardizes case, and handles common variations.
    
    Args:
        name: Committee name string to normalize
        
    Returns:
        Normalized name string
    """
    if not name:
        return ""
    
    # Remove common suffixes/designations
    name = re.sub(r'\s+(PC|PAC|INC|LLC|CORP|CORPORATION|COMMITTEE)\s*$', '', name, flags=re.IGNORECASE)
    
    # Standardize case and remove extra spaces
    name = ' '.join(name.split())
    name = name.strip()
    
    return name


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
        
        # Index: normalized name -> list of account numbers
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
        from .base import SunScraper
        
        try:
            # Download to temp file
            temp_file = SunScraper.download_active_committees()
            
            # Load from file
            loaded = self._load_from_file(temp_file)
            
            # Clean up temp file
            import os
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
                
                loaded = 0
                for row in reader:
                    # Try different possible field names for account number
                    acct_num = (
                        row.get('AcctNum', '') or 
                        row.get('Account Number', '') or
                        row.get('AccountNumber', '')
                    ).strip()
                    
                    if not acct_num:
                        continue
                    
                    # Try different possible field names for committee name
                    committee_name = (
                        row.get('Committee Name', '') or
                        row.get('CommitteeName', '') or
                        row.get('Name', '') or
                        row.get('ComName', '')
                    ).strip()
                    
                    if not committee_name:
                        continue
                    
                    # Store committee data
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
        Add a committee to all indexes.
        
        Args:
            acct_num: Account number (key)
            committee_name: Committee name
        """
        normalized_name = normalize_committee_name(committee_name)
        if normalized_name:
            self.name_index[normalized_name].append(acct_num)
    
    def find_by_name(
        self,
        name: str,
        use_cache: bool = True,
        fallback_search: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find committees by name using exact matching, with optional fallback to online search.
        
        Args:
            name: Committee name to search for
            use_cache: Whether to use cached results for repeated lookups. Default: True
            fallback_search: Whether to search online if not found in loaded data. Default: True
            
        Returns:
            List of matching committee dictionaries
        """
        if not name:
            return []
        
        normalized_search = normalize_committee_name(name)
        if not normalized_search:
            return []
        
        # Check cache first
        if use_cache:
            if normalized_search in self._lookup_cache:
                return self._lookup_cache[normalized_search]
        
        matches = []
        seen_accounts = set()
        
        # Exact match on normalized name
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
            logger.debug(f"Committee '{name}' not found in loaded data, searching online...")
            online_match = self._search_online(name)
            if online_match:
                matches.append(online_match)
                # Add to cache and indexes for future use
                if online_match['account'] not in self.committees:
                    self.committees[online_match['account']] = online_match['committee']
                    self._index_committee(online_match['account'], name)
                    self.total_committees += 1
        
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
            
            # Find best matching committee from search results
            best_match = None
            best_name = None
            normalized_search = normalize_committee_name(committee_name).lower()
            
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
                    normalized_found = normalize_committee_name(found_name).lower()
                    
                    # Check if this is an exact or close match
                    if normalized_found == normalized_search:
                        best_match = account_num
                        best_name = found_name
                        break
                    elif normalized_search in normalized_found or normalized_found in normalized_search:
                        # Partial match - use this if we don't have an exact match
                        if best_match is None:
                            best_match = account_num
                            best_name = found_name
            
            if not best_match:
                return None
            
            # Get committee details
            details = self._get_committee_details_online(best_match)
            if not details:
                return None
            
            # Build committee data dictionary
            committee_data = {
                'AcctNum': best_match,
                'Committee Name': best_name or committee_name,
                'Name': best_name or committee_name,
                'Type': details.get('type', ''),
                'Status': details.get('status', ''),
                'Address': details.get('address', ''),
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
        from .utils import strip_breaks
        
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
                
            details: Dict[str, str] = {
                "type": strip_breaks(rows[2].findAll('td')[1].text),
                "status": strip_breaks(rows[3].findAll('td')[1].text),
                "address": strip_breaks(rows[4].findAll('td')[1].text),
                "phone": strip_breaks(rows[5].findAll('td')[1].text),
                "chair": strip_breaks(rows[6].findAll('td')[1].text),
                "treasurer": strip_breaks(rows[7].findAll('td')[1].text),
                "registered_agent": strip_breaks(rows[8].findAll('td')[1].text),
                "purpose": strip_breaks(rows[9].findAll('td')[1].text),
                "affiliates": strip_breaks(rows[10].findAll('td')[1].text)
            }
            
            return details
        except Exception as e:
            logger.debug(f"Failed to fetch committee details for account {account_num}: {e}")
            return None

