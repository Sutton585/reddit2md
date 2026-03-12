# reddit2md: The Reddit to Markdown collector

reddit2md is a professional-grade Reddit scraper designed for high-signal knowledge management. It transforms transient Reddit discussions into permanent, well-structured Markdown notes for use in Obsidian vaults, AI-automated workflows, and personalized knowledge collections.

Whether you are building a research database, feeding an AI agent, or just keeping up with specific subreddits, reddit2md provides the granularity and control needed for a high-quality data pipeline. It requires no external Python libraries, relying entirely on the Python standard library for maximum portability and security.

---

## Installation & Quick Start
To get started, clone the repository to your local machine. Since reddit2md uses only the Python standard library, you do not need to install any external packages. Simply run `python reddit2md.py` in your terminal. On the first run, if no `config.yml` is found, the program will create a template for you. You can then edit this file to add your preferred subreddits and customize your settings.

### The Reliability Upgrade (Recommended)
While reddit2md is designed to run with zero dependencies, Reddit's security measures occasionally block standard Python requests. For maximum reliability and to bypass 403 Forbidden errors, we highly recommend installing the `requests` library:
`pip install requests`

---

## Dependencies

- **Python Standard Library (`urllib`, `sqlite3`, `xml.etree`):** Used for all core operations (network, database, and RSS parsing) to ensure maximum portability and zero-dependency reliability by default.
- **Requests (Recommended):** Used as an optional upgrade to handle advanced anti-bot measures (like 403 Forbidden blocks) that the standard library may struggle with.

---

## The Three Categories of Querying & Filtering

When you execute a scrape routine via the CLI, Python, or the config file, it's highly important to understand how the parameters affect the underlying engine. They fall into three distinct categories based on network reliability and signal lag:

### 1. Core Query Parameters
**Parameters:** `source` / `sources`, `sort`, `timeframe`, `post_type`, `allow_nsfw`, `label_exact` (when `sort: new`)
**Mechanic:** These parameters communicate directly with the most reliable, up-to-date Reddit API endpoints. They suffer from virtually zero lag. If a feed utilizing these parameters returns 0 results, it means there are genuinely 0 results available on Reddit matching that criteria at this exact moment.

### 2. Advanced Query Parameters (Search Injection)
**Parameters:** `search`, `exclude_terms`, `exclude_author`, `exclude_urls`, `exclude_label`, `label`
**Mechanic:** Using any of these parameters forcibly shifts the engine to use Reddit's internal search endpoint by injecting a Lucene-style query (`q=`). By filtering *at the source API level*, you ensure that Reddit returns highly relevant content inside its strict 25-item limit. While normally totally consistent, because it relies on Reddit's search engine indexing, the possibility of minimal lag-related inconsistencies exists. *(See **Advanced Querying** below for syntax).*

### 3. Local-Side Filtering 
**Parameters:** `ignore_older_than_hours`, `ignore_newer_than_hours`, `ignore_below_score`
**Mechanic:** These parameters are processed locally in Python *after* the network fetch occurs. Using these parameters has the effect of filtering the *results* of the query, not refining the query itself. Because we only receive a maximum of 25 results per scrape, filtering locally means you might end up with 0 items saved. This does not necessarily mean no posts match your criteria on Reddit; it simply means none of the *top 25 returned items* met your local requirements (e.g., they weren't old enough or didn't have high enough scores).

---

## One Tool, Three Interfaces, Three Outputs
reddit2md is designed to be completely agnostic. Every setting and feature is available with 100% parity across three interaction modes: the CLI, the config file, and as a Python resource.

More importantly, it makes **zero assumptions about the format you want your data in**. It provides three computationally equivalent repositories of output, allowing you to build the exact pipeline you need. **Crucially, the directory paths and names for all three of these outputs can be fully custom-configured on the fly using either the config file (`config.yml`), CLI arguments (e.g., `--data-dir`), or Python dictionary overrides.**

1. **User-Controlled Markdown Documents:** Generating Obsidian-ready `.md` files utilizing dynamic text templates (`post.template`, `comment.template`, `update.template`), giving you absolute control over your YAML frontmatter schema and body layout.
2. **Raw JSON Archives:** Generating noise-free, sanitized JSON artifacts specifically optimized for token-efficient LLM ingestion or Python data-science pipelines.
3. **The Detailed SQLite Database:** Operating as a headless background observer, tracking state and (if `--detailed-db` is enabled) caching the entire payload natively into SQL columns for direct querying, bypassing file generation entirely.

