"""Scraper for committee campaign finance data."""

from typing import Dict, Any, List, Optional
import io
import csv
import difflib
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup

from .base import SunScraper, HTTPError, ParseError
from .utils import strip_breaks, strip_spaces, toDate

logger = logging.getLogger(__name__)


class CommitteeScraper:
    """Returns campaign finance data for a committee."""

    url = "https://dos.elections.myflorida.com/cgi-bin/TreFin.exe"
    payload = {
        "account": 0,
        "comname": "",
        "CanCom": "Comm",
        "seqnum": 0,
        "queryfor": 1,
        "queryorder": "DAT",
        "queryoutput": 2,
        "query": "Submit Query Now"
    }

    def __init__(self, committee_name: str = '', result_type: str = '') -> None:
        """
        Initialize the committee scraper.

        Args:
            committee_name: Committee name, or partial name
            result_type: One of 'contributions', 'expenditures', 'other', or 'transfers'

        Raises:
            ValueError: If committee is not found or result_type is invalid
        """
        if not committee_name:
            raise ValueError("committee_name is required")
        if not result_type:
            raise ValueError("result_type is required. Must be one of: contributions, expenditures, other, transfers")
        if result_type not in ['contributions', 'expenditures', 'other', 'transfers']:
            raise ValueError(f"Invalid result_type: {result_type}. Must be one of: contributions, expenditures, other, transfers")
            
        self.committee_name = committee_name
        self.result_type = result_type
        self.account_num = self._get_account_num()
        if self.account_num is None:
            raise ValueError(f"Committee '{committee_name}' not found")
        self.committee_details = self._get_details()
        self._update_payload()
        self.results = self._parse_results()

    def _get_account_num(self) -> Optional[str]:
        """
        Get the account number for the committee.
        
        Returns:
            Account number as string, or None if not found
            
        Raises:
            HTTPError: If the request fails
        """
        committee_search_url = "https://dos.elections.myflorida.com/committees/ComLkupByName.asp"
        search_payload = {
            "searchtype": 1,
            "comName": self.committee_name[:50],
            "LkupTypeName": "L",
            "NameSearchBtn": "Search by Name"
        }

        try:
            r = requests.get(
                committee_search_url,
                params=search_payload,
                headers=SunScraper._default_headers,
                timeout=30
            )
            r.raise_for_status()
            return self.search_accounts(r)
        except requests.RequestException as e:
            raise HTTPError(f"Failed to search for committee: {e}") from e

    def search_accounts(self, response: requests.Response) -> Optional[str]:
        """
        Parse the response to find matching committee account numbers.
        
        Args:
            response: HTTP response from committee search
            
        Returns:
            Account number as string, or None if not found
        """
        try:
            soup = BeautifulSoup(response.content, "html.parser")
            tables = soup.findAll("table")
            if len(tables) < 3:
                return None
            committee_table = tables[2]
            rows = committee_table.findAll('tr')
            
            committee_name_list = []
            committees: Dict[str, str] = {}
            
            for committee in rows[1:]:
                cells = committee.findAll('td')
                if not cells:
                    continue
                name_cell = cells[0]
                link = name_cell.find('a')
                if not link:
                    continue
                name = link.text.strip()
                url = link.get('href', '')
                if '=' in url:
                    account_num = url.split('=')[1]
                    committee_name_list.append(name)
                    committees[name] = account_num
            
            if not committee_name_list:
                return None
                
            # Find best matching committee
            matches = difflib.get_close_matches(self.committee_name, committee_name_list, n=1)
            if matches:
                return committees[matches[0]]
            return None
        except (IndexError, AttributeError, KeyError, ValueError) as e:
            return None

    def _update_payload(self):
        """
        Update the payload sent to the campaign finance site.
        """

        self.payload["comname"] = self.committee_name
        self.payload["account"] = int(self.account_num)

        if self.result_type == "contributions":
            self.payload["queryfor"] = 1
        elif self.result_type == "expenditures":
            self.payload["queryfor"] = 2
        elif self.result_type == "other":
            self.payload["queryfor"] = 3
        elif self.result_type == "transfers":
            self.payload["queryfor"] = 4

    def _get_details(self) -> Dict[str, str]:
        """
        Get detailed information about the committee.
        
        Returns:
            Dictionary containing committee details
            
        Raises:
            HTTPError: If the request fails
            ParseError: If the page structure is unexpected
        """
        details_url = f"https://dos.elections.myflorida.com/committees/ComDetail.asp?account={self.account_num}"
        
        try:
            r = requests.get(details_url, headers=SunScraper._default_headers, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            details_table = soup.find("table")
            
            if details_table is None:
                raise ParseError("Could not find details table on committee page")
                
            rows = details_table.findAll('tr')
            if len(rows) < 11:
                raise ParseError("Unexpected table structure on committee details page")
                
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
        except requests.RequestException as e:
            raise HTTPError(f"Failed to fetch committee details: {e}") from e
        except (IndexError, AttributeError) as e:
            raise ParseError(f"Failed to parse committee details: {e}") from e

    def request(self, url: str, payload: Dict[str, Any]) -> Optional[Any]:
        """
        Make a request to the campaign finance site.
        
        Args:
            url: The URL to request
            payload: Query parameters to send
            
        Returns:
            A CSV DictReader iterator, or None if the request failed
            
        Raises:
            HTTPError: If the request fails
        """
        try:
            r = requests.get(url, params=payload, headers=SunScraper._default_headers, timeout=30)
            r.raise_for_status()
            
            if r.status_code == 200:
                reader = csv.DictReader(
                    io.StringIO(r.text),
                    delimiter='\t',
                    quoting=csv.QUOTE_NONE
                )
                return reader
            else:
                raise HTTPError(f"Server returned status code {r.status_code}")
        except requests.RequestException as e:
            raise HTTPError(f"Request failed: {e}") from e

    def _parse_results(self) -> List[Dict[str, Any]]:
        """
        Clean up the returned results.
        
        Returns:
            List of cleaned result dictionaries
        """
        data = self.request(self.url, self.payload)

        if data is None:
            return []

        clean_data: List[Dict[str, Any]] = []

        if self.result_type == 'contributions':
            for item in data:
                cleaned_item: Dict[str, Any] = {}
                cleaned_item['report_year'] = item['Rpt Yr']
                cleaned_item['report_type'] = item['Rpt Type']
                cleaned_item['date'] = toDate(item['Date'])
                cleaned_item['amount'] = float(item['Amount'])
                cleaned_item['type'] = strip_spaces(item['Typ'])
                cleaned_item['contributor_name'] = strip_spaces(item['Contributor Name'])
                cleaned_item['contributor_address'] = strip_spaces(item['Address'])
                cleaned_item['contributor_address2'] = strip_spaces(item['City State Zip'])
                cleaned_item['contributor_occupation'] = strip_spaces(item['Occupation'])
                cleaned_item['item_type'] = strip_spaces(item['Typ'])
                cleaned_item['inkind_description'] = strip_spaces(item['InKind Desc'])

                clean_data.append(cleaned_item)

            return clean_data

        elif self.result_type == 'expenditures':
            for item in data:
                cleaned_item: Dict[str, Any] = {}
                cleaned_item['report_year'] = item['Rpt Yr']
                cleaned_item['report_type'] = item['Rpt Type']
                cleaned_item['date'] = toDate(item['Date'])
                cleaned_item['amount'] = float(item['Amount'])
                cleaned_item['paid_to_name'] = strip_spaces(item['Expense Paid To'])
                cleaned_item['paid_to_address'] = strip_spaces(item['Address'])
                cleaned_item['paid_to_address2'] = strip_spaces(item['City State Zip'])
                cleaned_item['purpose'] = strip_spaces(item['Purpose'])
                cleaned_item['item_type'] = strip_spaces(item['Typ Reimb'])

                clean_data.append(cleaned_item)

            return clean_data

        # Other result types can be added here
        return clean_data

    def save_committee_details(self, filepath: Optional[str] = None) -> str:
        """
        Save committee details to a CSV file.
        
        Args:
            filepath: Optional filepath. If not provided, generates a filename with timestamp.
            
        Returns:
            Path to the saved file
            
        Raises:
            ValueError: If committee details are not available
            IOError: If file cannot be written
        """
        if not hasattr(self, 'committee_details') or self.committee_details is None:
            raise ValueError("No committee details available to save.")
        
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_name = self.committee_name.replace(' ', '_').replace('/', '_')[:50]
            filepath = f"committee_{safe_name}_{timestamp}.csv"
        
        try:
            # Convert single dict to list for CSV writer
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.committee_details.keys())
                writer.writeheader()
                writer.writerow(self.committee_details)
            logger.info(f"Saved committee details to {filepath}")
            return filepath
        except IOError as e:
            logger.error(f"Failed to save committee details: {e}")
            raise IOError(f"Failed to save committee details: {e}") from e
