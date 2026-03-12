# reddit2md Refactor — Complete Before/After Audit

This document is a full audit of every parameter, feature, and behavior
in reddit2md. For each item: what it was called before, what it's called
now, whether its behavior changed, and whether it's new.

Status key:
  ✅ UNCHANGED — same name, same behavior
  🔄 RENAMED — different name, same behavior (old name still works as alias)
  ⚡ CHANGED — behavior meaningfully different
  🆕 NEW — did not exist before
  ❌ REMOVED — no longer supported

---

## 1. Task/Routine Structure

### `name`
- **Before:** Not supported. Tasks could only be targeted via `--source`.
- **After:** Optional field on any routine entry. Enables `--task "name"` CLI targeting.
- **Status:** 🆕 NEW
- **Example:**
  ```yaml
  routine:
    - name: "Daily Marvel Scrape"
      source: marvelstudios
      sort: new
  ```
  ```bash
  python reddit2md.py --task "Daily Marvel Scrape"
  ```

### `source` / `sources`
- **Before:** `source` accepted a single string. Multiple subreddits required
  separate routine entries, each generating a separate HTTP call.
- **After:** `source` or `sources` accepts a string or a list. A list produces
  one combined URL (`r/A+B+C`) and one HTTP call.
- **Also accepted (new aliases):** `subreddit`, `subreddits`, `reddit`, `reddits`
- **Status:** ⚡ CHANGED + 🆕 NEW aliases
- **Migration note:** Existing single-source configs work unchanged. Configs
  with multiple separate entries for the same subreddit group can optionally
  be consolidated into one entry with a list.

---

## 2. URL Construction

### How URLs are built
- **Before:** url_builder generated a simple browse URL for every task:
  `reddit.com/r/{source}/{sort}/.rss`
- **After:** url_builder selects the most appropriate URL mode:
  - **Browse** (real-time, no lag): used when no q= params needed
  - **Search without q=** (lag possible): used when `post_type` or `allow_nsfw` set
  - **Search with q=** (lag possible): used when any filter requires q=
- **Status:** ⚡ CHANGED (internal — existing simple configs produce identical URLs)

### `sort`
- **Before:** `new`, `hot`, `top`, `rising` — embedded in browse URL path
- **After:** Same values plus `relevance` and `comments` (search endpoint only).
  In search mode, sort moves from URL path to `sort=` parameter.
- **Status:** ⚡ CHANGED (expanded values, structural URL change in search mode)

### `time_filter` → `timeframe`
- **Before:** Called `time_filter`. Described incorrectly as "only useful with
  sort=top or sort=relevance."
- **After:** Called `timeframe` (`time_filter` still works as alias). Correctly
  documented as a pre-filter that works with ANY sort method.
- **Status:** 🔄 RENAMED + ⚡ CHANGED (corrected behavior description)

### `post_type`
- **Before:** Not supported.
- **After:** `post_type: link` or `post_type: self`. Filters to link posts or
  text posts respectively. Forces search mode (no q= needed, but path changes).
- **Status:** 🆕 NEW

### `allow_nsfw`
- **Before:** Not supported.
- **After:** `allow_nsfw: true/false`. Maps to `include_over_18=on/off`.
  Forces search mode (no q= needed, but path changes).
- **Status:** 🆕 NEW

---

## 3. Flair / Label Filtering

### `label` / `flair`
- **Before:** `label` was a post-fetch local filter only. Checked flair after
  posts were already fetched.
- **After:** `label` (alias: `flair`) now goes into the URL as `flair:value`
  in q=. Pre-filters at Reddit's side before the 25-cap applies. Forces search
  mode. Accepts a list for OR logic.
- **Status:** ⚡ CHANGED (moved from local to URL-level)

### `label_exact` / `flair_exact`
- **Before:** Called `exact_flair`. Translated to `flair_name:` in q=.
- **After:** Called `label_exact` (alias: `flair_exact`). When sort=new or
  unset, uses `f=flair_name:` on the browse endpoint — no lag, no q=.
  Falls back to `q=flair_name:` only when sort is not new.
