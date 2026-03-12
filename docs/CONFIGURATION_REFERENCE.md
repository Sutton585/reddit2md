# Configuration Reference

This document serves as the encyclopedia for fine-tuning your data pipeline. You can use any of the below keys securely in your `config.yml` or through CLI arguments by converting snake_case parameter names to dash-case (e.g., `--ignore-older-than-hours`).

For details on how these parameters map to exact URL endpoints and filtering categories, see the [Variable to Endpoint Mapping](VARIABLE_TO_ENDPOINT_MAPPING.md) guide.

---

## System & Scrape Logistics

### `max_results`
Maximum number of new threads reddit2md will process from the feed per run.
### `offset`
Discards the first N results from the parsed Reddit RSS feed.
### `verbose`
Console output level. (0 = Errors, 1 = Progress, 2 = Debugging).
### `save_json`
Persists sanitized JSON data to your data directory after parsing.
### `save_md`
Generates human-readable Markdown files.
### `detailed_db`
Forces the SQLite database schema to expand and catch all JSON properties for headless querying. (Automatically enabled if `save_json` is false but the tool is actively scraping).
### `db_limit`
Maximum DB records to hold in SQLite before pruning. Acting as an active garbage collector, the system will delete the oldest associated `.json` files when pruning DB records.
### `md_log`
True/False toggle to append a human-readable run record in a `Scrape Log.md` file.
### `track`
Set this boolean to false to completely ignore reading and writing to the SQLite DB on runs.
### `group_by_source`
Sorts generated markdown into subdirectories based on their subreddit source.
### `detail`
Presets to control comment depth: (`XS`, `SM`, `MD` (Default), `LG`, `XL`).

---

## URL Level Pre-Filtering Settings (Category 1 & 2)

These settings interact directly with the Reddit API to filter results at the source.

### `source` / `sources`
The subreddit(s). Lists of elements are joined via `+` in a single request.
### `sort`
The feed sort algorithm (`new`, `hot`, `top`, `rising`, `relevance`, `comments`).
### `timeframe`
A broad window restricting the posts returned (`hour`, `day`, `week`, `month`, `year`, `all`). Maps to Reddit's `t=` parameter across both browse and search endpoints.
### `post_type`
Limits either to `link` or `self` (text) posts.
### `allow_nsfw`
Enables the retrieval of maturely-filtered posts.
### `nsfw_only`
Forces the search feed to exclusively return NSFW-marked posts.
### `spoiler`
Forces the feed to exclusively return spoiler-marked posts.
### `search`
Freeform Reddit search queries (Lucene-style). See Advanced Querying section.
### `title_search`
Restricts keyword searching to exclusively target the post title.
### `selftext`
Restricts keyword searching to exclusively target the body content of a text post.
### `author`
Requires posts to be submitted by a comma-separated list of usernames.
### `domain`
Requires posts to link out to a specific domain (e.g., `youtube.com`).
### `label`
A partial match for matching flairs.
### `label_exact`
Matches flairs explicitly and directly.

### URL Exclude Settings
#### `exclude_label`
Skips over posts carrying a specific list of flairs.
#### `exclude_terms`
Prevents posts mentioning specific words or keywords (AND explicitly drops them in the local ignore phase for optimal safety net verification).
#### `exclude_urls`
Drops posts linking out to specific websites/domains.
#### `exclude_author`
Prevents accounts (especially bots/Automods) from displaying in the return pool.

---

## Local Ignore Settings (Category 3)

These settings filter posts *after* they are returned from Reddit, immediately triggering deep pagination to fulfill your `max_results` target.

### `ignore_below_score`
Drops posts from generating a markdown file if they don't meet an upvote count.
### `ignore_below_upvote_ratio`
Drops posts locally if their overall upvote percentage is below a threshold (e.g., `0.95` for 95%).
### `ignore_below_comments`
Drops posts locally if they have fewer than a threshold of comments at time of scrape.
### `ignore_urls`
Explicitly removes specific URLs from saving inside the markdown `post_links` array output section (Does not filter out the *post itself* from retrieving).
### `ignore_older_than_hours` / `_days`
Discards posts locally if they are older than the threshold setting.
### `ignore_newer_than_hours` / `_days`
Discards posts locally if they are younger than the threshold setting.
### `rescrape_newer_than_hours` / `_days`
The primary maturity logic controller. Creates the file but queues it in the database tracking loop to be retrieved again after the provided timespan.

---

## Advanced Querying Syntax

When utilizing the Advanced Query Parameters, reddit2md builds your criteria directly into the RSS URL using `exclude_` and `search` parameters.

### Search Field Operators
The `search` (formerly query) parameter supports full Lucene-style Reddit search syntax injected completely raw into the URL.

| Operator | Example | Effect |
|---|---|---|
| `AND` / `OR` / `NOT` | `marvel AND NOT disney` | Boolean logic |
| `" "` (quotes) | `"spider-man"` | Exact phrase match |
| `title:` | `title:announcement` | Search post titles only |
| `site:` | `site:youtube.com` | Filter by linked domain |

---

## Context vs. Freshness: The Post Age and Maturity Logic

Scraping a thread the moment it is posted often misses the best discussion. reddit2md allows you to implement precise age filtering thresholds to guarantee fresh scrapes or deep, mature discussions. This is best illustrated via the interaction between the three time-based configuration parameters.

```yaml
source: marvelstudios
timeframe: day                    # t=day in URL — Reddit returns posts from past 24h only
ignore_newer_than_hours: 20       # Category 3 local — discard anything under 20h old
rescrape_newer_than_hours: 24     # Category 3 local — anything under 24h old gets a rescrape mark
```

What happens step by step:
1. URL is built with `t=day` — Reddit returns up to 25 posts from the past 24 hours.
2. Local Ignore: any post younger than 20 hours is discarded entirely — not scraped, not tracked. Since this is a Category 3 filter, scraping a lot of recent posts will trigger deep pagination to fulfill the target limit.
3. Local Rescrape check: every surviving post is over 20 hours old, which is under the `rescrape_newer_than` threshold of 24 hours, so every single surviving post gets a rescrape mark tracking it in the SQLite DB.
4. On the next run after maturity, those posts are revisited and the mature discussion is appended to the markdown files.

Net effect: you collect only posts in the 20h–24h window, and you automatically return to all of them when they mature. No manual tracking needed. (Note: If you do not care about post maturity and want every scrape to be final, you can explicitly set `rescrape_newer_than_hours` to `0` or leave it unset outright).
