"""SunScrape - A Python library for scraping Florida campaign finance data."""

from .base import SunScraper, SunScrapeError, HTTPError, ParseError
from .contributions import ContributionScraper
from .expenditures import ExpenditureScraper
from .transfers import TransferScraper
from .committee import CommitteeScraper
from .candidate import CandidateScraper
from .candidate_lookup import CandidateLookup
from .committee_lookup import CommitteeLookup

__version__ = "0.2.0"
__all__ = [
    "SunScraper",
    "SunScrapeError",
    "HTTPError",
    "ParseError",
    "ContributionScraper",
    "ExpenditureScraper",
    "TransferScraper",
    "CommitteeScraper",
    "CandidateScraper",
    "CandidateLookup",
    "CommitteeLookup",
]