- **Status:** 🔄 RENAMED + ⚡ CHANGED (browse-safe optimization)

### `exclude_label` / `exclude_flair`
- **Before:** Not supported.
- **After:** Adds `NOT flair:value` per entry into q=. Prevents posts with
  specified flair from appearing in results.
- **Status:** 🆕 NEW

---

## 4. Content Filtering

### `blacklist_terms` → `exclude_terms`
- **Before:** Called `blacklist_terms`. Ran locally only — filtered post titles
  after fetch.
- **After:** Called `exclude_terms`. All old aliases still work. Now runs in
  TWO places: as `NOT "term"` operators in q= (pre-fetch), AND still locally
  as a safety net (post-fetch). Best-of-both approach.
- **Status:** 🔄 RENAMED + ⚡ CHANGED (now also URL-level)

### `blacklist_urls` → `ignore_urls`
- **Before:** Called `blacklist_urls`. Stripped matching URLs from `post_links`
  frontmatter in markdown output.
- **After:** Called `ignore_urls`. Behavior unchanged. All old aliases work.
- **Status:** 🔄 RENAMED (behavior unchanged)

### `exclude_urls`
- **Before:** Not supported.
- **After:** Adds `NOT site:domain` per entry into q=. Prevents posts linking
  to specified domains from appearing in results entirely. Different from
  `ignore_urls` which only strips from frontmatter.
- **Status:** 🆕 NEW

### `exclude_author` / `exclude_authors`
- **Before:** Not supported.
- **After:** Adds `NOT author:username` per entry into q=. Prevents posts by
  specified users from appearing in results. Most useful for filtering bots.
- **Status:** 🆕 NEW

### `search` / `query`
- **Before:** Not supported as a structured key.
- **After:** Freeform Lucene-style string inserted as-is into q=. Appended
  last in q= assembly, after all structured keys. Supports full Reddit search
  syntax including field operators (author:, title:, site:, selftext: etc.)
  and boolean logic (AND, OR, NOT).
- **Status:** 🆕 NEW

---

## 5. Age / Time Filtering

### `min_age_hours` → `ignore_newer_than_hours`
- **Before:** Called `min_age_hours`. Posts younger than threshold were scraped
  immediately but marked for re-scrape. This was the maturity/rescrape logic.
- **After:** `min_age_hours` is now an alias for `ignore_newer_than_hours`.
  Behavior CHANGED: posts younger than this threshold are now DISCARDED entirely
  — not scraped, not tracked. This is pure local ignore behavior.
  The rescrape/maturity behavior has moved to `rescrape_newer_than_hours`.
- **Status:** 🔄 RENAMED + ⚡ CHANGED (behavior split into two separate params)
- **Migration critical:** If you relied on `min_age_hours` for the "scrape now,
  come back later" behavior, you must change to `rescrape_newer_than_hours`.

### `max_age_hours` → `ignore_older_than_hours`
- **Before:** Called `max_age_hours`. Ran locally, discarded posts too old.
  Also mapped to approximate `t=` bucket in URL.
- **After:** Called `ignore_older_than_hours` (alias: `max_age_hours`).
  Now local ONLY. No longer maps to t=. Use `timeframe` explicitly if you
  want URL-level time windowing.
- **Status:** 🔄 RENAMED + ⚡ CHANGED (t= mapping removed, local only)

### `rescrape_threshold_hours` → `rescrape_newer_than_hours`
- **Before:** Called `rescrape_threshold_hours`. Drove the maturity/rescrape
  scheduling — posts younger than threshold were scraped and marked for return.
- **After:** Called `rescrape_newer_than_hours`. Same behavior. All old aliases
  work. Now clearly distinct from `ignore_newer_than_hours`.
- **Status:** 🔄 RENAMED (behavior unchanged)

### `ignore_older_than_days` / `ignore_newer_than_days` / `rescrape_newer_than_days`
- **Before:** Not supported. Only `_hours` variants existed.
- **After:** `_days` variants accepted for all three. Converted to hours
  internally (×24). Convenience only.
