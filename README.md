# SunScrape

[![Build Status](https://travis-ci.com/SunSentinel/SunScrape.svg?branch=master)](https://travis-ci.com/SunSentinel/SunScrape)

A Python library that scrapes and parses political entity and campaign finance data from the [Florida Secretary of State's website](https://dos.myflorida.com/elections/candidates-committees/campaign-finance/campaign-finance-database/).

## Features

- Scrape campaign contributions, expenditures, and fund transfers
- Search by candidate, committee, date range, or election
- Utility methods for getting active candidate and committee lists
- Python 3.7+ support

## Installation

This package isn't on PyPI yet, so install from the repo:

```bash
pip install git+https://github.com/SunSentinel/SunScrape.git
```

For local development:

```bash
git clone https://github.com/SunSentinel/SunScrape.git
cd SunScrape
pip install -e .
```

## Requirements

- Python 3.7 or higher
- `beautifulsoup4>=4.9.0`
- `requests>=2.25.0`

## Usage

SunScrape makes it possible to grab campaign finance data in bulk in a usable, machine-readable format. This library provides a way to search Florida's campaign finance portal either by a particular entity or a specific filing type.

### By Filing Type

You can search through all contributions, expenses, or fund transfers reported to the SOS's office. Additional search terms can be passed to these objects:

#### Search Parameters

* `candidate_first` - Candidate first name
* `candidate_last` - Candidate last name
* `from_date` - Start date (MM/DD/YYYY)
* `to_date` - End date (MM/DD/YYYY)
* `committee_name` - Committee name, or partial name
* `election_id` - See [Election IDs](#election-ids)
* `all_time` - `True` or `False`, returns results for all years
* `contributor_first` - Contributor first name (contributions only)
* `contributor_last` - Contributor last name (contributions only)

#### Contributions

```python
from sunscrape import ContributionScraper

# Search by candidate
scraper = ContributionScraper(
    candidate_first='Ron',
    candidate_last='DeSantis'
)
print(scraper.results)

# Search by date range
scraper = ContributionScraper(
    from_date='01/01/2021',
    to_date='12/31/2021'
)
print(scraper.results)

# Search by committee
scraper = ContributionScraper(
    committee_name='Florida Citizen Voters'
)
print(scraper.results)
```

**Example Output:**
```python
[
    {
        'recipient': 'DeSantis, Ron',
        'recipient_party': 'Republican',
        'date': '2018-07-18',
        'amount': 3000.0,
        'type': 'CHE',
        'contributor_name': '1188 PARTNERS, LLC',
        'contributor_address': '2141 ALAQUA DRIVE',
        'contributor_address2': 'LONGWOOD, FL 32779',
        'contributor_occupation': 'INSURANCE',
        'inkind_description': ''
    },
    ...
]
```

#### Expenditures

```python
from sunscrape import ExpenditureScraper

# Search by candidate
scraper = ExpenditureScraper(
    candidate_first='Ron',
    candidate_last='DeSantis'
)
print(scraper.results)

# Search by committee
scraper = ExpenditureScraper(
    committee_name='Florida Citizen Voters'
)
print(scraper.results)
```

**Example Output:**
```python
[
    {
        'spender': 'DeSantis, Ron',
        'spender_party': 'Republican',
        'date': '2018-08-15',
        'amount': 5000.0,
        'recipient': 'ABC Consulting',
        'recipient_address': '123 Main St',
        'recipient_address2': 'Tallahassee, FL 32301',
        'purpose': 'Campaign Consulting',
        'type': 'EXP'
    },
    ...
]
```

#### Transfers

```python
from sunscrape import TransferScraper

# Search by candidate
scraper = TransferScraper(
    candidate_first='Ron',
    candidate_last='DeSantis'
)
print(scraper.results)

# Search by committee
scraper = TransferScraper(
    committee_name='Florida Citizen Voters'
)
print(scraper.results)
```

**Example Output:**
```python
[
    {
        'transfer_from': 'DeSantis, Ron',
        'transfer_from_party': 'Republican',
        'date': '2018-09-01',
        'amount': 10000.0,
        'transfer_to': 'Campaign Account',
        'transfer_from_address': '123 Main St',
        'transfer_from_address2': 'Tallahassee, FL 32301',
        'account_type': 'Checking',
        'transfer_type': 'TRF'
    },
    ...
]
```

### By Entity

#### Committee

Get detailed information and finance records for a specific committee:

```python
from sunscrape import CommitteeScraper

# Get contributions for a committee
scraper = CommitteeScraper(
    committee_name='Florida Citizen Voters',
    result_type='contributions'
)
print(scraper.results)
print(scraper.committee_details)

# Get expenditures for a committee
scraper = CommitteeScraper(
    committee_name='Florida Citizen Voters',
    result_type='expenditures'
)
print(scraper.results)
```

**Available result types:**
- `'contributions'` - Contribution records
- `'expenditures'` - Expenditure records
- `'other'` - Other financial records
- `'transfers'` - Fund transfer records

**Committee Details:**
The `committee_details` attribute contains:
- `type` - Committee type
- `status` - Registration status
- `address` - Committee address
- `phone` - Contact phone
- `chair` - Chairperson name
- `treasurer` - Treasurer name
- `registered_agent` - Registered agent
- `purpose` - Committee purpose
- `affiliates` - Affiliated entities

### Downloading Active Committees List

You can download the official list of all active committees directly from the state:

```python
from sunscrape import ContributionScraper

# Download with auto-generated filename
filepath = ContributionScraper.download_active_committees()
print(f"Downloaded to: {filepath}")

# Download with custom filename
filepath = ContributionScraper.download_active_committees('committees.csv')
print(f"Downloaded to: {filepath}")
```

This downloads the official extract provided by the Florida SOS website. The file is saved as CSV format.

You can also browse committees at: https://dos.elections.myflorida.com/committees/ComLkupByName.asp

### Downloading Candidate Lists

You can download official candidate lists for specific elections or all elections:

```python
from sunscrape import CandidateScraper

# Get available elections
elections = CandidateScraper.get_available_elections()
print(f"Found {len(elections)} elections")

# Download candidates for a specific election
filepath = CandidateScraper.download(
    election_year='20201103-GEN',  # Election ID
    state_office='ALL',             # or 'Federal Offices', 'Governor and Cabinet', etc.
    status='ALL',                  # or 'Active', 'Elected', 'Defeated', etc.
    candidate_type='State Candidates'  # or 'Local Candidates'
)
print(f"Downloaded to: {filepath}")

# Download candidates from ALL elections (combines into one file)
filepath = CandidateScraper.download_all(
    state_office='ALL',
    status='ALL',
    candidate_type='State Candidates'
)
print(f"Downloaded all candidates to: {filepath}")

# Download from specific elections only
filepath = CandidateScraper.download_all(
    election_ids=['20201103-GEN', '20221108-GEN'],
    state_office='ALL',
    status='ALL'
)
```

**Available Filters:**
- `election_year`: Election ID (e.g., '20201103-GEN'). If None, uses first available.
- `state_office`: 'ALL', 'Federal Offices', 'Governor and Cabinet', 'State Attorney / Public Defender', 'Senate and House', 'Judicial Offices', 'Special Districts'
- `status`: 'ALL', 'Active', 'Defeated', 'Elected', 'Qualified', 'Withdrawn', 'Did Not Qualify'
- `candidate_type`: 'State Candidates' or 'Local Candidates'

**Methods:**
- `download()` - Download candidates for a single election
- `download_all()` - Download candidates from all (or specified) elections and combine into one file

The downloaded files are automatically converted from tab-delimited to CSV format. The `download_all()` method adds a `_source_election` column to track which election each candidate came from.


### Election IDs

The library allows finance records searches by election, but you need the election ID used by the Secretary of State. You can find these with the `get_election_ids()` method:

```python
from sunscrape import ContributionScraper

# Get available elections
elections = ContributionScraper.get_election_ids()
print(elections)

# Use a specific election ID
scraper = ContributionScraper(election_id='20201103-GEN')
print(scraper.results)
```

### Error Handling

The library provides custom exceptions for better error handling:

```python
from sunscrape import ContributionScraper, HTTPError, ParseError, SunScrapeError

try:
    scraper = ContributionScraper(
        candidate_first='Ron',
        candidate_last='DeSantis'
    )
    print(scraper.results)
except HTTPError as e:
    print(f"HTTP error occurred: {e}")
except ParseError as e:
    print(f"Parsing error occurred: {e}")
except SunScrapeError as e:
    print(f"SunScrape error occurred: {e}")
```

**Exception Classes:**
- `SunScrapeError` - Base exception for all SunScrape errors
- `HTTPError` - Raised when HTTP requests fail
- `ParseError` - Raised when parsing data fails

### Saving Results

All scrapers support saving results to CSV files:

```python
from sunscrape import ContributionScraper

scraper = ContributionScraper(
    candidate_first='Ron',
    candidate_last='DeSantis'
)

# Save with auto-generated filename
csv_file = scraper.save()
print(f"Saved to: {csv_file}")

# Save with custom filename
scraper.save('my_data.csv')
```

**Save Method:**
- `save(filepath=None)` - Save results as CSV. If no filepath is provided, files are automatically named with a timestamp (e.g., `contributions_20240115_143022.csv`)

**Committee Details:**
For `CommitteeScraper`, you can also save committee details separately:

```python
from sunscrape import CommitteeScraper

scraper = CommitteeScraper(
    committee_name='Florida Citizen Voters',
    result_type='contributions'
)

# Save results
scraper.save('committee_contributions.csv')

# Save committee details
scraper.save_committee_details('committee_info.csv')
```


## Known Issues

### Searching by Date

The SOS's expenditure and fund transfer search portals fail when specifying a date, so date filtering is not available for `ExpenditureScraper` and `TransferScraper` objects. Date filtering is available for `ContributionScraper` objects.


## License

[MIT](LICENSE)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed list of changes.
