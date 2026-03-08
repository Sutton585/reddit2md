# reddit2md Architecture Document

**Target Platform:** Reddit  
**Module Name:** reddit2md

## 1. Objective
To build a professional-grade Reddit scraper designed for high-signal knowledge management. reddit2md transforms transient Reddit discussions into permanent, well-structured Markdown notes specifically optimized for Obsidian vaults, AI-automated workflows, and personalized daily digests.

## 2. Key Limitation & Technical Strategy
**Limitation:** Scraping Reddit without Official API Access (No OAuth tokens).
- **Discovery via RSS:** Standard `.json` index feeds for subreddits are heavily rate-limited and cached when accessed without an API key. To bypass this, the Client uses Reddit's `.rss` endpoints (e.g., `reddit.com/r/python/new/.rss`) to discover new `post_id`s reliably.
- **Deep Fetch via JSON:** Once a `post_id` is discovered via RSS, the Client fetches the full thread (including comments) using the individual post's `.json` endpoint (e.g., `reddit.com/comments/{post_id}.json`), which is less restricted.
- **Graceful Degradation:** The network client gracefully detects if the external `requests` library is installed. If available, it utilizes `requests` to bypass advanced anti-bot measures (e.g., Reddit's 403 Forbidden blocks). If not, it falls back to the standard library `urllib`.
- **Maturity Logic (The Living Note):** Implements a `min_post_age_hours` check. Threads scraped while young are marked as "Maturing" in the database. The Orchestrator returns after the age threshold to re-scrape and append the final, mature conversation, creating a chronological timeline.
- **Obsidian Graph Resolution:** Converts URLs pointing to other internal Reddit threads into Obsidian internal links (e.g., `[[Python_1rm32fu]]`).
- **File System Sanitization:** Reddit flairs often include slashes (`/`). The Processor layer sanitizes these into dashes (`-`) to prevent unintended nested directory creation.

## 3. The "5 Buckets" Implementation Plan

### A. Config (Settings Management)
Handles configuration merging following the Precedence Order (CLI > Job-Specific > Global Defaults). Validates these platform-specific toggles:
- `post_limit` (Integer): Maximum threads to fetch per feed run.
- `comment_detail` (Enum: XS, SM, MD, LG, XL): Controls the depth and volume of captured comments (e.g., `MD` = Top 8 comments, 2 replies deep).
- `sort` (Enum: new, hot, top, rising): Determines the targeted `.rss` endpoint.
- `min_post_age_hours` (Integer): The delay for maturity logic. Set to 0 to disable.
- `flair`, `filter_keywords`, `url_blacklist`: Search and output filters.
- `generate_subreddit_folders` (Boolean): Organizes output dynamically.

### B. Client (Network Operations)
Strictly isolates network logic from data parsing:
- `get_posts_from_rss(rss_url)`: Fetches and parses the XML Atom feed, extracting `post_id` and timestamp.
- `fetch_json_from_url(json_url)`: Handles raw HTTP GET requests to Reddit's `.json` endpoints.
- **Headers:** Applies standard browser-mimicking `User-Agent` and `Accept` headers to avoid standard bot-blocks.
- **Error Handling:** Explicitly catches 403 errors and alerts the user to install `requests` if using the `urllib` fallback.

### C. Processor (Data Sanitization & Translation)
Translates the messy, deeply-nested Reddit JSON tree into the clean Sandman Standard Schema.
- Extracts `link_flair_text` to use as the `metadata_label`.
- `_process_comments_recursive()`: Parses the complex recursive comment tree and filters it based on the user's `comment_detail` preset (dropping removed/deleted comments).
- `resolve_links()`: Uses regex (`REDDIT_PERMALINK_REGEX`) to identify links to other Reddit posts. If the target post exists in the `DatabaseManager`, it replaces the URL with an internal Obsidian link format (`[[Subreddit_ID]]`).
- `parse_frontmatter()`: Reads existing `.md` files on disk to support the State Reconciliation Flow.

### D. DatabaseManager (State Tracking)
Acts as the high-speed SQLite cache (`database.db`).
- Tracks: `id`, `title`, `author`, `subreddit`, `flair`, `score`, `post_timestamp`, `file_path`, and `rescrape_after`.
- Controls the footprint limit using `max_db_records`, deleting the oldest unneeded records automatically.
- Facilitates the "State Reconciliation Flow" on startup by comparing DB records against the physical `.md` files.

### E. Orchestrator / Scraper (The Execution Loop)
The main entry point (`scraper.py`) that coordinates the other four buckets.
- **State Validation:** Runs `validate_state()` on startup to prune orphaned DB records (where the `.md` file was deleted by the user) or rebuild the DB entirely from `.md` files if the cache was lost.
- **Job Loop:** Iterates through the jobs defined in `config.json`.
- **Maturity Loop:** Queries the DB for posts where `rescrape_after` is past the current time, fetches them again, and triggers the Processor's update logic.
- **Output Routing:** Detects whether a scraped post is new or "maturing" and routes it to the correct template behavior (writing a new file vs. regex-replacing the frontmatter and appending a `## Updated Comments` block).

## 4. Standard Schema Mapping

When the Processor (`clean_json`) sanitizes the Reddit API response, it maps the raw fields as follows to strictly meet the Universal Blueprint's requirements:

- `post_id` -> Maps from `data['id']` (Reddit's immutable base-36 ID, e.g., `1rm32fu`).
- `title` -> Maps from `data['title']`.
- `author` -> Maps from `data['author']`.
- `content` -> Maps from `data['selftext']`.
- `time_scraped` -> Current local datetime.
- `time_posted` -> Maps from `data['created_utc']` (Unix timestamp).
- `metadata_label` -> Maps from `data['link_flair_text']` (Falls back to `subreddit_name_prefixed` if empty).
- `comments` -> A custom recursive array of dictionaries containing the comment `author`, `score`, and `body` (strictly filtered to remove stickied, `[deleted]`, and `[removed]` entries).
- `score` -> Maps from `data['score']` (Total upvotes).
- `module` -> Set statically to `"reddit2md"`.