### Using the Command Line Interface
The CLI is the most common way to use reddit2md. You can run all configured scrape routines by calling the script with no arguments. To scrape a specific subreddit on the fly (even if it is not in your config), use the `--source` argument followed by the subreddit name. To run a configured routine block by its name, use the `--routine` argument.

```bash
# Basic run 
python reddit2md.py --source news --max-results 5 --detail XL --sort top --ignore-older-than-hours 24

# Advanced query — flair + keyword pre-filter
python reddit2md.py --source LeaksAndRumors --label "Comic,Movie" --search "avengers OR thor" --sort new

# Top posts of the week, text-only
python reddit2md.py --source python --sort top --timeframe week --post-type self

# Execute a specifically named routine from config.yml
python reddit2md.py --routine "Daily Python Search"
```

### Using as a Python Dependency
You can import the `RedditScraper` class into your own projects. This is ideal for building custom AI agents that need fresh Reddit data.

```python
from reddit2md import RedditScraper

scraper = RedditScraper(config_path="config.yml")

# Basic run
scraper.run(source="Python", overrides={'max_results': 5, 'detail': 'XL'})

# Advanced run — Author search across all of Reddit
scraper.run(overrides={
    'search': 'author:username AND title:announcement',
    'sort': 'new',
    'allow_nsfw': True
})
```

### Using the Configuration File
The `config.yml` file allows you to set global defaults and then define a list of specific routines in the `routine` block. This is the best way to manage a large list of scrape commands for a knowledge collection. Note that you can have multiple routines for the same subreddit with completely different settings. You can optionally label each entry with a `name` parameter to target them via the CLI's `--routine` argument.

```yaml
settings:
  md_output_directory: "My Vault/Reddit"
  ignore_below_score: 50
  data_output_directory: "data"
  group_by_source: true

routine:
  - name: "Top Marvel Comics"
    source: "MarvelComics"
    sort: "top"
    
  - name: "Deep Dive Marvel Comics"
    source: "MarvelComics"
    detail: "XL"
```

---

## Advanced Querying Syntax (Category 2)

When utilizing the **Advanced Query Parameters** (Category 2), reddit2md builds your criteria directly into the RSS URL using `exclude_` and `search` parameters, ensuring Reddit returns up to 25 results that already match your target logic.

### Multi-Subreddit in a Single Routine
You can target multiple subreddits in a single routine by providing a list as the source (`sources: ["python", "programming"]`). This generates a single HTTP call joining them into one stream (e.g., `r/python+programming/.rss`) rather than making multiple calls.

```yaml
routine:
  - sources: ["movies", "marvelstudios"]
    sort: new
    search: "avengers OR thor"
```

### Search Field Operators
The `search` (formerly query) parameter supports full Lucene-style Reddit search syntax injected completely raw into the URL.

| Operator | Example | Effect |
|---|---|---|
| `AND` / `OR` / `NOT` | `marvel AND NOT disney` | Boolean logic |
| `" "` (quotes) | `"spider-man"` | Exact phrase match |
| `title:` | `title:announcement` | Search post titles only |
| `site:` | `site:youtube.com` | Filter by linked domain |

```bash
# Example: Find all posts by a specific author mentioning a keyword
python reddit2md.py --source Python --search "author:gvanrossum AND title:release"
```

### Exclude Filters
Separate out your exclusions from your `search` query by utilizing specific exclusion lists. These are formatted into correct Reddit search operators for you.

- `exclude_terms: ["AI", "crypto"]`: Explicitly drops posts with these terms via `NOT "term"` in the URL. As an additional best-of-both-worlds safeguard, this parameter *also* runs again locally after fetch.
- `exclude_author: ["AutoModerator"]`: Excellent for dismissing automated posts. Drop posts via `NOT author:name`.
- `exclude_urls: ["youtube.com"]`: Drops posts that are primarily linking to specific domains.
- `exclude_label: ["Megathread"]`: Drops posts utilizing specific flairs.

### Flair Filtering
Two modes are available for positive flair matching:
- `label` (partial match): Catches any flair containing that text (e.g., "Comic" matches "Comic Books"). Supports a list for OR logic. Pushes traffic to the search endpoint.
- `label_exact` (exact match): Uses `flair_name:` for strict matching. Optimized to use the `f=` browse parameter if `sort: new` is applied, preventing any search index lagging.

---

