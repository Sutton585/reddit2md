# reddit2md: The Reddit to Markdown collectionor
reddit2md is a professional-grade Reddit scraper designed for high-signal knowledge management. It transforms transient Reddit discussions into permanent, well-structured Markdown notes for use in Obsidian vaults, AI-automated workflows, and personalized knowledge collections.

Whether you are building a research database, feeding an AI agent, or just keeping up with specific subreddits, reddit2md provides the granularity and control needed for a high-quality data pipeline. It requires no external Python libraries, relying entirely on the Python standard library for maximum portability and security.

---

## 1. Installation & Quick Start
To get started, clone the repository to your local machine. Since reddit2md uses only the Python standard library, you do not need to install any external packages. Simply run python reddit2md.py in your terminal. On the first run, if no config.yml is found, the program will create a template for you. You can then edit this file to add your preferred subreddits and customize your settings.

### The Reliability Upgrade (Recommended)
While reddit2md is designed to run with zero dependencies, Reddit's security measures occasionally block standard Python requests. For maximum reliability and to bypass 403 Forbidden errors, we highly recommend installing the requests library:
pip install requests

---

## 2. Key Dependencies

- **Python Standard Library (urllib, sqlite3, xml.etree):** Used for all core operations (network, database, and RSS parsing) to ensure maximum portability and zero-dependency reliability by default.
- **Requests (Recommended):** Used as an optional upgrade to handle advanced anti-bot measures (like 403 Forbidden blocks) that the standard library may struggle with.

---

## 3. One Tool, Three Interfaces
reddit2md is designed to be agnostic. Every setting and feature is available with 100% parity across three interaction modes: the CLI, the config file, and as a Python resource.

### Using the Command Line Interface
The CLI is the most common way to use reddit2md. You can run all configured scrape tasks by calling the script with no arguments. To scrape a specific subreddit on the fly (even if it is not in your config), use the --source argument followed by the subreddit name. For example:
```bash
python reddit2md.py --source news --max-results 5 --detail XL --sort top --min-age-hours 24
```

### Using as a Python Dependency
You can import the RedditScraper class into your own projects. This is ideal for building custom AI agents that need fresh Reddit data.
```python
from reddit2md import RedditScraper

scraper = RedditScraper(config_path="config.yml")
scraper.run(source="Python", overrides={'max_results': 5, 'detail': 'XL'})
```

### Using the Configuration File
The config.yml file allows you to set global defaults and then define a list of specific tasks in the routine. This is the best way to manage a large list of scrape tasks for a knowledge collection. Note that you can have multiple tasks for the same subreddit with different settings.

```yaml
settings:
  md_output_directory: "My Vault/Reddit"
  min_score: 50
  data_output_directory: "data"
  group_by_source: true

routine:
  - source: "MarvelComics"
    sort: "top"
  - source: "MarvelComics"
    detail: "XL"
```

---

## 4. Core Concepts & Philosophy
To use reddit2md effectively, it is important to understand its foundational pillars.

### The Multi-Layer Source of Truth
reddit2md uses a tripartite authority model to ensure data integrity:
- Markdown Files (The Authority): The ultimate source of truth. If you edit the label or rescrape_after date in your Obsidian note, the system detects this on the next run and updates the database. Deleting a note tells the system to forget the post entirely.
- SQLite Database (The Memory): Acts as a high-speed cache and state-tracker. It handles the logic for maturity delays and history. The DB is self-healing—if deleted, it will automatically rebuild itself by scanning your Markdown folders.
- JSON Archive (The Backup): Stores sanitized data for every scrape. This allows for a total vault rebuild without re-querying Reddit if your Markdown files are ever lost.

### Cumulative Knowledge (Living Notes)
Standard scrapers overwrite files, losing previous data. reddit2md creates chronological records. When a post is re-scraped (e.g., after it matures):
1. The front-matter is updated with the latest score and metadata.
2. The old comment section is preserved.
3. A new ## Updated Comments ([Timestamp]) section is appended to the bottom.
This allows you to track how discussions evolve over time within a single note.

### Automatic Internal Linking
reddit2md is built for interconnected knowledge. If a scraped post or comment contains a URL to another Reddit thread that you have already scraped, the system automatically converts that URL into an internal Obsidian link (e.g., [[Python_1rm32fu]]). This allows you to navigate your research as a connected graph rather than a collection of isolated files.

### Context vs. Freshness: The Maturity Logic
Scraping a thread the moment it is posted often misses the best discussion. reddit2md uses the min_age_hours setting to solve this. If a post is young, it is scraped immediately for freshness, but marked as Maturing. The system then automatically returns after the age threshold is met to append the final, mature conversation. Note: If you do not care about post maturity and want every scrape to be final, simply set min_age_hours to 0. This disables all re-scraping logic.

### Safe Vault Coexistence & Sanitization
To allow reddit2md notes to live alongside your existing research, the system uses a surgical ownership check. It only processes files where the post_id in the front-matter is present. This prevents the scraper from ever touching unrelated Markdown files in the same directory. 

Tip: You can manually lock a note to prevent future updates by simply deleting the rescrape_after field from its front-matter.

Additionally, the system automatically sanitizes labels derived from Reddit flairs to ensure they are safe for all file systems. Any forward slashes (/) are replaced with dashes (-), preventing unintended nested directory creation.

---

## 5. Debug Mode: The Safety Toggle
The debug flag is a powerful safety toggle designed to protect your live data during testing. Its behavior is consistent across all interfaces.

