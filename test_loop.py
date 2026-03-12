from reddit2md.core.config import Config
from reddit2md.scraper import RedditScraper

# Force a low score requirement on a high-traffic sub so we drop items and trigger pagination
overrides = {
    'max_results': 4,
    'ignore_below_score': 500, # A high enough score to force rejection of some 'new' items
    'verbose': 2,
    'rescrape_newer_than_hours': 0, # Force skip maturity tracking for test
}

scraper = RedditScraper(debug=True, overrides=overrides)
scraper.run(source="gaming", overrides={'sort': 'new', 'max_results': 4})
