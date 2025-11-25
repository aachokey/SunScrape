import io
import csv
import logging
from typing import Dict, Optional, Any, Iterator, List
import requests
from datetime import datetime

from bs4 import BeautifulSoup
from collections import OrderedDict

logger = logging.getLogger(__name__)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class SunScrapeError(Exception):
    """Base exception for SunScrape errors."""
    pass


class HTTPError(SunScrapeError):
    """Raised when an HTTP request fails."""
    pass


class ParseError(SunScrapeError):
    """Raised when parsing data fails."""
    pass


class SunScraper(object):

    """ Base class for all the scrapers """

    date_format = '%m/%d/%Y'
    
    # Common headers used across all requests
    _default_headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
        "referer": "https://www.google.com/"
    }

    def request(self, url: str, payload: Dict[str, Any]) -> Optional[Iterator[Dict[str, str]]]:
        """
        Make a request to the campaign finance site and return a CSV reader.
        
        Args:
            url: The URL to request
            payload: Query parameters to send
            
        Returns:
            A CSV DictReader iterator, or None if the request failed
            
        Raises:
            HTTPError: If the request fails
        """
        logger.info(f"Fetching data for {self.result_type}...")
        try:
            r = requests.get(url, params=payload, headers=self._default_headers, timeout=30)
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
            logger.error(f"Request failed: {e}")
            raise HTTPError(f"Request failed: {e}") from e


    @classmethod
    def get_election_ids(cls) -> OrderedDict[str, str]:
        """
        Returns an OrderedDict of available elections and the state's unique ID for that election.

        Florida's campaign finance website has custom ID's for each election.
        Pass one of these IDs in the scrapers for records for that election,
        or just get 'All' via "all_time=True"

        Returns:
            OrderedDict mapping election names to their IDs
            
        Raises:
            HTTPError: If the request fails
            ParseError: If the page structure is unexpected
        """
        elections = OrderedDict()

        url = cls.portal_url
        try:
            r = requests.get(url, headers=cls._default_headers, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            elex_dropdown = soup.find("select", {"name": "election"})
            
            if elex_dropdown is None:
                raise ParseError("Could not find election dropdown on page")
                
            elections_list = elex_dropdown.findAll("option")
            for election in elections_list[1:]:
                elections.update({election.text: election['value']})

            return elections
        except requests.RequestException as e:
            logger.error(f"Failed to fetch election IDs: {e}")
            raise HTTPError(f"Failed to fetch election IDs: {e}") from e
        except (AttributeError, KeyError) as e:
            logger.error(f"Failed to parse election IDs: {e}")
            raise ParseError(f"Failed to parse election IDs: {e}") from e

    @classmethod
    def download_active_committees(cls, filepath: Optional[str] = None) -> str:
        """
        Download the list of active committees from the Florida SOS website.
        
        This downloads the official extract of all active committees provided by
        the state. The data is returned as tab-delimited and converted to CSV format.
        
        Args:
            filepath: Optional filepath to save the CSV. If not provided, generates
                     a filename with timestamp (e.g., `active_committees_20240115_143022.csv`)
        
        Returns:
            Path to the saved CSV file
            
        Raises:
            HTTPError: If the request fails
            IOError: If the file cannot be written
            ParseError: If the data cannot be parsed
        """
        url = "https://dos.elections.myflorida.com/committees/extractComList.asp"
        
        headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://dos.elections.myflorida.com",
            "referer": "https://dos.elections.myflorida.com/committees/downloadcomlist.asp",
        }
        
        data = {"FormSubmit": "Download"}
        
        try:
            r = requests.post(url, headers=headers, data=data, timeout=60)
            r.raise_for_status()
            
            # Generate filename if not provided
            if filepath is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = f"active_committees_{timestamp}.csv"
            
            # Parse tab-delimited data and convert to CSV
            try:
                # Read as text and parse tab-delimited
                reader = csv.DictReader(
                    io.StringIO(r.text),
                    delimiter='\t',
                    quoting=csv.QUOTE_NONE
                )
                
                # Get fieldnames from the reader
                fieldnames = reader.fieldnames
                if fieldnames is None:
                    raise ParseError("Could not read column headers from downloaded file")
                
                # Read all rows
                rows = list(reader)
                
                # Write as proper CSV (comma-delimited)
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                
                logger.info(f"Downloaded and converted {len(rows)} active committees to {filepath}")
                return filepath
                
            except (csv.Error, ValueError) as e:
                logger.error(f"Failed to parse tab-delimited data: {e}")
                raise ParseError(f"Failed to parse downloaded data: {e}") from e
            
        except requests.RequestException as e:
            logger.error(f"Failed to download active committees: {e}")
            raise HTTPError(f"Failed to download active committees: {e}") from e
        except IOError as e:
            logger.error(f"Failed to save active committees file: {e}")
            raise IOError(f"Failed to save active committees file: {e}") from e

    def _update_payload(self, kwargs: Dict[str, Any]) -> None:
        """
        Update the payload sent to the campaign finance site based on kwargs.
        
        Args:
            kwargs: Dictionary of search parameters
        """
        if "candidate_first" in kwargs:
            self.payload["CanFName"] = kwargs["candidate_first"]
            self.payload["election"] = "All"

        if "candidate_last" in kwargs:
            self.payload["CanLName"] = kwargs["candidate_last"]
            self.payload["election"] = "All"

        if "committee_name" in kwargs:
            self.payload["ComName"] = kwargs["committee_name"]
            self.payload["ComNameSrch"] = 1
            self.payload["namesearch"] = 1
            self.payload["office"] = "All"
            self.payload["election"] = "All"

        if "from_date" in kwargs:
            self.payload["cdatefrom"] = kwargs["from_date"]
            self.payload["election"] = "All"

        if "to_date" in kwargs:
            self.payload["cdateto"] = kwargs["to_date"]
            self.payload["election"] = "All"

        if "all_time" in kwargs and kwargs["all_time"]:
            self.payload["election"] = "All"

        if "election_id" in kwargs:
            self.payload["election"] = kwargs["election_id"]

        if "contributor_first" in kwargs:
            self.payload["cfname"] = kwargs["contributor_first"]

        if "contributor_last" in kwargs:
            self.payload["clname"] = kwargs["contributor_last"]
            self.payload["namesearch"] = 1


    @classmethod
    def toDate(cls, text: str) -> str:
        """
        Convert a date string to ISO format.
        
        Args:
            text: Date string in MM/DD/YYYY format
            
        Returns:
            ISO format date string (YYYY-MM-DD) or empty string if parsing fails
        """
        text = text.strip()

        try:
            dt = datetime.strptime(text, cls.date_format)
            return dt.date().isoformat()
        except ValueError:
            logger.warning(f"Could not parse date: {text}")
            return ''

    def _generate_filename(self, filepath: Optional[str] = None) -> str:
        """
        Generate a filename for saving results.
        
        Args:
            filepath: Optional custom filepath. If provided, uses this instead.
            
        Returns:
            Generated filepath
        """
        if filepath:
            return filepath
        
        # Generate filename based on result type and timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result_type = getattr(self, 'result_type', 'results')
        filename = f"{result_type}_{timestamp}.csv"
        return filename

    def save(self, filepath: Optional[str] = None) -> str:
        """
        Save results to a CSV file.
        
        Args:
            filepath: Optional filepath. If not provided, generates a filename with timestamp.
            
        Returns:
            Path to the saved file
            
        Raises:
            ValueError: If results are not available or empty
            IOError: If file cannot be written
        """
        if not hasattr(self, 'results') or self.results is None:
            raise ValueError("No results available to save. Run the scraper first.")
        
        if not self.results:
            raise ValueError("Results list is empty. Nothing to save.")
        
        filepath = self._generate_filename(filepath)
        
        try:
            # Get all unique keys from all result dictionaries
            fieldnames = set()
            for result in self.results:
                fieldnames.update(result.keys())
            fieldnames = sorted(list(fieldnames))
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.results)
            
            logger.info(f"Saved {len(self.results)} results to {filepath}")
            return filepath
        except IOError as e:
            logger.error(f"Failed to save CSV file: {e}")
            raise IOError(f"Failed to save CSV file: {e}") from e