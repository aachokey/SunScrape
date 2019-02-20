from .base import SunScraper
from .utils import get_name, get_party, strip_spaces


class ExpenditureScraper(SunScraper):

    """ Returns a list of expenses """

    result_type = 'expenditures'
    url = "https://dos.elections.myflorida.com/cgi-bin/expend.exe"
    portal_url = "https://dos.elections.myflorida.com/campaign-finance/expenditures/"
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
        "cdollar_maximim": "",
        "rowlimit": "",
        "csort1": "DAT",
        "csort2": "CAN",
        "cdatefrom": "",
        "cdateto": "",
        "queryformat": 2
    }

    def __init__(self, **kwargs):
        """
        Keyword arguments:
        ------------------
        * candidate_first - Candidate first name
        * candidate_last - Candidate last name
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

        """ Clean up the returned results. """

        clean_data = []

        for expense in data:

            cleaned_expense = {}
            cleaned_expense['candidate'] = get_name(expense['Candidate/Committee'])
            cleaned_expense['candidate_party'] = get_party(expense['Candidate/Committee'])
            cleaned_expense['date'] = self.toDate(expense['Date'])
            cleaned_expense['amount'] = expense['Amount']
            cleaned_expense['recipient'] = strip_spaces(expense['Payee Name'])
            cleaned_expense['recipient_address'] = strip_spaces(expense['Address'])
            cleaned_expense['recipient_address2'] = strip_spaces(expense['City State Zip'])
            cleaned_expense['purpose'] = strip_spaces(expense['Purpose'])
            cleaned_expense['type'] = strip_spaces(expense['Type'])

            clean_data.append(cleaned_expense)

        return clean_data
