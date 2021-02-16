from sunscrape.committee import CommitteeScraper


scraper = CommitteeScraper(committee_name="Florida Citizen Voters",
                           result_type="contributions")

print(scraper.results)
