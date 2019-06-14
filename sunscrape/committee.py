from .utils import strip_breaks, strip_spaces, toDate

import io
import csv
import difflib
import requests
from bs4 import BeautifulSoup


class CommitteeScraper():
    """ Returns a committee """

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

    def __init__(self, committee_name='', result_type=''):
        """
        Keyword arguments:
        ------------------
        * committee_name - Committee name, or partial name
        * result_type - contributions, expenditures, other or transfers

        """
        self.committee_name = committee_name
        self.result_type = result_type
        self.account_num = self._get_account_num()
        self.committee_details = self._get_details()
        self._update_payload(committee_name)
        self.results = self._parse_results()

    def _get_account_num(self):
        committee_search_url = "https://dos.elections.myflorida.com/committees/ComLkupByName.asp"

        search_payload = {
            "searchtype": 1,
            "comName": self.committee_name[:50],
            "LkupTypeName": "L",
            "NameSearchBtn": "Search by Name"
        }

        r = requests.get(
                committee_search_url,
                params=search_payload,
                allow_redirects=True
                )

        return self.search_accounts(r)

    def search_accounts(self, response):
        # Parse the table of matching committee names
        try:
            soup = BeautifulSoup(response.content, "html.parser")
            committee_table = soup.findAll("table")[2]
            rows = committee_table.findAll('tr')
            # Add them to a list
            committee_name_list = []
            # Store names and account numbers
            committees = {}
            for committee in rows[1:]:
                cells = committee.findAll('td')
                name_cell = cells[0]
                name = name_cell.find('a').text.strip()
                url = name_cell.find('a')['href']
                account_num = url.split('=')[1]
                committee_name_list.append(name)
                committees.update({name: account_num})
            # Now see which committee matches best
            matching_committee = difflib.get_close_matches(self.committee_name,
                                                           committee_name_list)[0]
            return committees[matching_committee]
        except IndexError:
            print("Committee not found")

    def _update_payload(self, kwargs):
        """
        Update the payload sent to the campaign finance site based on kwargs.
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

    def _get_details(self):
        details_url = "https://dos.elections.myflorida.com/committees/ComDetail.asp?account={}".format(self.account_num)
        r = requests.get(details_url, allow_redirects=True)
        soup = BeautifulSoup(r.content, "html.parser")
        details_table = soup.find("table")
        rows = details_table.findAll('tr')
        details = {
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

    def request(self, url, payload):

        r = requests.get(url, params=payload, allow_redirects=True)
        if r.status_code == 200:
            reader = csv.DictReader(io.StringIO(r.text),
                                    delimiter='\t',
                                    quoting=csv.QUOTE_NONE)
            return reader

        else:
            print("====\nERROR: {0} response from server\n====".format(
                                                                r.status_code
                                                                ))

    def _parse_results(self):
        """
        Clean up the returned results.
        """

        data = self.request(self.url, self.payload)

        clean_data = []

        if self.result_type == 'contributions':
            for item in data:
                cleaned_item = {}
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
                cleaned_item = {}
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

        elif self.result_type == '':
            print('Error: No result type provided.')
