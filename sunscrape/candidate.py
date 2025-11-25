"""Scraper for candidate campaign finance data."""

import io
import csv
import logging
import os
from typing import Optional, List, Dict
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from .base import SunScraper, HTTPError, ParseError

logger = logging.getLogger(__name__)


class CandidateScraper(SunScraper):
    """
    Returns campaign finance data for a candidate.
    
    Note: This class is not yet fully implemented and will raise NotImplementedError.
    """

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

    def __init__(self, candidate_first: str = '', candidate_last: str = '', result_type: str = '') -> None:
        """
        Initialize the candidate scraper.

        Args:
            candidate_first: Candidate first name
            candidate_last: Candidate last name
            result_type: One of 'contributions', 'expenditures', 'other', or 'transfers'

        Raises:
            NotImplementedError: This scraper is not yet fully implemented
        """
        self.candidate_first = candidate_first
        self.candidate_last = candidate_last
        self.result_type = result_type
        raise NotImplementedError(
            "CandidateScraper is not yet fully implemented. "
            "Use ContributionScraper, ExpenditureScraper, or TransferScraper "
            "with candidate_first and candidate_last parameters instead."
        )

    @classmethod
    def get_available_elections(cls) -> List[Dict[str, str]]:
        """
        Get list of available elections from the candidate download page.
        
        Returns a list of dictionaries with election information that can be used
        with download().
        
        Returns:
            List of dictionaries with 'value' and 'text' keys for each election
            
        Raises:
            HTTPError: If the request fails
            ParseError: If the page structure is unexpected
        """
        url = "https://dos.elections.myflorida.com/candidates/downloadcanlist.asp"
        
        headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
        }
        
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
            
            # Find the election year dropdown
            election_select = soup.find("select", {"name": "elecID"})
            if election_select is None:
                raise ParseError("Could not find election dropdown on candidate download page")
            
            elections = []
            options = election_select.findAll("option")
            for option in options:
                value = option.get('value', '')
                text = option.text.strip()
                if value and text:  # Skip empty options
                    elections.append({
                        'value': value,
                        'text': text
                    })
            
            logger.info(f"Found {len(elections)} available elections")
            return elections
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch candidate elections: {e}")
            raise HTTPError(f"Failed to fetch candidate elections: {e}") from e
        except (AttributeError, KeyError) as e:
            logger.error(f"Failed to parse candidate elections: {e}")
            raise ParseError(f"Failed to parse candidate elections: {e}") from e

    @classmethod
    def download(
        cls,
        election_year: Optional[str] = None,
        state_office: str = "ALL",
        status: str = "ALL",
        candidate_type: str = "State Candidates",
        filepath: Optional[str] = None
    ) -> str:
        """
        Download candidate list from the Florida SOS website.
        
        This downloads the official candidate extract for a specific election with
        optional filters. The data is returned as tab-delimited and converted to CSV format.
        
        Args:
            election_year: Election year/ID (e.g., '20201103-GEN'). If None, uses first available.
            state_office: State office filter. Use 'ALL' for all offices, or specific office codes.
                         Default: 'ALL'
            status: Candidate status filter. Use 'ALL' for all statuses, or specific status codes.
                   Default: 'ALL'
            candidate_type: Type of candidates. Options: 'State Candidates' (maps to 'STA'),
                           'Local Candidates' (maps to 'LOC'). Default: 'State Candidates'
            filepath: Optional filepath to save the CSV. If not provided, generates
                     a filename with election info and timestamp.
        
        Returns:
            Path to the saved CSV file
            
        Raises:
            HTTPError: If the request fails
            IOError: If the file cannot be written
            ParseError: If the data cannot be parsed
            ValueError: If invalid parameters are provided
        """
        url = "https://dos.elections.myflorida.com/candidates/extractCanList.asp"
        
        headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://dos.elections.myflorida.com",
            "referer": "https://dos.elections.myflorida.com/candidates/downloadcanlist.asp",
        }
        
        # Build form data - field names and values must match the actual form
        data = {
            "FormSubmit": "Download Candidate List"
        }
        
        # Add election year if provided (form uses elecID)
        if election_year:
            data["elecID"] = election_year
        else:
            # Get first available election if not specified
            elections = cls.get_available_elections()
            if elections:
                data["elecID"] = elections[0]['value']
                logger.info(f"No election specified, using: {elections[0]['text']}")
            else:
                raise ValueError("No elections available and none specified")
        
        # Add filters - convert to form field names and values
        # office field: "All" or specific office codes
        if state_office.upper() == "ALL":
            data["office"] = "All"
        else:
            # Map state office names to codes if needed
            # For now, pass through as-is (may need mapping)
            data["office"] = state_office
        
        # status field: "All" or specific status codes
        if status.upper() == "ALL":
            data["status"] = "All"
        else:
            data["status"] = status
        
        # cantype field: "STA" for State Candidates, "LOC" for Local Candidates
        if candidate_type == "State Candidates":
            data["cantype"] = "STA"
        elif candidate_type == "Local Candidates":
            data["cantype"] = "LOC"
        else:
            data["cantype"] = candidate_type
        
        # Log the form data being sent for debugging
        logger.debug(f"Sending form data: {data}")
        logger.info(f"Downloading candidates for election: {election_year or 'default'}")
        
        try:
            r = requests.post(url, headers=headers, data=data, timeout=60)
            r.raise_for_status()
            
            # Log response info for debugging
            logger.debug(f"Response status: {r.status_code}, Content-Type: {r.headers.get('content-type', 'unknown')}")
            logger.debug(f"Response length: {len(r.text)} bytes")
            
            # Check if response is HTML (error page) instead of data
            if r.text.strip().startswith('<') or 'html' in r.headers.get('content-type', '').lower():
                # Response is HTML, likely an error or empty result
                logger.warning("Response appears to be HTML, not tab-delimited data")
                # Try to extract error message if present
                soup = BeautifulSoup(r.text, "html.parser")
                error_msg = soup.find('div', class_='error') or soup.find('p', class_='error')
                if error_msg:
                    raise ParseError(f"Server returned error: {error_msg.text.strip()}")
                else:
                    raise ParseError("Server returned HTML instead of data. No candidates found for the selected criteria.")
            
            # Check response encoding - might need to handle differently
            if r.encoding:
                logger.debug(f"Response encoding: {r.encoding}")
            
            # Save raw response for debugging (optional - can be removed later)
            raw_filepath = filepath.replace('.csv', '_raw.txt') if filepath else 'candidates_raw.txt'
            try:
                with open(raw_filepath, 'wb') as f:
                    f.write(r.content)
                logger.debug(f"Saved raw response to {raw_filepath} for debugging")
            except Exception as e:
                logger.debug(f"Could not save raw response: {e}")
            
            # Generate filename if not provided
            if filepath is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_election = election_year or data.get("elecID", "unknown")
                safe_election = safe_election.replace('/', '_').replace(' ', '_')[:30]
                filepath = f"candidates_{safe_election}_{timestamp}.csv"
            
            # Parse tab-delimited data and convert to CSV
            try:
                # Try to decode the response content properly
                # First try with the detected encoding, fallback to utf-8, then latin-1
                try:
                    if r.encoding:
                        response_text = r.content.decode(r.encoding)
                    else:
                        response_text = r.content.decode('utf-8')
                except (UnicodeDecodeError, LookupError):
                    try:
                        response_text = r.content.decode('utf-8', errors='replace')
                    except:
                        response_text = r.content.decode('latin-1', errors='replace')
                
                # Log some info about the response
                logger.debug(f"Response text length: {len(response_text)}")
                lines = response_text.splitlines()
                logger.debug(f"Number of lines: {len(lines)}")
                if len(lines) > 0:
                    logger.debug(f"First line (header): {lines[0][:200]}")
                if len(lines) > 1:
                    logger.debug(f"Second line (first data): {lines[1][:200]}")
                if len(lines) > 2:
                    logger.debug(f"Third line: {lines[2][:200]}")
                
                # Read as text and parse tab-delimited
                # Use strict=False to handle any encoding issues
                reader = csv.DictReader(
                    io.StringIO(response_text),
                    delimiter='\t',
                    quoting=csv.QUOTE_NONE,
                    strict=False
                )
                
                # Get fieldnames from the reader
                fieldnames = reader.fieldnames
                if fieldnames is None:
                    raise ParseError("Could not read column headers from downloaded file")
                
                logger.debug(f"Fieldnames: {fieldnames}")
                
                # Read all rows - be more explicit about reading
                rows = []
                row_count = 0
                for row in reader:
                    # Skip completely empty rows
                    if any(value.strip() for value in row.values() if value):
                        rows.append(row)
                        row_count += 1
                        if row_count <= 3:
                            logger.debug(f"Row {row_count}: {dict(list(row.items())[:5])}...")
                
                logger.info(f"Parsed {len(rows)} candidate rows from response")
                
                if len(rows) == 0:
                    logger.warning("Downloaded file contains no candidate data (only headers)")
                    # Check if response has data but we're not parsing it correctly
                    lines = response_text.splitlines()
                    if len(lines) > 1:
                        logger.warning(f"Response has {len(lines)} lines but parsed 0 rows. First data line: {lines[1][:200] if len(lines) > 1 else 'N/A'}")
                
                # Write as proper CSV (comma-delimited)
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                
                logger.info(f"Downloaded and converted {len(rows)} candidates to {filepath}")
                return filepath
                
            except (csv.Error, ValueError) as e:
                logger.error(f"Failed to parse tab-delimited data: {e}")
                logger.error(f"Response text sample: {r.text[:1000]}")
                raise ParseError(f"Failed to parse downloaded data: {e}") from e
            
        except requests.RequestException as e:
            logger.error(f"Failed to download candidates: {e}")
            raise HTTPError(f"Failed to download candidates: {e}") from e
        except IOError as e:
            logger.error(f"Failed to save candidates file: {e}")
            raise IOError(f"Failed to save candidates file: {e}") from e

    @classmethod
    def download_all(
        cls,
        state_office: str = "ALL",
        status: str = "ALL",
        candidate_type: str = "State Candidates",
        filepath: Optional[str] = None,
        election_ids: Optional[List[str]] = None
    ) -> str:
        """
        Download candidates from all available elections and combine into a single file.
        
        This method downloads candidate lists for multiple elections and combines them
        into a single CSV file. Useful for getting a comprehensive list of all candidates.
        
        Args:
            state_office: State office filter. Use 'ALL' for all offices. Default: 'ALL'
            status: Candidate status filter. Use 'ALL' for all statuses. Default: 'ALL'
            candidate_type: Type of candidates. Options: 'State Candidates', 'Local Candidates'.
                          Default: 'State Candidates'
            filepath: Optional filepath to save the combined CSV. If not provided, generates
                     a filename with timestamp.
            election_ids: Optional list of specific election IDs to download. If None,
                         downloads from all available elections.
        
        Returns:
            Path to the saved CSV file with all candidates combined
            
        Raises:
            HTTPError: If any request fails
            IOError: If the file cannot be written
            ParseError: If any data cannot be parsed
        """
        # Get elections to download
        if election_ids is None:
            elections = cls.get_available_elections()
            election_ids = [e['value'] for e in elections]
            logger.info(f"Downloading candidates from {len(election_ids)} elections")
        else:
            logger.info(f"Downloading candidates from {len(election_ids)} specified elections")
        
        all_candidates = []
        all_fieldnames = set()
        successful_downloads = 0
        
        # Download from each election
        for election_id in election_ids:
            try:
                logger.info(f"Downloading candidates for election: {election_id}")
                # Download to temporary file
                temp_file = cls.download(
                    election_year=election_id,
                    state_office=state_office,
                    status=status,
                    candidate_type=candidate_type,
                    filepath=None  # Auto-generate temp filename
                )
                
                # Read the downloaded file
                with open(temp_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    if fieldnames:
                        all_fieldnames.update(fieldnames)
                    
                    for row in reader:
                        # Add election ID to each row for tracking
                        row['_source_election'] = election_id
                        all_candidates.append(row)
                
                successful_downloads += 1
                logger.info(f"Downloaded {len([r for r in all_candidates if r.get('_source_election') == election_id])} candidates from {election_id}")
                
                # Clean up temp file
                try:
                    os.remove(temp_file)
                except:
                    pass
                    
            except Exception as e:
                logger.warning(f"Failed to download candidates for election {election_id}: {e}")
                continue
        
        if len(all_candidates) == 0:
            raise ParseError("No candidates were downloaded from any election")
        
        # Generate filename if not provided
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f"candidates_all_{timestamp}.csv"
        
        # Write combined data
        # Build fieldnames list - include _source_election if we added it
        fieldnames_list = sorted(list(all_fieldnames))
        # Make sure _source_election is included and at the end
        if '_source_election' not in fieldnames_list:
            fieldnames_list.append('_source_election')
        else:
            # Move it to the end if it's already there
            fieldnames_list.remove('_source_election')
            fieldnames_list.append('_source_election')
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames_list)
            writer.writeheader()
            writer.writerows(all_candidates)
        
        logger.info(f"Combined {len(all_candidates)} candidates from {successful_downloads} elections into {filepath}")
        return filepath