## Core Concepts & Philosophy
To use reddit2md effectively, it is important to understand its foundational pillars.

### The Multi-Layer Source of Truth (The Data Triad)
reddit2md uses a tripartite authority model to ensure data integrity and maximize pipeline flexibility:
- **Markdown Files (The Authority):** The ultimate source of truth for human users. If you edit the label or `rescrape_after` date in your Obsidian note, the system detects this on the next run and updates the database. Deleting a note tells the system to forget the post entirely. You control the exact shape of these documents using the files in the `templates/` directory.
- **SQLite Database (The Brain & Data Warehouse):** Acts as a high-speed cache and state-tracker. It handles the logic for maturity delays and history. If you configure `detailed_db: true` (or simply disable JSON file saving), this database will expand its schema to capture the entire payload (upvote ratios, comments, media flags) allowing you to use it as a native headless data warehouse. The DB is self-healing—if corrupted, it will rebuild itself by scanning your Markdown folders.
- **JSON Archive (The Payload Backup):** Stores sanitized data for every scrape. This allows for a total vault rebuild without re-querying Reddit if your Markdown files are ever lost, and acts as the cleanest ingestion point for local AI pipelines.

### Cumulative Knowledge (Living Notes)
Standard scrapers overwrite files, losing previous data. reddit2md creates chronological records. When a post is re-scraped (e.g., after it matures):
1. The front-matter is updated with the latest score and metadata.
2. The old comment section is preserved.
3. A new `## Updated Comments ([Timestamp])` section is appended to the bottom.
This allows you to track how discussions evolve over time within a single note.

### Automatic Internal Linking
reddit2md is built for interconnected knowledge. If a scraped post or comment contains a URL to another Reddit thread that you have already scraped, the system automatically converts that URL into an internal Obsidian link (e.g., `[[Python_1rm32fu]]`). This allows you to navigate your research as a connected graph rather than a collection of isolated files.

### Context vs. Freshness: The Post Age and Maturity Logic
Scraping a thread the moment it is posted often misses the best discussion. reddit2md allows you to implement precise age filtering thresholds to guarantee fresh scrapes or deep, mature discussions.

This is best illustrated via the interaction between the three time-based configuration parameters.

```yaml
source: marvelstudios
timeframe: day                    # t=day in URL — Reddit returns posts from past 24h only
ignore_newer_than_hours: 20       # local — discard anything under 20h old
rescrape_newer_than_hours: 24     # local — anything under 24h old gets a rescrape mark
```

What happens step by step:
1. URL is built with `t=day` — Reddit returns up to 25 posts from the past 24 hours.
2. Local Ignore: any post older than 20 hours is discarded entirely — not scraped, not tracked.
3. Local Rescrape check: every surviving post is under 20 hours old, which is under the `rescrape_newer_than` threshold of 24 hours, so **every single surviving post gets a rescrape mark** tracking it in the SQLite DB.
4. On the next run after maturity, those posts are revisited and the mature discussion is appended to the markdown files.

Net effect: you collect only posts in the 0–20h window, and you automatically return to all of them when they mature. No manual tracking needed. (Note: If you do not care about post maturity and want every scrape to be final, you can explicitly set `rescrape_newer_than_hours` to 0 or leave it unset outright).

### Safe Vault Coexistence & Sanitization
To allow reddit2md notes to live alongside your existing research, the system uses a surgical ownership check. It only processes files where the `post_id` in the front-matter is present. This prevents the scraper from ever touching unrelated Markdown files in the same directory. 

Tip: You can manually lock a note to prevent future updates by simply deleting the `rescrape_after` field from its front-matter.

Additionally, the system automatically sanitizes labels derived from Reddit flairs to ensure they are safe for all file systems. Any forward slashes (`/`) are replaced with dashes (`-`), preventing unintended nested directory creation.

---

## Debug Mode: The Safety Toggle
The debug flag is a powerful safety toggle designed to protect your live data during testing. Its behavior is consistent across all interfaces.

### How Debug Mode Works
- When Debug is TRUE (Default/Test State): All custom path settings for `md_output_directory`, `data_output_directory`, and `md_log` are ignored. The system forces all output into the local `./data` folder within the repository. This ensures that test runs do not pollute your Obsidian vault or live research database.
- When Debug is FALSE (Production State): The system respects your custom path settings, allowing you to route Markdown notes and logs directly into your preferred workspace.

---