### How Debug Mode Works
- When Debug is TRUE (Default/Test State): All custom path settings for md_output_directory, data_output_directory, and md_log are ignored. The system forces all output into the local /data folder within the repository. This ensures that test runs do not pollute your Obsidian vault or live research database.
- When Debug is FALSE (Production State): The system respects your custom path settings, allowing you to route Markdown notes and logs directly into your preferred workspace.

### Typical Workflow Example
1. Test: Set "debug": true in your config. Experiment with new subreddits or detail settings. Verify the results in the local /data/markdown/ directory.
2. Deploy: Once satisfied, set "debug": false and point your md_output_directory to the live directory, (ie. your Obsidian Vault). All future runs will now populate your vault with beautifully formatted notes organized by subreddit.

---

## 6. Automation: Set It and Forget It
To maintain a fresh knowledge base, you can schedule reddit2md to run automatically. On macOS or Linux, you can use a cron job to trigger a scrape periodically:
0 8 * * * cd /path/to/reddit2md && /usr/bin/python3 reddit2md.py --debug False

---

## 7. Comprehensive Configuration Reference
Use this section as an encyclopedia for fine-tuning your data pipeline.

### Console Output Level
Description: Controls the verbosity of the terminal output during execution. 0 = Errors only, 1 = Progress & Warnings (Default), 2 = Granular Debugging.
- Config: "verbose": 1
- CLI: --verbose 1
- Python: 'verbose': 1

### Post Limit
Description: The maximum number of new threads reddit2md will attempt to fetch from a subreddit feed during a single run.
- Config: "max_results": 8
- CLI: --max-results 8
- Python: 'max_results': 8

### Comment Detail Presets
Description: Presets to control the exact volume and depth of comments captured. 
- XS: Top 3 top-level comments, 0 replies (Literal: 3 total).
- SM: Top 5 top-level comments, 1 reply each (Literal: 5 + 5 = 10 max).
- MD (Default): Top 8 top-level comments, 2 replies each (Literal: 8 + 16 = 24 max).
- LG: Top 10 top-level comments, 3 depth (3 replies, 1 sub-reply) (Literal: 10 + 30 + 30 = 70 max).
- XL: No limits. Recursively captures every single comment and reply.
- Config: "detail": "MD"
- CLI: --detail MD
- Python: 'detail': 'MD'

### Flair
Description: Categorizes the post based on its source metadata.
- Config: "label": "Value"
- CLI: --label Value
- Python: 'label': 'Value'

### Post Link
Description: Metadata field for links to external URLs or internal Obsidian links to related scraped posts.
- Config: "post_links": "URL"
- CLI: --post-links URL
- Python: 'post_links': 'URL'

### Save JSON
Description: Whether the sanitized JSON data fetched from Reddit is persisted to your data directory after the Markdown note is generated.
- Config: "save_json": true
- CLI: --save-json [True/False]
- Python: 'save_json': True

### Update Scrape Log
Description: Whether the human-readable Scrape Log.md dashboard is updated during the run.
- Config: "md_log": true
- CLI: --md-log [True/False]
- Python: 'md_log': True

### Maximum DB Records
Description: Footprint control for the SQLite cache. When the DB exceeds this limit, the oldest records are pruned (does not touch Markdown files).
- Config: "db_limit": 1000
- CLI: --db-limit 1000
- Python: 'db_limit': 1000

### Reddit Sort Method
Description: Choice of sort determines the flavor of your research: new (Default) for real-time tracking, hot for discovery, top for historical quality, or rising for momentum.
- Config: "sort": "new"
- CLI: --sort new
- Python: 'sort': 'new'

### Post Age Filtering (`min_age_hours` / `max_age_hours`)
Sandman allows you to strictly filter out posts based on their age:
- **`min_age_hours`**: The minimum age of a post to be considered relevant. Anything newer is entirely ignored.
- **`max_age_hours`**: The maximum age of a post to be considered relevant. Posts older than this will not be scraped at all.

### Maturity Logic (`rescrape_threshold_hours`)
Description: The window of time a post must exist before it is considered mature. If a post is younger than this limit, it is scraped for freshness but marked for a later re-scrape. Set to 0 to disable re-scraping logic entirely.
- Config: "rescrape_threshold_hours": 12
- CLI: --rescrape-threshold-hours 12
- Python: 'rescrape_threshold_hours': 12

### Feed Pagination (`offset`)
Description: Discards the first N results from the parsed Reddit RSS feed before the scraper begins processing them. Useful for picking up where a previous scrape left off.
- Config: "offset": 10
- CLI: --offset 10
- Python: 'offset': 10

### Filter Keywords
Description: Case-insensitive keywords. If any appear in a post title, the post is skipped.
- Config: "blacklist_terms": ["word1", "word2"]
- CLI: --blacklist-terms "word1, word2"
- Python: 'blacklist_terms': ["word1", "word2"]

### URL Blacklist
Description: Prevents specific domains or fragments from being included in post_links metadata.
- Config: "blacklist_urls": ["fragment1", "fragment2"]
- CLI: --blacklist-urls "fragment1, fragment2"
- Python: 'blacklist_urls': ["fragment1", "fragment2"]

### Subreddit Folders
Description: Whether the system creates a sub-folder for each subreddit within your output directory.
- Config: "group_by_source": false
- CLI: --group-by-source [True/False]
- Python: 'group_by_source': False

---

## 8. Directory Structure and Files
reddit2md organizes its data into three main components. The markdown folder contains the notes you see in your live directory (ie. Obsidian). The json folder inside the data directory contains the structured data used by the system and AI agents. The database.db file inside the data directory acts as the high-speed index. Finally, the Scrape Log.md file provides a more human-readable record showing the status of every post, including which ones are currently maturing and when they are scheduled for their final re-scrape.
