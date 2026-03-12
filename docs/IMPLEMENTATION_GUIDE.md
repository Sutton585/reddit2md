# reddit2md Refactor — Complete Implementation Guide
# For AI Agent Developers

This document is the authoritative spec for completing the reddit2md URL builder refactor. It supersedes tasks.md and refactor.md entirely. It references "Fixing my refactor mistakes.md" (hereafter FMRM) by line number for supporting detail, and flags every place where that document contains outdated decisions that must NOT be followed.

---

## 0. Guiding Philosophy — Read First

**FMRM lines 7–8** defines the core principle:

> reddit2md operates a permissive translation layer. If we can reasonably interpret what the user meant, we accept it and translate silently. We never error on a recognizable input just because it isn't the preferred syntax.

This applies everywhere: field names, value formats, boolean representations. When in doubt, accept it and normalize it. The preferred syntax is what we show in docs. Everything else works without complaint.

---

## 1. Files to Modify

| File | Nature of change |
|---|---|
| `reddit2md/core/url_builder.py` | Significant rewrite of existing file |
| `reddit2md/core/config.py` | Add new keys, add alias normalization |
| `reddit2md/scraper.py` | Pass new fields to url_builder, update CLI args, add local filters |
| `README.md` | Surgical additions only — see Documentation Guide |

---

## 2. Corrections to Existing Code — Fix These First

These are bugs introduced by the previous refactor that must be resolved before adding new functionality.

### 2.1 Wrong flair operator in url_builder.py

The existing code uses `flair_text:` and `flair_name:` inside `q=`. Testing confirmed the correct operator is simply `flair:`. `flair_text:` is not in Reddit's official docs and must be replaced. Find and replace in `url_builder.py`: `flair_text:` → `flair:` (inside any q= string assembly). `flair_name:` inside `q=` stays as-is — it is used for exact match in search mode fallback only.

### 2.2 Group 2 structured keys to DROP

**FMRM lines 76–80** lists `author`, `title`, `selftext`, and `site` as structured config keys that translate to `q=` operators. **This decision was reversed.** These are NOT implemented as structured keys. They are available only via the freeform `search` field. Remove any implementation of these as named config keys.

### 2.3 `comment_contains` — DROP entirely

**FMRM line 98** lists `comment_contains` as a local filter. **This was dropped.** Do not implement it. Remove from config defaults if present.

### 2.4 `exact_flair` rename

Previous code used `exact_flair` as the parameter name. The correct names are `label_exact` (canonical) and `flair_exact` (alias). Rename throughout.

### 2.5 Source alias `source: "news+pics"` in tests

