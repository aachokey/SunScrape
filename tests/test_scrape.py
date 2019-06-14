from sunscrape.transfers import TransferScraper
from sunscrape.expenditures import ExpenditureScraper
from sunscrape.contributions import ContributionScraper
from sunscrape.committee import CommitteeScraper

import pytest


@pytest.mark.parametrize('first_name,last_name', [
    ('ron', 'desantis'),
    ('andrew', 'gillum')
])
def test_contrib_scrape(first_name, last_name):

    scraper = ContributionScraper(candidate_first=first_name,
                                  candidate_last=last_name)
    print(scraper.results)


@pytest.mark.parametrize('first_name,last_name', [
    ('ron', 'desantis'),
    ('andrew', 'gillum')
])
def test_expense_scrape(first_name, last_name):

    scraper = ExpenditureScraper(candidate_first=first_name,
                                 candidate_last=last_name)
    print(scraper.results)


@pytest.mark.parametrize('first_name,last_name', [
    ('ron', 'desantis'),
    ('andrew', 'gillum')
])
def test_transfer_scrape(first_name, last_name):

    scraper = TransferScraper(candidate_first=first_name,
                              candidate_last=last_name)
    print(scraper.results)


@pytest.mark.parametrize('committee_name', [
    "Florida Citizen Voters",
    "2020 Vision Florida"
])
def test_committee_scrape(committee_name):

    scraper = CommitteeScraper(committee_name=committee_name)
    print(scraper.results)
