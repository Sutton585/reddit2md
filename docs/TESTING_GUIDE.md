# reddit2md Refactor — Testing & Validation Guide

This document defines how to verify that the refactored reddit2md behaves exactly as specified. Each test has an isolated output folder, a clear expected URL, and explicit success and failure signals.

---

## Setup: Two Important Prerequisites

### 1. Isolated output folders per test

Every test task specifies its own `md_output_directory`. This prevents the tracking database from seeing a post as "already scraped" and skipping it when a second task targets the same subreddit. Each folder is independent, and results are easy to audit by folder name.

### 2. The `track` flag — disable the database for repeat testing

Add support for a `track: false` setting on any task. When set, the task does not read from or write to the SQLite database — every run of that task is treated as fresh. This is essential for testing: without it, the first run of `r/python` writes posts to the DB, and every subsequent run (even in a different folder) skips them because they already exist.

**Implementation note:** In `_process_single_post()`, if `config.get('track', True)` is `False`, skip the `db_manager.post_exists()` check and the `db_manager.add_or_update_post()` call. The markdown file is still written. The DB is untouched.

All test tasks in this guide use `track: false` so they can be re-run freely.

---

## How to Run Any Test

Run a single named task:
```bash
python reddit2md.py --config tests/config_test.yml --task "TEST-A1" --debug true
```

Run all tests:
```bash
python reddit2md.py --config tests/config_test.yml --debug true
```

Check the URL that was generated (requires `verbose: 2` in settings):
```
stdout: Fetching RSS feed: https://www.reddit.com/r/...
```

Inspect output:
```bash
ls data/tests/A1-browse/
ls data/tests/B1-multi-source/
```

---

## The Test Config

Save as `tests/config_test.yml`.

