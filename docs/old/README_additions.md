# README.md — Surgical Additions for v3.1
# =========================================
# This file documents every change needed to README.md.
# Nothing is rewritten. All changes are ADDITIONS or precise REPLACEMENTS
# of outdated text. Apply them in order.
#
# FORMAT:
#   LOCATION: [description of where in the file]
#   ACTION: APPEND | INSERT_AFTER | REPLACE
#   ---
#   [content]


# -----------------------------------------------------------------------
# CHANGE 1: Update version reference in the opening description
# -----------------------------------------------------------------------
# LOCATION: First paragraph, sentence mentioning "no external Python libraries"
# ACTION: No change needed — still accurate.


# -----------------------------------------------------------------------
# CHANGE 2: Add new sort values to the Sort Method reference entry
# -----------------------------------------------------------------------
# LOCATION: Section 7, "Reddit Sort Method" entry
# ACTION: REPLACE the Description line with the expanded version below
#
# OLD:
#   Description: Choice of sort determines the flavor of your research:
#   new (Default) for real-time tracking, hot for discovery, top for
#   historical quality, or rising for momentum.
#
# NEW:
#   Description: Choice of sort determines the flavor of your research:
#   new (Default) for real-time tracking, hot for discovery, top for
#   historical quality, rising for momentum, relevance for best keyword
#   match (useful with --query), or comments for most-discussed threads.
#   Note: relevance and top are most useful when combined with --time-filter.


# -----------------------------------------------------------------------
# CHANGE 3: Insert new "Advanced Querying" section between sections 3 and 4
# -----------------------------------------------------------------------
# LOCATION: After the closing of "## 3. One Tool, Three Interfaces" section,
#           before "## 4. Core Concepts & Philosophy"
# ACTION: INSERT the entire block below
# -----------------------------------------------------------------------

## 3.5 Advanced Querying: Pre-Filtering at the Source

Standard scraping fetches up to 25 posts from a subreddit feed and then filters locally. Advanced querying builds those filtering criteria directly into the RSS URL, so Reddit returns up to 25 results that already match your criteria — dramatically improving the signal-to-noise ratio of every run.

This is powered by Reddit's native search syntax. When any of the advanced parameters below are used, reddit2md automatically switches to the `search.rss` endpoint and assembles the correct URL. Simple configs with just `source` and `sort` continue to use the original browsing endpoint with no change in behavior.

### How It Works
When you specify a `query`, `label`, `post_type`, or other search parameter, the system constructs a URL like this:

```
https://www.reddit.com/r/LeaksAndRumors/search.rss?q=flair_text%3A%22Comics%22+AND+%28avengers+OR+thor%29&restrict_sr=on&sort=new&include_over_18=off
```

### Multi-Subreddit in a Single Task
You can target multiple subreddits in a single task by providing a list or plus-joined string as the source.

```yaml
# config.yml
routine:
  - source: "movies+marvelstudios"
    sort: new
    query: "avengers OR thor"
```

```python
# Python
scraper.run(source="movies+marvelstudios", overrides={'query': 'avengers OR thor'})
```

### Query Field Operators
The `query` parameter supports full Lucene-style Reddit search syntax:

| Operator | Example | Effect |
|---|---|---|
| `AND` / `OR` / `NOT` | `marvel AND NOT disney` | Boolean logic |
| `" "` (quotes) | `"spider-man"` | Exact phrase match |
| `title:` | `title:announcement` | Search post titles only |
| `author:` | `author:username` | Posts by a specific user |
| `url:` / `site:` | `url:youtube.com` | Filter by linked domain |

```bash
# Example: Find all posts by a specific author mentioning a keyword
python reddit2md.py --source Python --query "author:gvanrossum AND title:release"
```

### Flair Filtering
Two modes are available for flair matching:
- `label` (partial match): Catches any flair containing that text. Supports a comma-separated list for OR logic.
- `exact_flair` (exact match): Uses `flair_name:` for strict matching.

