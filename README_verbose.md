# reddit2md: The Data Triad Architecture

A hyper-customizable, zero-dependency Python module built for the **Sandman Suite**. It ingests advanced Reddit querying parameters and exports clean, high-signal data. 

Unlike strict scrapers that enforce a specific file format, `reddit2md` makes no assumptions about how you want to use the data. It natively builds three equivalent repositories—**The Data Triad**—which can be toggled on or off based entirely on your workflow needs.

## The Three Output Repositories

1. **Markdown Documents (`--save-md`)**: Designed for PKM tools like Obsidian. Everything from the front-matter metadata down to the body content is heavily customizable using `post.template` and `comment.template` files. Perfect for human readers and Knowledge Graphs.
2. **JSON Archives (`--save-json`)**: Pure, structured data. Heavy metadata (including deep interaction metrics) is stored in a clean JSON format. Ideal for direct LLM ingestion or token-efficient pipelines.
3. **SQLite Database (`--detailed-db`)**: A native tracking index that doubles as a Data Warehouse. If enabled, it captures the entire rich JSON payload natively in SQL columns, allowing for complex historical queries without touching files. Essential for headless agents.

You can run `reddit2md` as a pure Markdown generator (MD=True, JSON=False, DB=False), a headless DB ingestor (MD=False, JSON=False, DB=True), or any combination thereof. 

---

## The Three Tiers of Querying & Filtering

To maintain API safety, respect Reddit's infrastructure, and prevent localized script lag, `reddit2md` categorizes parameters into a strict three-tier hierarchy based on where the filtering actually resolves.

### Category 1: Core URL Query Parameters
These parameters hit highly optimized, low-latency Reddit endpoints (e.g., `/r/python/.rss?sort=new`).
* **`source`**: The target subreddit or user (e.g., `r/Python`, `u/sutton585`).
* **`sort`**: `new`, `hot`, `top`, `relevance`, or `comments`.
* **`timeframe`**: Narrow queries to `hour`, `day`, `week`, `month`, `year`, or `all`. (Note: using `timeframe` automatically elevates the query to Category 2 backend processing).
* **`limit` / `max_results`**: The ceiling number of valid artifacts to extract.
* **`offset`**: Skip the first `N` results from the raw feed stream.

### Category 2: Advanced URL Filters
When you use these parameters, the tool dynamically redirects your query to Reddit's Advanced Search Endpoint (`/search.rss?q=...`), allowing for incredibly specific inclusion bounds. 
* **`--search` / `--query`**: Standard Lucene search string.
* **`--author`**: Require posts to be written by specific authors.
* **`--domain`**: Require links from specific domains (e.g., `youtube.com`).
* **`--selftext`**: Keywords required natively in the post body.
* **`--title-search`**: Keywords required natively in the post title.
* **`--nsfw-only`**: Boolean flag to restrict the feed strictly to NSFW content.
* **`--spoiler`**: Boolean flag to restrict the feed strictly to Spoiler content.

### Category 3: Local "Ignore" Parameters
These parameters operate locally *after* Reddit returns the raw feed. If a post fails one of these limits, the Python script rejects it *and automatically paginates deeper into Reddit's feed (Deep Pagination)* to ensure your `max_results` target is ultimately fulfilled. 
* **`--ignore-below-score`**: Discard posts falling below karma threshold.
* **`--ignore-below-upvote-ratio`**: Discard posts dropping below ratio (e.g., `0.85` for 85%).
* **`--ignore-below-comments`**: Discard posts with too few comments.
* **`--ignore-older-than-hours`**: Discards stale posts based on age.
* **`--ignore-newer-than-hours`**: Discards posts that are too fresh (wait for maturation).
* **`--exclude-terms`**: Keywords that force local rejection if found in the title.
* **`--exclude-author`**: Specific authors to drop.
* **`--exclude-urls`**: Specific domains to drop from link aggregation.

**Note on Deep Pagination:** 
To prevent excessive API abuse when using Category 3 parameters, `reddit2md` utilizes a hard-coded maximum pagination limit of 3 pages per query. 

---

## Agnostic Operation
Because this is a Sandman core module, there is 100% feature parity across all three interfaces. Whether you define your parameters in `config.yml`, override them in the terminal via `--flags`, or call `RedditScraper().run(overrides={})` from another Python script, the architecture routes them identically. 

*For detailed guidance on creating and managing Living Note Markdown Templates, see `docs/TEMPLATE_AND_VARIABLE_EXPANSION.md`.*