```yaml
settings:
  debug: true
  verbose: 2
  save_json: false
  detail: XS
  enable_md_log: false

routine:

  # ══════════════════════════════════════════════════
  # BLOCK A — URL Mode Selection
  # ══════════════════════════════════════════════════

  - name: "TEST-A1"
    source: python
    sort: new
    max_results: 3
    track: false
    md_output_directory: data/tests/A1-browse

  - name: "TEST-A2"
    source: python
    sort: new
    label: "Help"
    max_results: 5
    track: false
    md_output_directory: data/tests/A2-label-search

  - name: "TEST-A3"
    source: learnpython
    sort: new
    label_exact: "Help"
    max_results: 5
    track: false
    md_output_directory: data/tests/A3-label-exact-browse

  - name: "TEST-A4"
    source: learnpython
    sort: top
    timeframe: week
    label_exact: "Help"
    max_results: 5
    track: false
    md_output_directory: data/tests/A4-label-exact-search

  - name: "TEST-A5"
    source: worldnews
    sort: new
    post_type: self
    max_results: 5
    track: false
    md_output_directory: data/tests/A5-post-type

  - name: "TEST-A6"
    source: movies
    sort: new
    allow_nsfw: true
    max_results: 3
    track: false
    md_output_directory: data/tests/A6-nsfw

  # ══════════════════════════════════════════════════
  # BLOCK B — Multi-source and Source Alias Formats
  # ══════════════════════════════════════════════════

  - name: "TEST-B1"
    sources:
      - movies
      - marvelstudios
    sort: new
    max_results: 5
    track: false
    md_output_directory: data/tests/B1-multi-source

  - name: "TEST-B2"
    subreddit: python
    sort: new
    max_results: 3
    track: false
    md_output_directory: data/tests/B2-alias-subreddit

  - name: "TEST-B3"
    reddits:
      - python
    sort: new
    max_results: 3
    track: false
    md_output_directory: data/tests/B3-alias-reddits

  # ══════════════════════════════════════════════════
  # BLOCK C — Exclude Parameters (URL-level q=)
  # ══════════════════════════════════════════════════

  - name: "TEST-C1"
    source: technology
    sort: new
    exclude_terms: ["AI", "artificial intelligence"]
    max_results: 10
    track: false
    md_output_directory: data/tests/C1-exclude-terms

  - name: "TEST-C2"
    source: formula1
    sort: new
    exclude_author: ["AutoModerator"]
    max_results: 10
    track: false
    md_output_directory: data/tests/C2-exclude-author

  - name: "TEST-C3"
    source: worldnews
    sort: new
    exclude_urls: ["youtube.com", "twitter.com"]
    max_results: 5
    track: false
    md_output_directory: data/tests/C3-exclude-urls

  - name: "TEST-C4"
    source: movies
    sort: new
    label: "Discussion"
    exclude_label: ["News", "Trailer"]
    max_results: 5
    track: false
    md_output_directory: data/tests/C4-exclude-label

  # ══════════════════════════════════════════════════
  # BLOCK D — Ignore Parameters (local only)
  # ══════════════════════════════════════════════════

  - name: "TEST-D1"
    source: news
    sort: new
    ignore_older_than_hours: 6
    max_results: 10
    track: false
    md_output_directory: data/tests/D1-ignore-older

  - name: "TEST-D2"
    source: news
    sort: new
    ignore_newer_than_hours: 4
    max_results: 10
    track: false
    md_output_directory: data/tests/D2-ignore-newer

  - name: "TEST-D3"
    source: askreddit
    sort: new
    ignore_below_score: 100
    max_results: 10
    track: false
    md_output_directory: data/tests/D3-ignore-score

  # ══════════════════════════════════════════════════
  # BLOCK E — Rescrape / Maturity Logic
  # ══════════════════════════════════════════════════

  - name: "TEST-E1"
    source: worldnews
    sort: new
    rescrape_newer_than_hours: 48
    max_results: 5
    track: true
    md_output_directory: data/tests/E1-rescrape-mark

  - name: "TEST-E2"
    source: marvelstudios
    sort: new
    timeframe: day
    ignore_newer_than_hours: 20
    rescrape_newer_than_hours: 24
    max_results: 10
    track: true
    md_output_directory: data/tests/E2-three-param-interaction

  # ══════════════════════════════════════════════════
  # BLOCK F — timeframe
  # ══════════════════════════════════════════════════

  - name: "TEST-F1"
    source: dataisbeautiful
    sort: new
    timeframe: week
    max_results: 5
    track: false
    md_output_directory: data/tests/F1-timeframe-new

  - name: "TEST-F2"
    source: dataisbeautiful
    sort: top
    timeframe: month
    max_results: 5
    track: false
    md_output_directory: data/tests/F2-timeframe-top

  # ══════════════════════════════════════════════════
  # BLOCK G — search field (freeform Lucene)
  # ══════════════════════════════════════════════════

  - name: "TEST-G1"
    source: learnpython
    sort: relevance
    search: "title:beginner"
    max_results: 5
    track: false
    md_output_directory: data/tests/G1-search

  # ══════════════════════════════════════════════════
  # BLOCK H — Named task and alias normalization
  # ══════════════════════════════════════════════════

  - name: "TEST-H1"
    source: python
    sort: hot
    max_results: 2
    track: false
    md_output_directory: data/tests/H1-named-task

  - name: "TEST-H2"
    subreddit: programming
    sort: new
    blacklist_terms: ["hiring", "jobs"]
    min_score: 50
    max_age_hours: 72
    rescrape_threshold_hours: 48
    max_results: 5
    track: false
    md_output_directory: data/tests/H2-alias-normalization
```

---

## Test-by-Test Validation

For each test: run it, check the URL in stdout, check the output folder, verify the signals listed.

---

### BLOCK A — URL Mode Selection

---

**TEST-A1 — Pure browse mode**

Expected URL in stdout:
```
https://www.reddit.com/r/python/new/.rss
```

✅ **Success:** URL contains no `search.rss`, no `?q=`, no `sort=` parameter. Up to 3 markdown files in `data/tests/A1-browse/`.

❌ **Failure signal — URL contains `search.rss`:** url_builder switched to search mode for no reason. Check the mode decision tree.

❌ **Failure signal — Zero files:** Network issue or r/python returned nothing. Verify internet access and try a larger subreddit like r/news.

---

**TEST-A2 — label forces q= and search endpoint**

Expected URL in stdout:
```
https://www.reddit.com/r/python/search.rss?q=flair%3A%22Help%22&restrict_sr=on&sort=new
```

✅ **Success:** URL contains `search.rss`, `q=flair%3A`, `restrict_sr=on`, `sort=new`. Files in `data/tests/A2-label-search/`. Frontmatter `label:` field in generated files should match or be close to "Help".

❌ **Failure signal — Browse URL:** `label` didn't trigger search mode. Check mode decision tree in url_builder.

❌ **Failure signal — `flair_text%3A` in URL instead of `flair%3A`:** Bug 2.1 not fixed. The `flair_text:` operator must be replaced with `flair:`.