## Automation: Set It and Forget It
To maintain a fresh knowledge base, you can schedule reddit2md to run automatically. On macOS or Linux, you can use a cron job to trigger a scrape periodically:
`0 8 * * * cd /path/to/reddit2md && /usr/bin/python3 reddit2md.py --debug False`

---

## Comprehensive Configuration Reference
Use this section as an encyclopedia for fine-tuning your data pipeline. You can use any of the below keys securely in your `config.yml` or through CLI arguments by converting snake_case parameter names to dash-case (e.g., `--ignore-older-than-hours`).

### Routine Identity
- **`name`**: An optional human-readable name for a routine block, targetable by the CLI parameter `--routine`. 

### System & Scrape Logistics
- **`max_results`**: Maximum number of new threads reddit2md will process from the feed per run.
- **`offset`**: Discards the first N results from the parsed Reddit RSS feed. (Local slice).
- **`verbose`**: Console output level. (0 = Errors, 1 = Progress, 2 = Debugging).
- **`save_json`**: Persists sanitized JSON data to your data directory after markdown block generation.
- **`save_md`**: Generates human-readable Markdown files.
- **`detailed_db`**: Forces the SQLite database schema to expand and catch all JSON properties for headless querying. (Automatically enabled if `save_json` is false but the tool is actively scraping).
- **`db_limit`**: Maximum DB records to hold in SQLite before pruning. Acting as an active garbage collector, the system will delete the oldest associated `.json` files when pruning DB records.
- **`md_log`**: True/False toggle to append a human-readable run record in a `Scrape Log.md` file.
- **`track`**: Set this boolean to false to completely ignore reading and writing to the SQLite DB on runs.
- **`group_by_source`**: Sorts generated markdown into subdirectories based on their subreddit source.
- **`detail`**: Presets to control comment depth: (`XS`, `SM`, `MD` (Default), `LG`, `XL`).

### URL Level Pre-Filtering Settings
- **`source`** / **`sources`**: The subreddit(s). Lists of elements are joined via `+` in a single request.
- **`sort`**: The feed sort algorithm (`new`, `hot`, `top`, `rising`, `relevance`, `comments`).
- **`timeframe`**: A broad window restricting the posts returned (`hour`, `day`, `week`, `month`, `year`, `all`). Maps to Reddit's `t=` parameter across both browse and search endpoints.
- **`post_type`**: Limits either to `link` or `self` (text) posts.
- **`allow_nsfw`**: Enables the retrieval of maturely-filtered posts.
- **`nsfw_only`**: Forces the search feed to exclusively return NSFW-marked posts.
- **`spoiler`**: Forces the feed to exclusively return spoiler-marked posts.
- **`search`**: Freeform Reddit search queries (Lucene-style). See Advanced Querying section.
- **`title_search`**: Restricts keyword searching to exclusively target the post title.
- **`selftext`**: Restricts keyword searching to exclusively target the body content of a text post.
- **`author`**: Requires posts to be submitted by a comma-separated list of usernames.
- **`domain`**: Requires posts to link out to a specific domain (e.g., `youtube.com`).
- **`label`**: A partial match for matching flairs.
- **`label_exact`**: Matches flairs explicitly and directly. 

### URL Exclude Settings
- **`exclude_label`**: Skips over posts carrying a specific list of flairs.
- **`exclude_terms`**: Prevents posts mentioning specific words or keywords (AND explicitly drops them in the local ignore phase for optimal safety net verification).
- **`exclude_urls`**: Drops posts linking out to specific websites/domains.
- **`exclude_author`**: Prevents accounts (especially bots/Automods) from displaying in the return pool.

### Local Ignore Settings
- **`ignore_below_score`**: Drops posts from generating a markdown file if they don't meet an upvote count.
- **`ignore_below_upvote_ratio`**: Drops posts locally if their overall upvote percentage is below a threshold (e.g., `0.95` for 95%).
- **`ignore_below_comments`**: Drops posts locally if they have fewer than a threshold of comments at time of scrape.
- **`ignore_urls`**: Explicitly removes specific URLs from saving inside the markdown `post_links` array output section (Does not filter out the *post itself* from retrieving).
- **`ignore_older_than_hours` / `_days`**: Discards posts locally if they are older than the threshold setting.
- **`ignore_newer_than_hours` / `_days`**: Discards posts locally if they are younger than the threshold setting.
- **`rescrape_newer_than_hours` / `_days`**: The primary maturity logic controller. Creates the file but queues it in the database tracking loop to be retrieved again after the provided timespan.