```yaml
# config.yml — Partial flair, multiple values
routine:
  - source: LeaksAndRumors
    label: ["Comic", "Movie"]
    sort: new
```

---


# -----------------------------------------------------------------------
# CHANGE 4: Add new parameters to Section 7 (Configuration Reference)
# -----------------------------------------------------------------------
# LOCATION: End of Section 7, after the "Subreddit Folders" entry
# ACTION: APPEND the block below


### Keyword Search (`query`)
Description: A literal keyword search string injected into the `q=` parameter of the RSS URL. Supports full Lucene/Reddit syntax including boolean operators (AND, OR, NOT), exact phrases in quotes, and field-specific operators like `author:`, `title:`, `selftext:`, `url:`.
- Config: `query: "avengers OR thor"`
- CLI: `--query "avengers OR thor"`
- Python: `'query': 'avengers OR thor'`

### Flair Filter — Partial (`label`)
Description: Pre-filters the RSS feed to posts whose flair contains this text (case-insensitive, partial match via `flair_text:`). A list value applies OR logic.
- Config: `label: "Comics"` or `label: ["Comics", "Movies"]`
- CLI: `--label "Comics"` or `--label "Comics,Movies"`
- Python: `'label': 'Comics'` or `'label': ['Comics', 'Movies']`

### Flair Filter — Exact (`exact_flair`)
Description: Pre-filters the RSS feed using `flair_name:` for an exact match. Overrides `label` if both are set.
- Config: `exact_flair: "Solved"`
- CLI: `--exact-flair "Solved"`
- Python: `'exact_flair': 'Solved'`

### Time Filter (`time_filter`)
Description: Limits results to a specific time window. Only meaningful when `sort` is set to `top` or `relevance`.
Values: `hour`, `day`, `week`, `month`, `year`, `all`
- Config: `time_filter: "week"`
- CLI: `--time-filter week`
- Python: `'time_filter': 'week'`

### Post Type (`post_type`)
Description: Filters the feed to a specific post format. `link` returns only link/image posts. `self` returns only text posts.
- Config: `post_type: "self"`
- CLI: `--post-type self`
- Python: `'post_type': 'self'`

### Allow NSFW (`allow_nsfw`)
Description: Controls whether NSFW-marked posts are included. Reddit excludes NSFW content by default. Only takes effect when the search endpoint is active.
- Config: `allow_nsfw: true`
- CLI: `--allow-nsfw True`
- Python: `'allow_nsfw': True`


# -----------------------------------------------------------------------
# CHANGE 5: Update CLI examples in Section 3
# -----------------------------------------------------------------------
# LOCATION: Section 3, "Using the Command Line Interface"
# ACTION: REPLACE the code block with:
#
# ```bash
# # Basic run (unchanged behavior)
# python reddit2md.py --source news --max-results 5 --detail XL --sort top --min-age-hours 24
#
# # Advanced query — flair + keyword pre-filter
# python reddit2md.py --source LeaksAndRumors --label "Comic,Movie" --query "avengers OR thor" --sort new
#
# # Top posts of the week, text-only
# python reddit2md.py --source python --sort top --time-filter week --post-type self
# ```


# -----------------------------------------------------------------------
# CHANGE 6: Update Python examples in Section 3
# -----------------------------------------------------------------------
# LOCATION: Section 3, "Using as a Python Dependency"
# ACTION: REPLACE the code block with:
#
# ```python
# from reddit2md import RedditScraper
#
# scraper = RedditScraper(config_path="config.yml")
#
# # Basic run
# scraper.run(source="Python", overrides={'max_results': 5, 'detail': 'XL'})
#
# # Advanced run — Author search across all of Reddit
# scraper.run(overrides={
#     'query': 'author:username AND title:announcement',
#     'sort': 'new',
#     'allow_nsfw': True
# })
# ```