❌ **Failure signal — Files have totally unrelated flair:** `flair:` operator not working. Zero results is also possible if r/python doesn't use this flair — verify in browser before assuming bug.

---

**TEST-A3 — label_exact with sort=new stays on browse endpoint**

Expected URL in stdout:
```
https://www.reddit.com/r/learnpython/new/.rss?f=flair_name%3A%22Help%22
```

✅ **Success:** URL is still `.rss` (browse mode), not `search.rss`. The `f=` parameter is appended to the browse URL. Files appear in `data/tests/A3-label-exact-browse/`.

❌ **Failure signal — URL uses `search.rss`:** The f= browse optimization wasn't applied for sort=new. Check the label_exact branch in the mode decision tree.

❌ **Failure signal — `f=flair_text:` instead of `f=flair_name:`:** Wrong operator for the f= parameter specifically.

❌ **Failure signal — `q=` in URL instead of `f=`:** label_exact is going through q= even though sort=new qualifies for the f= shortcut.

---

**TEST-A4 — label_exact with sort=top falls back to q= on search endpoint**

Expected URL in stdout:
```
https://www.reddit.com/r/learnpython/search.rss?q=flair_name%3A%22Help%22&restrict_sr=on&sort=top&t=week
```

✅ **Success:** `search.rss`, `q=flair_name%3A`, `sort=top`, `t=week`. This is the fallback path — sort=top cannot use f=.

❌ **Failure signal — Browse URL with f=:** The f= optimization was incorrectly applied even though sort=top was specified. f= disables sort control entirely in browse mode.

❌ **Failure signal — No `t=week`:** `timeframe: week` not passed to URL.

---

**TEST-A5 — post_type forces search endpoint with no q=**

Expected URL in stdout:
```
https://www.reddit.com/r/worldnews/search.rss?restrict_sr=on&sort=new&type=self
```

✅ **Success:** `search.rss` present. `type=self` present. No `q=` anywhere in URL. Files in folder should be text posts only (no link posts — verify by checking that `url_overridden_by_dest` is empty or absent in a few files).

❌ **Failure signal — Browse URL:** `post_type` didn't force search mode.

❌ **Failure signal — `type=` missing:** `post_type` reached the mode decision but wasn't added to URL params.

❌ **Failure signal — `q=` appears in URL:** `post_type` went into q= instead of as a URL param.

---

**TEST-A6 — allow_nsfw forces search endpoint with no q=**

Expected URL in stdout:
```
https://www.reddit.com/r/movies/search.rss?restrict_sr=on&sort=new&include_over_18=on
```

✅ **Success:** `search.rss` present. `include_over_18=on` present. No `q=`.

❌ **Failure signal — `include_over_18` missing:** `allow_nsfw: true` not translated.

---

### BLOCK B — Multi-source and Source Alias Formats

---

**TEST-B1 — Multi-source produces single combined URL**

Expected URL in stdout:
```
https://www.reddit.com/r/movies+marvelstudios/new/.rss
```

Stdout should show exactly ONE "Fetching RSS feed" line, not two.

✅ **Success:** Single URL with `+` joining the subreddits. Files in `data/tests/B1-multi-source/`. Check frontmatter `source:` field across files — some should say `r/movies`, others `r/marvelstudios`, confirming both subreddits are represented.

❌ **Failure signal — Two separate "Fetching RSS feed" lines:** url_builder looped over sources instead of combining them. This is a core correctness failure.

❌ **Failure signal — Only one subreddit's posts appear:** The `+` syntax generated but Reddit only returned one subreddit's results. This is a Reddit behavior issue, not a bug — verify by opening the URL in a browser.

---

**TEST-B2 vs TEST-B3 vs TEST-A1 — Source alias formats produce identical URLs**

A1 uses `source: python`, B2 uses `subreddit: python`, B3 uses `reddits: [python]`.

All three should produce:
```
https://www.reddit.com/r/python/new/.rss
```

✅ **Success:** All three stdout URLs are identical.

❌ **Failure signal — B2 or B3 produce a different URL or error:** Alias normalization not working for that alias.

❌ **Failure signal — B3 produces `r/python%2C/new/.rss` or similar:** List-to-string conversion not handled correctly.

---

### BLOCK C — Exclude Parameters

---

**TEST-C1 — exclude_terms goes into q= AND filters locally**

Expected URL contains:
```
q=NOT+%22AI%22+AND+NOT+%22artificial+intelligence%22
```