- **Status:** 🆕 NEW

---

## 6. Score Filtering

### `min_score` → `ignore_below_score`
- **Before:** Called `min_score`. Ran locally, discarded posts below threshold.
- **After:** Called `ignore_below_score` (alias: `min_score`). Behavior unchanged.
- **Status:** 🔄 RENAMED (behavior unchanged)

---

## 7. Multi-Source Handling

### Multiple subreddits
- **Before:** Multiple sources required multiple routine entries. Each generated
  a separate HTTP call and separate URL.
- **After:** A single routine entry with `sources: [A, B, C]` generates one
  combined URL `r/A+B+C/.rss` and one HTTP call.
- **Status:** ⚡ CHANGED
- **To get old behavior:** List them as separate routine entries.

---

## 8. CLI Arguments

### `--source`
- **Before:** Ran ad-hoc task for a subreddit not necessarily in config.
- **After:** Same behavior, unchanged.
- **Status:** ✅ UNCHANGED

### `--task`
- **Before:** Not supported.
- **After:** Runs a named routine entry from config by name (case-insensitive).
- **Status:** 🆕 NEW

### New CLI arguments added
All new config parameters have corresponding CLI arguments:
`--task`, `--search`, `--label`, `--flair`, `--label-exact`, `--flair-exact`,
`--exclude-label`, `--exclude-flair`, `--exclude-terms`, `--exclude-urls`,
`--exclude-author`, `--ignore-urls`, `--ignore-older-than-hours`,
`--ignore-older-than-days`, `--ignore-newer-than-hours`,
`--ignore-newer-than-days`, `--rescrape-newer-than-hours`,
`--rescrape-newer-than-days`, `--ignore-below-score`, `--timeframe`,
`--post-type`, `--allow-nsfw`

### `--sort` expanded values
- **Before:** `new`, `hot`, `top`, `rising`
- **After:** Also accepts `relevance`, `comments` (search endpoint only)
- **Status:** ⚡ CHANGED (expanded)

---

## 9. Parameters Removed

### `exact_flair`
- **Before:** Structured config key.
- **After:** Removed. Use `label_exact` or `flair_exact`.
- **Status:** ❌ REMOVED (replaced by `label_exact`/`flair_exact`)

### `comment_contains`
- **Before:** Listed in some versions of the implementation guide.
- **After:** Not implemented. Not supported.
- **Status:** ❌ REMOVED (never fully implemented, dropped)

### `author`, `title`, `selftext`, `site` as structured keys
- **Before:** Partially planned as structured config keys.
- **After:** Not implemented as structured keys. Available only via the
  freeform `search` field using Reddit's operator syntax.
- **Status:** ❌ REMOVED from structured keys (available via `search`)

---

## 10. Parameters Unchanged

| Parameter | Notes |
|---|---|
| `detail` | XS/SM/MD/LG/XL comment depth presets — unchanged |
| `max_results` | Post limit per feed — unchanged |
| `offset` | Local list slicing — unchanged |
| `group_by_source` | Output folder logic — unchanged |
| `save_json` | JSON archive toggle — unchanged |
| `enable_md_log` | Scrape log toggle — unchanged |
| `md_log` | Log path — unchanged |
| `db_limit` | DB record cap — unchanged |
| `debug` | Debug mode toggle — unchanged |
| `verbose` | Output verbosity — unchanged |
| `data_output_directory` | Data dir path — unchanged |
| `md_output_directory` | Markdown output path — unchanged |

---

## 11. Exclude vs Ignore — New Conceptual Framework

This is a new organizing principle, not a breaking change. It clarifies the
intent behind parameter names:

**Exclude** = goes into the URL, filters at Reddit's side, reduces the 25-cap pool.
Requires search mode. May introduce indexing lag.

**Ignore** = runs locally after fetch, trims results we already received.
No URL implications. No lag. Always reliable.

All parameters are now named to reflect which category they belong to.
Parameters that cannot be expressed in a URL are never named `exclude_*`.
