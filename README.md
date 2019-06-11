# SunScrape

[![Build Status](https://travis-ci.com/SunSentinel/SunScrape.svg?branch=master)](https://travis-ci.com/SunSentinel/SunScrape)

A python library that scrapes and parses campaign finance data from the [Florida Secretary of State's website](https://dos.myflorida.com/elections/candidates-committees/campaign-finance/campaign-finance-database/).


## Installation
This package isn't on PyPI yet, so install from the repo:

`pip install git+https://github.com/SunSentinel/SunScrape.git`


## Usage
SunScrape makes it possible to grab campaign finance data in bulk in a usable, machine-readable format. 

This library provides a way to search Florida's campaign finance portal either by a particular entity or a specific filing type.


### By entity
Results can be obtained for a particular candidate or committee.

#### Candidate
Results for a candidate.

#### Committee
Results of a particular committee registered in the state. A list of these committees can be found here: https://dos.elections.myflorida.com/committees/ComLkupByName.asp


### By filing
You can also search through all contributions, expenses or fund transfers reported to the SOS's office. Additional search terms can also be passed to these object:

* `candidate_first` - Candidate first name
* `candidate_last` - Candidate last name
* `from_date` - Start date (MM/DD/YYYY)
* `to_date` - End date (MM/DD/YYYY)
* `committee_name` - Committee name, or partial name
* `election_id` - See [Election IDs](#election-ids)
* `all_time` - `True` or `False`, returns results for all years

#### Contributions
#### Expenses
#### Transfers



**Example**
```python

>>> from sunscrape.contributions import ContributionScraper
>>> scraper = ContributionScraper(candidate_first='Ron', candidate_last='Desantis')
>>> scraper.results

[{'candidate': 'DeSantis, Ron', 'candidate_party': 'Republican', 'date': '2018-07-18', 'amount': '3000.00', 'type': 'CHE', 'contributor_name': '1188 PARTNERS, LLC', 'contributor_address': '2141 ALAQUA DRIVE', 'contributor_address2': 'LONGWOOD, FL 32779', 'contributor_occupation': 'INSURANCE', 'inkind_description': ''}...]
```


## Known issues

#### Election IDs

The library allows finance records searches by election, but you need the election ID used by the Secretary of State. You can find these with the `get_election_ids()` method.


#### Searching by date

The SOS's expenditure and fund transfer search portals fail when specifying a date, so we excluded these options from the `expenditures` and `transfers` objects. Though it is still possible to use the arguments in `contributions` objects.


## Development

#### Requirements
+ Python 3
+ Virtual environment

#### Steps
1. Clone this repository: `git clone https://github.com/SunSentinel/SunScrape.git`
2. Change into project directory: `cd SunScrape`
3. Start up your virtual environment.
4. Install SunScrape from local source: `pip install -e .`
5. Install requirements: `pip install -r requirements.txt` or `pipenv install` for pipenv users.


## Running tests
`pytest`

## Contributing
Want to help out? Submit an issue or pull request.

## License
[MIT](LICENSE)