✅ **Success:** Both NOT operators visible in URL. Open r/technology/new in a browser — AI posts are everywhere. Check generated files: none should have "AI" or "artificial intelligence" in their title.

❌ **Failure signal — URL contains no NOT operators:** `exclude_terms` not reaching q=.

❌ **Failure signal — Files contain AI-related titles:** Either the URL layer failed OR the local safety net failed. Check which by comparing the URL to the files.

❌ **Failure signal — URL shows `NOT+AI` without quotes:** Terms with spaces or common words should be quoted. Short single words like "AI" may not need quotes but the implementation should quote all entries for consistency.

---

**TEST-C2 — exclude_author filters AutoModerator**

Expected URL contains:
```
NOT+author%3AAutoModerator
```

✅ **Success:** AutoModerator appears in NOT operator in URL. Verify by browsing r/formula1/new — AutoModerator posts nearly always appear there. Generated files in `data/tests/C2-exclude-author/` should contain zero AutoModerator posts (check `poster:` field in frontmatter).

❌ **Failure signal — AutoModerator post appears in output:** Either the URL layer failed (check URL) or posts are being written despite the NOT operator. If the URL looks correct, it may be a Reddit search index lag issue — try the test later.

❌ **Failure signal — `author%3A` present but wrong formatting:** Check that it's `NOT+author%3AAutoModerator` not `NOT+%22author%3AAutoModerator%22` (the field operator should not be quoted, only the value would be if it had spaces).

---

**TEST-C3 — exclude_urls prevents youtube and twitter posts**

Expected URL contains:
```
NOT+site%3Ayoutube.com+AND+NOT+site%3Atwitter.com
```

✅ **Success:** Both NOT site: operators in URL. Check generated files: look at `post_links:` in frontmatter — no youtube.com or twitter.com domains should appear.

❌ **Failure signal — youtube/twitter links appear in post_links:** The URL layer may have worked but `ignore_urls` does post_links filtering, not `exclude_urls`. These are two different things. If youtube.com appears in post_links, it means the post got through the URL filter (check if the post body just mentions YouTube without linking) — that's different from the URL having a youtube link as the primary post link.

---

**TEST-C4 — exclude_label combined with label**

Expected URL q= contains:
```
flair%3A%22Discussion%22+AND+NOT+flair%3ANews+AND+NOT+flair%3ATrailer
```

✅ **Success:** Both `flair:` (positive) and `NOT flair:` (negative) operators present. Files should have Discussion flair and should not have News or Trailer flair.

❌ **Failure signal — Only the label appears, no NOT flair:** `exclude_label` not reaching q= assembly.

❌ **Failure signal — Assembly order wrong:** `NOT flair:` operators appear before `flair:` operator. Order matters for readability and predictability even if Reddit accepts any order.

---

### BLOCK D — Ignore Parameters

---

**TEST-D1 — ignore_older_than discards stale posts**

