from .base import SunScraper
from .utils import get_name, get_party, strip_spaces

import requests
from bs4 import BeautifulSoup

class CandidateScraper(SunScraper):
    """ Returns a candidate """

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

    def __init__(self, candidate_first='', candidate_last='', result_type=''):
        """
        Keyword arguments:
        ------------------
        * candidate_first - Candidate first name
        * candidate_last - Candidate last name
        * result_type - contributions, expenditures, other or transfers

        """
        self.candidate_first = candidate_first
        self.candidate_last = candidate_last
        self.account_num = self._get_account_num()
        self.candidate_details = self._get_details()
        self._update_payload(committee_name)
        self.results = self._parse_results()

    def _get_account_num(self):
        candidate_search_url = "https://dos.elections.myflorida.com/candidates/canlist.asp"

        search_payload = {
            "elecid": "20201103-GEN",
            "OfficeGroup": "ALL",
            "StatusCode": "ALX",
            "OfficeCode": "ALL",
            "CountyCode": "ALL",
            "CanName": self.candidate_last,
            "OrderBy": "NAM",
        }

        r = requests.get(
                candidate_search_url,
                params=search_payload,
                allow_redirects=True
                )

        return self.search_candidates(r)

    def search_candidates(self, response):
        pass

    # TODO:
    # Search the account page for the candidate
    # Collect restu records
