"""Scraper for campaign contributions."""

import logging
from typing import Dict, Any, List

from .base import SunScraper
from .candidate_lookup import CandidateLookup
from .committee_lookup import CommitteeLookup
from .utils import get_name, get_party, strip_spaces


class ContributionScraper(SunScraper):
    """Returns a list of contributions."""

    result_type = 'contributions'
    url = "http://dos.elections.myflorida.com/cgi-bin/contrib.exe"
    portal_url = "https://dos.elections.myflorida.com/campaign-finance/contributions/"
    payload = {
        "election": "All",
        "search_on": 1,
        "CanFName": "",
        "CanLName": "",
        "CanNameSrch": 2,
        "office": "All",
        "cdistrict": "",
        "cgroup": "",
        "party": "All",
        "ComName": "",
        "ComNameSrch": 2,
        "committee": "All",
        "cfname": "",
        "clname": "",
        "namesearch": 2,
        "ccity": "",
        "cstate": "",
        "czipcode": "",
        "coccupation": "",
        "cdollar_minimum": "",
        "cdollar_maximum": "",
        "rowlimit": "",
        "csort1": "NAM",
        "csort2": "CAN",
        "queryformat": 2
    }

    def __init__(
        self,
        enrich: bool = True,
        **kwargs: Any
    ) -> None:
        """
        Initialize the contribution scraper.

        Keyword arguments:
        ------------------
        * enrich - Whether to automatically enrich results with candidate data (default: True)
        * candidate_first - Candidate first name
        * candidate_last - Candidate last name
        * from_date - Contributions start date (MM/DD/YYYY)
        * to_date - Contributions end date (MM/DD/YYYY)
        * committee_name - Committee name, or partial name
        * election_id - See base.get_election_ids
        * all_time - True or False, returns results beyond current election
        """
        self._update_payload(kwargs)
        data = self.request(self.url, self.payload)
        if data is None:
            self.results: List[Dict[str, Any]] = []
        else:
            self.results = self._parse_results(data)
        
        # Automatically enrich with candidate and committee data by default
        if enrich:
            logger = logging.getLogger(__name__)
            logger.info("Enriching contribution results with candidate and committee data...")
            logger.info("  Loading candidates and committees...")
            candidate_lookup = CandidateLookup()
            committee_lookup = CommitteeLookup()
            self.results = candidate_lookup.merge_with_transactions(
                transactions=self.results,
                name_field='recipient',
                party_field='recipient_party',
                committee_lookup=committee_lookup
            )
            logger.info("✓ Contribution enrichment complete")

    def _parse_results(self, data: Any) -> List[Dict[str, Any]]:
        """
        Clean up the returned results.
        
        Args:
            data: CSV DictReader iterator
            
        Returns:
            List of cleaned contribution dictionaries
        """
        clean_data = []

        for contrib in data:
            cleaned_contrib: Dict[str, Any] = {}
            cleaned_contrib['recipient'] = get_name(
                contrib['Candidate/Committee'])
            cleaned_contrib['recipient_party'] = get_party(
                contrib['Candidate/Committee'])
            cleaned_contrib['date'] = self.toDate(contrib['Date'])
            cleaned_contrib['amount'] = float(contrib['Amount'])
            cleaned_contrib['type'] = strip_spaces(contrib['Typ'])
            cleaned_contrib['contributor_name'] = strip_spaces(
                contrib['Contributor Name'])
            cleaned_contrib['contributor_address'] = strip_spaces(
                contrib['Address'])
            cleaned_contrib['contributor_address2'] = strip_spaces(
                contrib['City State Zip'])
            cleaned_contrib['contributor_occupation'] = strip_spaces(
                contrib['Occupation'])
            cleaned_contrib['inkind_description'] = strip_spaces(
                contrib['Inkind Desc'])

            clean_data.append(cleaned_contrib)

        return clean_data
