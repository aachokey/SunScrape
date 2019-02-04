from .base import SunScraper
from .utils import get_name, get_party, strip_spaces


class ContributionScraper(SunScraper):

    """ Returns a list of contributions """

    result_type = 'contributions'
    url = "http://dos.elections.myflorida.com/cgi-bin/contrib.exe"
    portal_url = "https://dos.elections.myflorida.com/campaign-finance/contributions/"
    payload = {
        "election": "20181106-GEN",
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
        "rowlimit": 20,
        "csort1": "NAM",
        "csort2": "CAN",
        "queryformat": 2
    }

    def __init__(self, **kwargs):
        """
        Keyword arguments:
        ------------------
        * candidate_first - Candidate first name
        * candidate_last - Candidate last name
        * from_date - Contributions start date (MM/DD/YYYY)
        * to_date - Contributions end date (MM/DD/YYYY)
        * committee_name - Committee name, or partial name
        * election_id - See base._get_election_ids
        * all_time - True or False, returns results beyond current election
        """

        self._update_payload(kwargs)
        self.results = self._parse_results(self.request(
                                                self.url,
                                                self.payload)
                                           )

    def _parse_results(self, data):
        """
        Clean up the returned results.
        """

        clean_data = []

        for contrib in data:

            cleaned_contrib = {}
            cleaned_contrib['candidate'] = get_name(contrib['Candidate/Committee'])
            cleaned_contrib['candidate_party'] = get_party(contrib['Candidate/Committee'])
            cleaned_contrib['date'] = self.toDate(contrib['Date'])
            cleaned_contrib['amount'] = contrib['Amount']
            cleaned_contrib['type'] = strip_spaces(contrib['Typ'])
            cleaned_contrib['contributor_name'] = strip_spaces(contrib['Contributor Name'])
            cleaned_contrib['contributor_address'] = strip_spaces(contrib['Address'])
            cleaned_contrib['contributor_address2'] = strip_spaces(contrib['City State Zip'])
            cleaned_contrib['contributor_occupation'] = strip_spaces(contrib['Occupation'])
            cleaned_contrib['inkind_description'] = strip_spaces(contrib['Inkind Desc'])

            clean_data.append(cleaned_contrib)

        return clean_data