The existing url_builder tests include `source="movies+marvelstudios"` as a user-facing input. This is an internal URL detail that leaked into the API surface. Keep it working (it's valid input) but do not feature it in test labels or examples. The preferred test input is `sources=["movies", "marvelstudios"]`.

---

## 3. Parameter Map — The Complete Spec

### 3.1 Group 1 — URL-level, browse-safe

**Reference: FMRM lines 49–63** (base table, still accurate with corrections below)

These translate to URL parameters outside of `q=`. A task using ONLY these parameters stays on the browse endpoint with zero search lag.

| reddit2md key | Aliases | URL translation | Browse safe? |
|---|---|---|---|
| `source` | `sources`, `subreddit`, `subreddits`, `reddit`, `reddits` | base path `/r/A+B+C/` | ✅ |
| `sort` | — | path segment or `sort=` param | ✅ |
| `timeframe` | `time_filter` | `t=` | ✅ |
| `post_type` | — | `type=` | ⚠️ forces search endpoint, not q= |
| `allow_nsfw` | — | `include_over_18=` | ⚠️ forces search endpoint, not q= |
| `label_exact` / `flair_exact` | both accepted | `f=flair_name:` | ✅ when sort=new or unset |

**Critical note on `post_type` and `allow_nsfw`:** These are URL-level params that never touch `q=`, but they require the search endpoint. If a user sets either without any q= params, switch to search mode but leave `q=` absent entirely. See FMRM lines 62–63 for example URL.

**Critical note on `label_exact`/`flair_exact`:** Uses `f=flair_name:"value"` when sort is `new` or unset — this keeps the request on the browse endpoint (confirmed working in live testing). When any other sort value is specified, fall back to `q=flair_name:"value"` on the search endpoint.

**Critical note on `sort`:** Values `relevance` and `comments` only exist on the search endpoint. Setting either triggers search mode even if no other search params are present. See FMRM lines 83–85.

### 3.2 Group 2 — Requires `q=`, forces search mode

**Reference: FMRM lines 67–85** — NOTE: lines 76–80 are outdated. `author`, `title`, `selftext`, `site` listed there are NOT implemented as structured keys. Only the following are implemented.

| reddit2md key | Aliases | `q=` translation | Assembly order |
|---|---|---|---|
| `label` / `flair` | both accepted | `flair:"value"` | 1st |
| `label_exact` / `flair_exact` | both accepted | `flair_name:"value"` (search mode fallback only) | 1st |
| `exclude_label` / `exclude_flair` | both accepted | `NOT flair:value` per entry | 2nd |
| `exclude_terms` | `blacklist`, `blacklist_terms`, and others | `NOT "term"` per entry | 3rd |
| `exclude_urls` | `exclude_url` | `NOT site:domain` per entry | 4th |
| `exclude_author` | `exclude_authors` | `NOT author:name` per entry | 5th |
| `search` | `query` | inserted as-is, no parsing | last |

**Assembly rule:** Structured fields assembled in the order shown, `search`/`query` appended last. All joined with `AND`. No conflict detection — Reddit interprets any contradictions. See FMRM lines 10–11 and 38–44.

**`search`/`query` handling — critical:** Never parse, validate, or modify the value. URL-encode it with `urllib.parse.quote()` and insert as-is. See FMRM lines 13–15. Do not double-encode. A user who writes `search: 'title:beginner AND selftext:help'` gets exactly that expression in the URL — operators, colons, and all.

**`label`/`flair` list support:** If value is a list, produce OR logic: `flair:("Comics" OR "Movies")`. If a single string, produce `flair:"Comics"`.

**`exclude_terms` dual-layer behavior:** Each entry becomes `NOT "entry"` in q= AND still runs locally after fetch as a safety net. Do not remove the existing local filter in `scraper.py`. Both layers run intentionally — the URL layer maximizes the 25-result pool quality, the local layer catches anything that slipped through due to search index lag.

### 3.3 Group 3 — Local only, never in URL

**Reference: FMRM lines 89–107** — accurate except remove `comment_contains` (line 98, dropped).

| reddit2md key | Aliases | When it runs |
|---|---|---|
| `ignore_below_score` | `min_score` | After fetch, discards posts below threshold |
| `ignore_newer_than_hours/days` | `min_age_hours` | After fetch, discards posts too fresh — not scraped, not tracked |
| `ignore_older_than_hours/days` | `max_age_hours` | After fetch, discards posts too old — not scraped, not tracked |
| `rescrape_newer_than_hours/days` | `rescrape_threshold_hours`, `rescrape_threshold` | After fetch, marks young posts for a return visit |
| `ignore_urls` | `blacklist_urls`, `blacklist_url`, `ignore_url` | During markdown generation, strips from post_links frontmatter |
| `offset` | — | After RSS parse, slices first N from list |
| `detail` | — | During comment processing |
| `group_by_source` | — | During file output |
| `debug`, `verbose`, `save_json`, `enable_md_log`, `md_log`, `db_limit` | — | System behavior |

### 3.4 The ignore_newer_than / rescrape_newer_than distinction

These two parameters are easily confused because both deal with posts that are too fresh. The difference is whether the post gets discarded or kept.

`ignore_newer_than_hours: 24` means "if the post is less than 24 hours old, skip it entirely — don't scrape it, don't track it, move on." The post is gone from this run with no record in the database.

`rescrape_newer_than_hours: 24` means "if the post is less than 24 hours old, scrape it now but schedule a return visit — write `rescrape_after` into the frontmatter so the next run knows to append the mature discussion." The post is kept and tracked, but flagged.

A user who only ever wants mature, settled discussions should use `ignore_newer_than`. A user who wants the fresh post immediately AND wants to return for the mature follow-up should use `rescrape_newer_than`. Both can be set simultaneously with different thresholds — a post that is 22 hours old with `ignore_newer_than_hours: 20` and `rescrape_newer_than_hours: 24` passes the ignore check (22 > 20) and gets a rescrape mark (22 < 24). A post that is 18 hours old fails the ignore check (18 < 20) and is discarded before the rescrape check ever runs. See the worked example in section 11.5.

### 3.5 timeframe — the only URL-level time control

`timeframe` (alias: `time_filter`) maps directly to Reddit's `t=` parameter and is the only mechanism for pre-filtering posts by age at the URL level. Reddit has no URL operator for minimum post age — there is no way to tell Reddit "only show me posts older than X hours" in the URL. All minimum-age filtering is therefore local only.

`timeframe` accepts: `hour`, `day`, `week`, `month`, `year`, `all`. It works with any `sort` value, not just `top` — the Reddit UI implies otherwise, but `sort=new&t=week` is valid and produces newest posts from the past 7 days.

`ignore_older_than_hours` does NOT map to `t=`. It is purely local. If you want URL-level time windowing, set `timeframe` explicitly.

---

## 4. Source Field — Alias Normalization

**Reference: FMRM lines 126–142**

All of the following must be recognized and normalized to `source` before reaching URLBuilder. Normalization happens in `config.py` `get_task_config()`.

**Accepted aliases:** `source`, `sources`, `subreddit`, `subreddits`, `reddit`, `reddits`

**Priority if multiple appear in same task:** `source` > `sources` > `subreddit` > `subreddits` > `reddit` > `reddits`

**Accepted value formats — all produce the same result:**
```yaml
source: "MarvelComics"            # single string
sources: ["news", "pics"]         # list — preferred in docs
subreddit: "news"                 # alias, string
reddit: ["news", "pics"]          # alias, list
source: "news+pics"               # plus-joined string — support silently, don't document as preferred
```

URLBuilder receives `source` only. It never knows which alias was used. A list value is joined with `+` internally to form `r/A+B+C/` in the URL. The key insight here is that providing a list produces a single HTTP call to `r/A+B+C/.rss`, not one call per subreddit. This is a meaningful efficiency gain and is the correct behavior — do not loop over sources and make separate calls.

---

## 5. Mode Decision Tree

**Reference: FMRM lines 111–122** — updated with `f=` exception and sort trigger

```
sort=relevance or sort=comments?
    └─ Yes → SEARCH MODE (q= may or may not be populated)

Has label_exact/flair_exact?
    └─ Yes + sort=new or unset → f=flair_name: on BROWSE endpoint (no lag)
    └─ Yes + any other sort  → q=flair_name: on SEARCH endpoint

Has any q= param? (label/flair, exclude_label, exclude_terms, exclude_urls, exclude_author, search/query)
    └─ Yes → SEARCH endpoint, build q= string

Has post_type, allow_nsfw, or timeframe?
    └─ Yes → SEARCH endpoint, no q= string required

Nothing above?
    └─ BROWSE endpoint, sort in path: /r/sub/new/.rss
```

**Structural difference when switching to search mode:** The base path changes from `/r/sub/new/.rss` to `/r/sub/search.rss`. Sort moves from a path segment to a URL parameter (`sort=new`). `restrict_sr=on` is added automatically when source is specified. Everything else (`post_type`, `allow_nsfw`, `timeframe`) remains as URL params outside q=.

This is NOT a total architectural change. The goal at all times is to minimize what goes into `q=`. Parameters stay outside `q=` whenever Reddit supports it directly.

---

## 6. `config.py` Changes

### 6.1 New default keys to add

```python
# Task identity
"name": None,                       # optional human-readable name for CLI targeting

# URL-level, no q=
"post_type": None,                  # "link" | "self" | None
"allow_nsfw": False,                # include_over_18 toggle
"timeframe": None,                  # "hour"|"day"|"week"|"month"|"year"|"all" — alias: time_filter

# URL-level, forces q= (exclude group)
"search": None,                     # freeform Lucene string, alias: query
"label": None,                      # partial flair match, alias: flair
"label_exact": None,                # exact flair match, alias: flair_exact
"exclude_label": [],                # NOT flair:value per entry, alias: exclude_flair
"exclude_terms": [],                # NOT "term" per entry, aliases: blacklist, blacklist_terms, etc.
"exclude_urls": [],                 # NOT site:domain per entry, alias: exclude_url
"exclude_author": [],               # NOT author:name per entry, alias: exclude_authors

# Local only (ignore group)
"ignore_urls": [],                  # strips from post_links output — aliases: blacklist_urls, ignore_url
"ignore_below_score": None,         # alias: min_score
"ignore_older_than_hours": None,    # alias: max_age_hours
"ignore_older_than_days": None,     # converted to hours ×24 internally
"ignore_newer_than_hours": None,    # alias: min_age_hours
"ignore_newer_than_days": None,     # converted to hours ×24 internally
"rescrape_newer_than_hours": None,  # aliases: rescrape_threshold_hours, rescrape_threshold
"rescrape_newer_than_days": None,   # converted to hours ×24 internally
```

### 6.2 `get_task_config()` normalization

After merging settings + task_data, apply these normalizations in order:

1. **Source aliases** — collapse `subreddits`, `subreddit`, `reddit`, `reddits`, `sources` into `source`. See section 4 for priority.
2. **label/flair** — if `flair` is set and `label` is not, rename flair → label, remove flair key. URLBuilder only sees `label`.
3. **label_exact/flair_exact** — normalize to `label_exact`.
4. **exclude_label/exclude_flair** — normalize to `exclude_label`.
5. **exclude_terms and all blacklist aliases** — normalize to `exclude_terms`.
6. **exclude_author/exclude_authors** — normalize to `exclude_author`.
7. **ignore_urls and all blacklist_urls aliases** — normalize to `ignore_urls`.
8. **ignore_below_score/min_score** — normalize to `ignore_below_score`.
9. **timeframe/time_filter** — normalize to `timeframe`.
10. **max_age_hours** — normalize to `ignore_older_than_hours`.
11. **min_age_hours** — normalize to `ignore_newer_than_hours`.
12. **min_score** — normalize to `ignore_below_score`.
13. **rescrape_threshold_hours / rescrape_threshold** — normalize to `rescrape_newer_than_hours`.
14. **_days variants** — for `ignore_older_than_days`, `ignore_newer_than_days`, `rescrape_newer_than_days`: multiply by 24, store under canonical `_hours` key, remove `_days` key.
15. **search/query** — normalize to `search`. If both set, `search` wins.
16. **Single string to list** — any parameter that accepts a list (label, exclude_label, exclude_terms, exclude_urls, exclude_author, ignore_urls) must be wrapped in a list if the user provided a single string.

---

## 7. `url_builder.py` Changes

### 7.1 Method signature

```python
def build_rss_url(
    self,
    source=None,
    sort="new",
    timeframe=None,
    post_type=None,
    allow_nsfw=False,
    label=None,
    label_exact=None,
    exclude_label=None,
    exclude_terms=None,
    exclude_urls=None,
    exclude_author=None,
    search=None,
    **kwargs  # absorbs all other config keys safely
):
```

All alias normalization happens in `config.py` before this is called. URLBuilder only receives the canonical names listed above. All local-only parameters (`ignore_*`, `rescrape_*`, `ignore_below_score`) are NOT passed to url_builder — they are consumed entirely in `scraper.py`.

### 7.2 q= assembly method

Isolate all `q=` construction in a single private method `_build_q_string()`. This is the "advanced group" isolation principle — if the decision is ever made to drop structured q= keys, this one method is the only thing that changes.

Assembly order inside `_build_q_string()`:
1. `label` → `flair:"value"` or `flair:("A" OR "B")` for lists
2. `label_exact` → `flair_name:"value"` (only called when not using `f=`)
3. `exclude_label` → `NOT flair:value` per entry
4. `exclude_terms` → `NOT "term"` per entry, joined with AND
5. `exclude_urls` → `NOT site:domain` per entry
6. `exclude_author` → `NOT author:username` per entry
7. `search` → appended as-is, URL-encoded, never parsed or modified

If only `search` is set and nothing else, q= contains only the search value with no AND prefix. If no q= content is generated at all, omit `q=` from the URL entirely.

### 7.3 `restrict_sr=on`

Add automatically whenever `source` is specified AND mode is search. Never add it on browse URLs — it's redundant there and adds noise.

### 7.4 Updated test cases

All existing tests expecting `flair_text%3A` must be updated to `flair%3A`. Tests expecting `exact_flair` must be updated to `label_exact`. Add new tests covering:

- `label_exact` with sort=new → confirms `f=flair_name:` on browse endpoint
- `label_exact` with sort=top → confirms fallback to `q=flair_name:` on search endpoint
- `exclude_terms` as list → confirms NOT operators in q=
- `exclude_label` as list → confirms NOT flair: operators in q=
- `exclude_author` as list → confirms NOT author: operators in q=
- `exclude_urls` as list → confirms NOT site: operators in q=
- `search` + `label` combined → confirms correct assembly order, search appended last
- `sources` as list → confirms plus-joined in a single URL
- All six source alias formats → same URL output
- `post_type` only → confirms search endpoint with no q=
- `allow_nsfw` only → confirms search endpoint with no q=
- `sort=relevance` with no other params → confirms search endpoint with no q=

---

## 8. `scraper.py` Changes

### 8.1 `execute_task()` — url_builder call

Replace the current RSS URL construction with a call to `build_rss_url()`, passing all canonical URL-level keys:

```python
rss_url = self.url_builder.build_rss_url(
    source=config.get('source'),
    sort=config.get('sort', 'new'),
    timeframe=config.get('timeframe'),
    post_type=config.get('post_type'),
    allow_nsfw=config.get('allow_nsfw', False),
    label=config.get('label'),
    label_exact=config.get('label_exact'),
    exclude_label=config.get('exclude_label', []),
    exclude_terms=config.get('exclude_terms', []),
    exclude_urls=config.get('exclude_urls', []),
    exclude_author=config.get('exclude_author', []),
    search=config.get('search'),
)
```

### 8.2 Local filters in `_process_single_post()`

The local ignore filters all run here, after fetch, before any file is written. Apply in this order:

1. **`ignore_older_than_hours`** — compute post age. If age exceeds threshold, return False (skip entirely).
2. **`ignore_newer_than_hours`** — if age is less than threshold, return False (skip entirely).
3. **`ignore_below_score`** — if score below threshold, return False (skip entirely).
4. **`exclude_terms` local safety net** — if any term appears in post title, return False (skip entirely).
5. **`rescrape_newer_than_hours`** — if age is less than threshold, set `rescrape_after_iso = post_date + threshold`. Post proceeds to be scraped and written.

Note that `ignore_newer_than` and `rescrape_newer_than` can coexist with different thresholds. A post that is 22 hours old with `ignore_newer_than_hours: 20` and `rescrape_newer_than_hours: 24` passes the ignore check (22 > 20) and gets a rescrape mark (22 < 24). A post that is 18 hours old fails the ignore check (18 < 20) and is discarded before the rescrape check ever runs.

### 8.3 Named task targeting via CLI

Tasks in the routine can have an optional `name` field:

```yaml
routine:
  - name: "Marvel Comics Daily"
    source: MarvelStudiosSpoilers
    sort: new
    label: Spoiler
```

The CLI `--source` argument targets by subreddit name for ad-hoc runs. The new `--task` argument targets by name:

```bash
python reddit2md.py --task "Marvel Comics Daily"
```

**Implementation in `scraper.py` `run()`:**

```python
def run(self, source=None, task=None, overrides=None):
    if task:
        routine = [c for c in self.config_manager.get_all_routine_configs()
                   if c.get('name', '').lower() == task.lower()]
        if not routine:
            print(f"No task named '{task}' found in config.")
            return
    elif source:
        task_conf = self.config_manager.get_adhoc_task_config(source)
        routine = [task_conf]
    else:
        routine = self.config_manager.get_all_routine_configs()
```

Name matching is case-insensitive. If no match found, print a clear error rather than silently running nothing. `name` is metadata only — never used in URL construction, never written to any output file. If two tasks share a name, both run.

**CLI argument to add in `main()`:**
```python
parser.add_argument("--task", help="Run a specific named task from the config routine.")
```

### 8.4 New CLI arguments

```
--task                              Run a named routine task by name (case-insensitive)
--search / --query                  Freeform Lucene search string
--label / --flair                   Partial flair filter
--label-exact                       Exact flair filter (browse-safe when sort=new)
--exclude-label / --exclude-flair   Exclude by flair (NOT flair: in q=)
--exclude-terms                     Exclude by keyword (NOT "term" in q=)
--exclude-urls                      Exclude by domain (NOT site: in q=)
--exclude-author                    Exclude by author (NOT author: in q=)
--ignore-urls                       Strip domains from post_links output
--ignore-below-score                Discard posts below score threshold
--ignore-older-than-hours           Local only — discard posts too old
--ignore-older-than-days            Converted to hours internally
--ignore-newer-than-hours           Local only — discard posts too fresh
--ignore-newer-than-days            Converted to hours internally
--rescrape-newer-than-hours         Scrape now, mark for return visit
--rescrape-newer-than-days          Converted to hours internally
--timeframe                         URL-level time window: hour|day|week|month|year|all
--post-type                         link|self
--allow-nsfw                        Boolean
```

Both `--label` and `--flair` must be accepted by argparse and normalize to the same override key. Same for `--search` and `--query`.

---

## 9. Acceptance Criteria

A developer marks this complete when ALL of the following pass:

1. **Existing simple configs work unchanged.** A config with only `source` and `sort` produces the same browse URL as before. No regression.
2. **Flair operator is `flair:` not `flair_text:`** in all generated q= strings.
3. **All six source aliases** (`source`, `sources`, `subreddit`, `subreddits`, `reddit`, `reddits`) produce identical URLs for the same subreddit set.
4. **`sources` as a list** produces a single combined URL (`r/A+B+C`) — not multiple HTTP calls.
5. **`label_exact` with sort=new** produces `f=flair_name:` on the browse endpoint.
6. **`label_exact` with sort=top** produces `q=flair_name:` on the search endpoint.
7. **`exclude_terms` list** produces `NOT "a" AND NOT "b"` in q= AND still filters locally after fetch.
8. **`exclude_label` list** produces `NOT flair:a AND NOT flair:b` in q=.
9. **`exclude_author` list** produces `NOT author:a AND NOT author:b` in q=.
10. **`exclude_urls` list** produces `NOT site:a AND NOT site:b` in q=.
11. **`search` field** is inserted as-is, last in q= string, never parsed or modified.
12. **`author`, `title`, `selftext`, `site`** do NOT exist as structured config keys anywhere in the codebase.
13. **`comment_contains`** does not exist anywhere in the codebase.
14. **`ignore_older_than_hours`** accepted. Alias `max_age_hours` works identically. Local only — no t= implication.
15. **`ignore_newer_than_hours`** accepted. Alias `min_age_hours` works identically. Local only. Discards posts entirely — no rescrape scheduling.
16. **`rescrape_newer_than_hours`** accepted. Aliases `rescrape_threshold_hours` and `rescrape_threshold` work identically. Marks posts for return visit — does NOT discard.
17. **`timeframe`** accepted. Alias `time_filter` works identically. Direct t= URL param. Runs independently of all local time filters.
18. **The three-parameter interaction** works correctly: `timeframe: day` + `ignore_newer_than_hours: 20` + `rescrape_newer_than_hours: 24` produces posts 20–24h old, all marked for rescrape.
19. **`ignore_below_score`** accepted. Alias `min_score` works identically. Local only.
20. **`name` field** allows `--task "name"` CLI targeting, case-insensitive.
21. **url_builder standalone tests** all pass: `python -m reddit2md.core.url_builder`
22. **No new dependencies.** `urllib.parse` only.

---

## 10. Nomenclature Changes and Alias Normalization

This section defines all parameter renames introduced in this refactor. Every rename follows the same permissive alias pattern as `source`/`sources` — the old name always works, the new name is preferred in documentation. All normalization happens in `config.py` `get_task_config()` before anything reaches url_builder or scraper logic.

### 10.1 Full Alias Map

| Canonical name | Accepted aliases | Single or list? | Notes |
|---|---|---|---|
| `source` | `sources`, `subreddit`, `subreddits`, `reddit`, `reddits` | both | See section 4 |
| `label` | `flair` | both | Partial flair match, forces q= |
| `label_exact` | `flair_exact` | string | Exact flair, browse-safe when sort=new |
| `exclude_label` | `exclude_flair` | both | NEW — NOT flair: in q= |
| `exclude_terms` | `exclude`, `excludes`, `exclude_term`, `blacklist`, `blacklist_terms`, `blacklist_term`, `blacklists` | both | NOT "term" in q= + local safety net |
| `exclude_urls` | `exclude_url` | both | NEW — NOT site: in q= |
| `exclude_author` | `exclude_authors` | both | NEW — NOT author: in q= |
| `ignore_urls` | `ignore_url`, `blacklist_urls`, `blacklist_url` | both | Local only, strips from post_links output |
| `ignore_below_score` | `min_score` | int | Local only |
| `timeframe` | `time_filter` | string | t= URL param, direct |
| `ignore_older_than_hours` | `max_age_hours` | int | Local only — discard too-old posts |
| `ignore_older_than_days` | — | int | Converted to hours ×24 internally |
| `ignore_newer_than_hours` | `min_age_hours` | int | Local only — discard too-fresh posts |
| `ignore_newer_than_days` | — | int | Converted to hours ×24 internally |
| `rescrape_newer_than_hours` | `rescrape_threshold_hours`, `rescrape_threshold` | int | Local — scrape now, mark for return |
| `rescrape_newer_than_days` | `rescrape_threshold_days` | int | Converted to hours ×24 internally |

### 10.2 Normalization Rules

Apply in this order in `config.py` `get_task_config()` after merging settings and task data. Scan the merged config dict for any alias key. If found, rename to canonical, remove alias. If both canonical and alias are present simultaneously, canonical wins. If value is a single string and parameter accepts a list, wrap in list. If `_days` variant is used, multiply by 24, store under canonical `_hours` key, remove the `_days` key.

---

## 11. Exclude vs Ignore — Core Design Concept

This is the fundamental filtering distinction in reddit2md. Every filter parameter belongs to exactly one category. Understanding this determines where in the system a parameter lives and what it can affect.

### 11.1 The Rule

**Exclude** = incorporated into the RSS URL before any fetch. Reduces the quality of the 25-result pool at Reddit's side. Requires q= or a dedicated URL parameter. May introduce search lag because it forces the search endpoint. Reddit does the filtering. We get better results from the 25-cap.

**Ignore** = applied locally after the RSS fetch returns. Does not affect the 25-result pool size or composition. Always reliable. No lag implications. We do the filtering on whatever Reddit returned.

The practical goal: exclude as much as possible in the URL to maximize the quality of the 25 results, then use ignore as a safety net or for anything that has no URL equivalent.

### 11.2 What Can and Cannot Be Excluded

Reddit's q= parameter supports NOT operators for content-based filtering. Reddit does NOT support any age-based filtering in q= or any other URL parameter beyond the coarse `t=` bucket via `timeframe`. This is a hard Reddit limitation — there is no `age:` operator, no timestamp operator, nothing. All precise age filtering is therefore local.

**Can be excluded (URL-level, q= NOT operators):**

| Parameter | q= translation |
|---|---|
| `exclude_terms` | `NOT "term"` per entry |
| `exclude_urls` | `NOT site:domain` per entry |
| `exclude_label` / `exclude_flair` | `NOT flair:value` per entry |
| `exclude_author` | `NOT author:username` per entry |

All of the above force q= inclusion and therefore search mode. `exclude_terms` also runs locally as a safety net — both layers intentionally.

**Cannot be excluded — local only:**

| Parameter | Why URL is impossible |
|---|---|
| `ignore_older_than` | Reddit has no max-age URL operator |
| `ignore_newer_than` | Reddit has no min-age URL operator |
| `ignore_below_score` | `score:>X` in q= is unreliable per Reddit |
| `ignore_urls` | Filters link content inside posts, not which posts appear |

### 11.3 New Exclude Parameters

**`exclude_urls`** (alias: `exclude_url`) prevents posts linking to specified domains from appearing in results. This is completely different from `ignore_urls`, which only strips those URLs from the `post_links` frontmatter in the generated markdown. A user can and often should set both simultaneously:

```yaml
exclude_urls: ["imgur.com"]          # imgur posts never appear in RSS results
ignore_urls: ["reddit.com/r/x/wiki"] # wiki links stripped from markdown output only
```

**`exclude_label` / `exclude_flair`** prevents posts with specified flair from appearing in results. Particularly useful when combined with `label` to include one flair category and exclude another:

```yaml
label: "Discussion"
exclude_label: ["Megathread", "Weekly"]
```

**`exclude_author`** prevents posts by specified users from appearing in results. The most common use case is filtering out bot accounts. Because AutoModerator posts appear in nearly every active subreddit's /new feed, this is one of the most practically useful new parameters:

```yaml
exclude_author: ["AutoModerator", "BotAccount"]
```

### 11.4 Time Parameters — All Local (Ignore)

There is no age-based exclude. Because Reddit has no age operator for URLs, the "exclude" prefix is never used for age parameters — it would imply URL-level filtering that does not exist.

**`timeframe`** (alias: `time_filter`) is the ONLY URL-level time control. It maps directly to `t=` and accepts coarse buckets only: `hour`, `day`, `week`, `month`, `year`, `all`. It runs independently of all local time filters — setting both `timeframe` and `ignore_older_than_hours` means both run, each doing their own job. `timeframe` narrows the pool before fetch; `ignore_older_than_hours` trims the local results with precision after fetch.

**`ignore_older_than_hours/days`** (alias: `max_age_hours`) discards posts older than this threshold after fetch. Not scraped, not tracked, not written to disk.

**`ignore_newer_than_hours/days`** (alias: `min_age_hours`) discards posts younger than this threshold after fetch. Not scraped, not tracked, not written to disk. This is a hard discard — use `rescrape_newer_than_hours` instead if you want to keep the post and revisit it later.

**`rescrape_newer_than_hours/days`** (aliases: `rescrape_threshold_hours`, `rescrape_threshold`) scrapes the post now but writes a `rescrape_after` timestamp into its frontmatter. On a future run when that timestamp has passed, the system returns and appends the mature discussion as a new `## Updated Comments` section. This is the "living note" / maturity feature.

**Full time-parameter reference:**

| Parameter | URL? | Local? | Behavior |
|---|---|---|---|
| `timeframe` | ✅ direct t= | ❌ | Coarse time window — the only URL-level time control |
| `ignore_older_than_hours/days` | ❌ | ✅ discard | Posts too old — thrown away entirely |
| `ignore_newer_than_hours/days` | ❌ | ✅ discard | Posts too fresh — thrown away entirely |
| `rescrape_newer_than_hours/days` | ❌ | ✅ rescrape mark | Posts too fresh — kept now, revisited later |

### 11.5 How the Three Time Parameters Interact — Worked Example

This example is the canonical illustration of time parameter interaction and must appear verbatim in the README. See Documentation Guide section for placement.

```yaml
source: marvelstudios
timeframe: day                    # t=day in URL — Reddit returns posts from past 24h only
ignore_newer_than_hours: 20       # local — discard anything under 20h old
rescrape_newer_than_hours: 24     # local — anything under 24h old gets a rescrape mark
```

What happens step by step:

1. URL is built with `t=day` — Reddit returns up to 25 posts from the past 24 hours
2. Local: any post older than 20 hours is discarded entirely — not scraped, not tracked
3. Local: every surviving post is under 20 hours old, which is under the `rescrape_newer_than` threshold of 24 hours, so **every single surviving post gets a rescrape mark**
4. On the next run, those posts are revisited and the mature discussion is appended

Net effect: you collect only posts in the 0–20h window, and you automatically return to all of them when they mature. No manual tracking needed.

What each parameter contributes individually: `timeframe: day` does the coarse URL-level work so no posts older than 24h ever arrive locally. `ignore_newer_than_hours: 20` does the precise local trim, discarding the 20–24h window that came through `t=day` but is outside the acceptable range. `rescrape_newer_than_hours: 24` ensures everything that survived (all under 20h old) gets scheduled for a return visit.

Note on the overlap: because the surviving window is 0–20h and the rescrape threshold is 24h, 100% of surviving posts fall under the rescrape threshold. This is intentional — the user is saying "I only want fresh posts, and I want to return to all of them when they're mature."

### 11.6 Updated q= Assembly Order

Full assembly order in `_build_q_string()`:

1. `label` → `flair:"value"` or `flair:("A" OR "B")` for lists
2. `label_exact` → `flair_name:"value"` (search mode fallback only, not when f= is active)
3. `exclude_label` / `exclude_flair` → `NOT flair:value` per entry
4. `exclude_terms` → `NOT "term"` per entry
5. `exclude_urls` → `NOT site:domain` per entry
6. `exclude_author` → `NOT author:username` per entry
7. `search` / `query` → appended as-is, last, never parsed

All parts joined with `AND`. If only `search` is set and nothing else, q= contains only the search value with no AND prefix.

---

## 12. Out of Scope — Do Not Implement Now

These are documented for future reference only.

- **Pagination via `after=`** — See FMRM lines 144–156. Viable future feature. Current `offset` (local list slicing of the 25 results) is not the same thing and must not be conflated with true Reddit pagination. Mark for future dev.
- **`score:>X` in q=** — Unreliable per Reddit's own behavior. Not implemented as a structured key. Available in raw `search` string at user's own risk.
- **`selftext` as structured key** — Dropped. Available via `search` field using Reddit's `selftext:` operator.
- **`site` as structured key** — Dropped. Available via `search` field using Reddit's `site:` operator.
- **`author` as positive structured key** — Dropped. Available via `search` field using `author:username`. Note that `exclude_author` IS implemented as a structured key because filtering out bots is a far more common need than only-posts-by-one-user, and the list format is much cleaner than manually writing `AND NOT author:botname` in the `search` field.