Expected URL: browse mode, no `t=` (ignore parameters don't affect the URL).
```
https://www.reddit.com/r/news/new/.rss
```

✅ **Success:** URL has no `t=` param. Files in `data/tests/D1-ignore-older/` all have `date_posted:` within the past 6 hours. Verify by checking each frontmatter timestamp against current time.

❌ **Failure signal — Files with date_posted older than 6h:** Local ignore check not running.

❌ **Failure signal — URL contains `t=`:** `ignore_older_than` incorrectly mapped to the URL. It must be local only.

❌ **Failure signal — Zero files:** Either r/news is slow or the 6h window is genuinely empty. Widen to `ignore_older_than_hours: 12` to verify the parameter is working at all.

---

**TEST-D2 — ignore_newer_than discards fresh posts**

Expected URL: browse mode, no `t=`.

✅ **Success:** All files in `data/tests/D2-ignore-newer/` have `date_posted:` at least 4 hours ago.

❌ **Failure signal — Files with date_posted less than 4h ago:** `ignore_newer_than_hours` not running.

❌ **Failure signal — Same files appear in D1 and D2:** The two tests may overlap if posts happen to be in the 4–6h window. This is expected — it's not a bug.

---

**TEST-D3 — ignore_below_score discards low-score posts**

✅ **Success:** Every file in `data/tests/D3-ignore-score/` has `score: 100` or higher in frontmatter.

❌ **Failure signal — A file exists with score below 100:** `ignore_below_score` not running.

❌ **Failure signal — Zero files:** r/askreddit/new with `ignore_below_score: 100` will likely produce zero results since new posts start at low scores. Switch to `sort: hot` or lower the threshold to 10 to verify the filter works without producing nothing.

---

### BLOCK E — Rescrape / Maturity Logic

These tests use `track: true` so the database is engaged and rescrape_after timestamps are persisted.

---

**TEST-E1 — rescrape_newer_than marks posts**

r/worldnews/new returns mostly posts under 48h old.

After running:
```bash
sqlite3 data/database.db "SELECT id, title, rescrape_after FROM posts WHERE rescrape_after IS NOT NULL ORDER BY last_scrape_timestamp DESC LIMIT 10;"
```

✅ **Success:** Most or all posts from this task have a non-null `rescrape_after`. Check that `rescrape_after` is approximately `post_date + 48h` for a few posts by comparing to `date_posted:` in the frontmatter files.

✅ Also check frontmatter directly: open a file in `data/tests/E1-rescrape-mark/` and confirm `rescrape_after:` appears.

❌ **Failure signal — `rescrape_after` absent from frontmatter and database:** `rescrape_newer_than_hours` not running.

❌ **Failure signal — Some posts have rescrape_after, some don't:** The threshold comparison has a bug. Posts older than 48h would correctly have no rescrape mark — but r/worldnews/new should not have many posts older than 48h.

---

**TEST-E2 — The canonical three-parameter interaction**

This is the most important test in the set.

After running, check three things in sequence:

**Step 1 — URL:**
```
https://www.reddit.com/r/marvelstudios/search.rss?restrict_sr=on&sort=new&t=day
```
`t=day` must be present (from `timeframe: day`). The URL should NOT contain any `q=` since no exclude params were set. Notice that `timeframe` forces the `search.rss` endpoint even with `sort=new`.

**Step 2 — Files in `data/tests/E2-three-param-interaction/`:**
Open a few files and check `date_posted:`. All dates should fall between 20 and 24 hours ago. Nothing newer than 20h (those were discarded by `ignore_newer_than_hours: 20`). Nothing older than 24h (those never arrived due to `t=day`, and would have been discarded locally too).

**Step 3 — Database:**
```bash
sqlite3 data/database.db "SELECT id, post_timestamp, rescrape_after FROM posts WHERE file_path LIKE '%E2%';"
```
Every row should have `rescrape_after` set, because all surviving posts are under 24 hours old (within the `rescrape_newer_than_hours: 24` window).

✅ **Full success:** All three checks pass. This confirms `timeframe`, `ignore_newer_than`, and `rescrape_newer_than` are all working and interacting correctly.

❌ **Failure signal — `t=day` absent from URL:** `timeframe: day` not reaching url_builder.

❌ **Failure signal — Posts under 20h old appear in files:** `ignore_newer_than_hours: 20` not running.

❌ **Failure signal — `rescrape_after` absent from some rows:** `rescrape_newer_than_hours: 24` not running, or the threshold comparison is wrong direction.

❌ **Failure signal — Zero files:** The 20–24h window may be genuinely empty for r/marvelstudios. Widen to `ignore_newer_than_hours: 4` and `rescrape_newer_than_hours: 24` to get results while still verifying the interaction.

---

### BLOCK F — timeframe

---

**TEST-F1 — timeframe works with sort=new**

Expected URL:
```
https://www.reddit.com/r/dataisbeautiful/search.rss?restrict_sr=on&sort=new&t=week
```

✅ **Success:** `t=week` present even though sort=new. This confirms `timeframe` works with all sort values, not just sort=top. Check `date_posted:` in files — all should be within the past 7 days.

❌ **Failure signal — `t=week` absent:** `timeframe` not applied when sort=new.

❌ **Failure signal — Browse URL instead of search:** `timeframe` must force the search endpoint. Reddit ignores `t=` on the browse endpoint completely.

---

**TEST-F2 — timeframe with sort=top**

Expected URL:
```
https://www.reddit.com/r/dataisbeautiful/search.rss?restrict_sr=on&sort=top&t=month
```

✅ **Success:** Compare scores between F1 and F2 output files. F2 (sort=top, timeframe=month) should have noticeably higher scores — these are the top posts of the past month.

---

### BLOCK G — freeform search

---

**TEST-G1 — search field inserted as-is**

Expected URL contains:
```
q=title%3Abeginner
```

✅ **Success:** The `title:` field operator is preserved and URL-encoded. Results should be posts with "beginner" in the title. Open a few files and verify the titles contain "beginner".

❌ **Failure signal — `%253A` in URL instead of `%3A`:** Double-encoding. The colon was encoded twice. `urllib.parse.quote()` should be called once on the full search string.

❌ **Failure signal — `title:` was stripped or modified:** The search field was parsed instead of passed through as-is.

---

### BLOCK H — Named task and alias normalization

---

**TEST-H1 — Named task CLI targeting**

Run with explicit task name:
```bash
python reddit2md.py --config tests/config_test.yml --task "TEST-H1" --debug true
```

✅ **Success:** Only the H1 task runs. Stdout shows only one task executing. Files appear in `data/tests/H1-named-task/`.

Test case-insensitivity:
```bash
python reddit2md.py --config tests/config_test.yml --task "test-h1" --debug true
```

✅ **Success:** Same result. Task matched despite lowercase.

Test no-match behavior:
```bash
python reddit2md.py --config tests/config_test.yml --task "NONEXISTENT" --debug true
```

✅ **Success:** Prints `No task named 'NONEXISTENT' found in config.` and exits cleanly. No tasks run.

❌ **Failure signal — All tasks run when --task is specified:** Task filtering not implemented.

❌ **Failure signal — Partial names match:** `--task "TEST"` should NOT match all tasks starting with "TEST". Exact name only.

---

**TEST-H2 — All old alias names normalize correctly**

This task uses exclusively old/deprecated parameter names. Expected behavior is identical to a task using canonical names.

Expected URL (same as A1 would produce for r/programming with no filters, since exclude_terms goes into q=):
```
https://www.reddit.com/r/programming/search.rss?q=NOT+%22hiring%22+AND+NOT+%22jobs%22&restrict_sr=on&sort=new
```

✅ **Success:** `blacklist_terms` was normalized to `exclude_terms` and appears as NOT operators in q=. Files in `data/tests/H2-alias-normalization/` have `score:` of 50+ (from `min_score: 50`). Posts are under 72 hours old (from `max_age_hours: 72`).

Check database for rescrape marks (this task has `track: false` but set `rescrape_threshold_hours: 48` — if track is false, no DB entry is written, so check the frontmatter directly):
```bash
grep "rescrape_after" data/tests/H2-alias-normalization/*.md
```

✅ **Success:** `rescrape_after:` appears in frontmatter for posts under 48h old.

❌ **Failure signal — `blacklist_terms` not recognized:** Posts with "hiring" or "jobs" in title appear in output.

❌ **Failure signal — `min_score` not recognized:** Low-score posts appear.

❌ **Failure signal — `max_age_hours` not recognized:** Posts older than 72h appear.

❌ **Failure signal — `rescrape_threshold_hours` not recognized:** `rescrape_after:` absent from frontmatter.

---

## Cross-Cutting Checks

Run these after all individual tests pass.

### 1. Second run produces no new files (when track: true)

For tests E1 and E2 (which use `track: true`), run the same task a second time immediately:
```bash
python reddit2md.py --config tests/config_test.yml --task "TEST-E1" --debug true
```

✅ **Success:** Stdout shows "0 new posts". No new markdown files appear. Existing files are unchanged.

❌ **Failure signal — New files created on second run or existing files overwritten:** Database tracking not working.

### 2. All frontmatter fields present

Every generated file must contain these fields:
```
post_id:
source:
poster:
date_posted:
date_scraped:
score:
module: reddit2md
label:
```

Run: `grep -L "post_id" data/tests/**/*.md` — should return nothing.

### 3. Canonical wins over alias when both present

Add a one-off test task:
```yaml
- name: "TEST-ALIAS-CONFLICT"
  source: python
  sort: new
  ignore_below_score: 200
  min_score: 10
  max_results: 3
  track: false
  md_output_directory: data/tests/alias-conflict
```

✅ **Success:** All files have `score: 200` or higher. `ignore_below_score` (canonical) won over `min_score` (alias).

❌ **Failure signal — Files with scores between 10 and 200 appear:** Alias overrode canonical. Normalization priority is wrong.

### 4. The `track: false` flag truly prevents DB writes

After running several `track: false` tasks:
```bash
sqlite3 data/database.db "SELECT COUNT(*) FROM posts WHERE file_path LIKE '%A1%' OR file_path LIKE '%B2%';"
```

✅ **Success:** Returns 0. No records in DB for tasks that used `track: false`.

❌ **Failure signal — Records appear for track: false tasks:** The flag is not being respected.
