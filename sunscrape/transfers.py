"""Scraper for fund transfers."""

from typing import Dict, Any, List
from .base import SunScraper
from .utils import get_name, get_party, strip_spaces


class TransferScraper(SunScraper):
    """Returns a list of fund transfers."""

    result_type = "transfers"
    url = "https://dos.elections.myflorida.com/cgi-bin/FundXfers.exe"
    portal_url = "https://dos.elections.myflorida.com/campaign-finance/transfers/"
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
        "ccstate": "",
        "czipcode": "",
        "cpurpose": "",
        "cdollar_minimum": "",
        "cdollar_maximum": "",
        "rowlimit": "",
        "csort1": "DAT",
        "csort2": "CAN",
        "cdatefrom": "",
        "cdateto": "",
        "queryformat": 2
    }

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize the transfer scraper.

        Keyword arguments:
        ------------------
        * candidate_first - Candidate first name
        * candidate_last - Candidate last name
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

    def _parse_results(self, data: Any) -> List[Dict[str, Any]]:
        """
        Clean up the returned results.
        
        Args:
            data: CSV DictReader iterator
            
        Returns:
            List of cleaned transfer dictionaries
        """
        clean_data = []

        for transfer in data:
            cleaned_transfer: Dict[str, Any] = {}
            cleaned_transfer['transfer_from'] = get_name(transfer['Candidate/Committee'])
            cleaned_transfer['transfer_from_party'] = get_party(transfer['Candidate/Committee'])
            cleaned_transfer['date'] = self.toDate(transfer['Date'])
            cleaned_transfer['amount'] = float(transfer['Amount'])
            cleaned_transfer['transfer_to'] = strip_spaces(transfer['Funds Transferred To'])
            cleaned_transfer['transfer_from_address'] = strip_spaces(transfer['Address'])
            cleaned_transfer['transfer_from_address2'] = strip_spaces(transfer['City State Zip'])
            cleaned_transfer['account_type'] = strip_spaces(transfer['Nature Of Account'])
            cleaned_transfer['transfer_type'] = strip_spaces(transfer['Type'])

            clean_data.append(cleaned_transfer)

        return clean_data
