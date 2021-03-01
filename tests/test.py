from sunscrape.committee import CommitteeScraper
from sunscrape.contributions import ContributionScraper


scraper = CommitteeScraper(committee_name="Florida Citizen Voters",
                           result_type="contributions")

print(scraper.results)


contribs_scraper = ContributionScraper(from_date="01/01/2021")

print(contribs_scraper.results)