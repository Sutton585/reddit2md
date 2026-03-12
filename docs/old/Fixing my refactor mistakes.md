# Fixing my mistakes

That last round of updates created unforntate gaps in desired features and nomenclature.

# Implementation guide

## Principal of translation
reddit2md operates a permissive translation layer. The philosophy is: if we can reasonably interpret what the user meant, we try to account for it so we can accept it and translate it silently. We try to not error on a recognizable input just because it isn't the preferred syntax. This applies to field names (source/sources/subreddit/reddits), value formats (string vs list vs plus-joined string), and boolean values (true/yes/1). The preferred syntax is what we show in documentation. Everything else we try to translate internally and accept without complaint.

## Advanced Query Support
No conflict detection between structured keys and `search` field. url_builder assembles structured keys first, appends `search` value last with AND. Done. Any contradictions in the resulting `q=` string are Reddit's problem to interpret.

### `search` YAML quoting

The implementation guide just needs: "never parse or modify the `search` field value — URL-encode it and insert as-is."

The problem is specifically when a user wants Reddit's exact phrase match syntax, which requires literal double quotes reaching the `q=` string. Example:

User wants to search for the exact phrase "spider man" — in Reddit's `q=` that needs to look like:
```
q="spider man"
```

But in YAML, if they write:
```yaml
search: "spider man"
```
The outer double quotes are YAML string delimiters — they get stripped. What arrives at the url_builder is just `spider man` with no quotes, which Reddit treats as two separate keywords, not a phrase.

The correct YAML to get literal double quotes through is:
```yaml
search: '"spider man"'    # single quotes wrap the whole value
```

Code does not detect this situation and warn the user.


### zero conflict-handling code:

**`search`/`query` is always appended last, as-is. Whatever the user puts there is their responsibility.**

The url_builder just does its job assembling structured keys, then appends the `search` value at the end joined with `AND`. If the user creates a contradiction, Reddit sorts it out — or returns unexpected results. That's on them.

So the implementation rule is literally: no conflict detection, no warnings, no merging logic beyond simple AND concatenation.


## Parameter Implementation Map

### Group 1: URL-level — browse mode stays intact, no lag

These translate directly to URL parameters outside of `q=`. A task using only these parameters stays on the browse endpoint.

| reddit2md key | YAML example | URL translation | Browse safe? |
|---|---|---|---|
| `source` | `source: MarvelComics` | `/r/MarvelComics/new/.rss` | ✅ |
| `sources` | `sources: [MarvelComics, MarvelStudios]` | `/r/MarvelComics+MarvelStudios/new/.rss` | ✅ |
| `sort` | `sort: new` | `sort=new` | ✅ |
| `time_filter` | `time_filter: week` | `t=week` | ✅ |
| `post_type` | `post_type: self` | `type=self` | ✅ on search only |
| `allow_nsfw` | `allow_nsfw: true` | `include_over_18=on` | ✅ on search only |

**Note on `post_type` and `allow_nsfw`:** these are URL-level params that don't touch `q=`, but they only work on the search endpoint. So if a user sets either of these without any `q=` params, we need to switch to search mode — but we're not adding anything to `q=`. The URL would look like:
`/r/MarvelComics/search.rss?restrict_sr=on&sort=new&type=self&include_over_18=off`

---

### Group 2: Require `q=` — forces search mode, potential lag

Any of these being set switches the URL to the search endpoint and builds a `q=` string.

| reddit2md key | YAML example | `q=` translation |
|---|---|---|
| `search` / `query` | `search: "hello world"` | `hello world` |
| `search` / `query` | `search: "hello world AND author:jeff123"` | `hello world AND author:jeff123` |

| `author` | `author: jeff123` | `author:jeff123` |
| `title` | `title: avengers` | `title:avengers` |
| `selftext` | `selftext: spoiler` | `selftext:spoiler` |
| `label` / `flair` | `label: Comics` | `flair:Comics` |
| `site` | `site: youtube.com` | `site:youtube.com` |
| `blacklist_terms` | `blacklist_terms: [megathread, weekly]` | `NOT "megathread" AND NOT "weekly"` |
#### Note
Certain values of sort would trigger us having to use q=
**`sort: relevance` and `sort: comments` are search-only**
Those two sort values don't exist on the browse endpoint. Using them implicitly triggers search mode just like a `q=` param would. Worth flagging.

---

### Group 3: Local only — never touches the URL

| reddit2md key | YAML example | When it runs |
|---|---|---|
| `min_score` | `min_score: 50` | After fetch, discards posts below threshold |
| `min_age_hours` | `min_age_hours: 12` | After fetch, drives rescrape scheduling |
| `max_age_hours` | `max_age_hours: 48` | After fetch, discards posts too old |
| `offset` | `offset: 5` | After RSS parse, slices first N from list |
| `blacklist_urls` | `blacklist_urls: [imgur.com]` | During markdown generation, filters post_links frontmatter |
| `comment_contains` | `comment_contains: spoiler` | After full JSON fetch, discards if no comment matches |
| `detail` | `detail: MD` | During comment processing |
| `group_by_source` | `group_by_source: true` | During file output |
| `debug` | `debug: false` | System |
| `verbose` | `verbose: 1` | System |
| `save_json` | `save_json: true` | During file output |
| `enable_md_log` | `enable_md_log: true` | After run |
| `md_log` | `md_log: path/to/log.md` | After run |
| `db_limit` | `db_limit: 1000` | After run, DB pruning |
| `rescrape_threshold_hours` | `rescrape_threshold_hours: 12` | After fetch, sets rescrape_after timestamp |

---

### The Mode Decision Tree

```
Has q= params?  ──No──→  Has post_type or allow_nsfw? ──No──→  BROWSE URL
                                                        ──Yes─→  SEARCH URL (no q= string)
                ──Yes─→  SEARCH URL (with q= string)
```

So there are actually three states:
1. **Pure browse** — `r/A+B/new/.rss` — real-time, no lag
2. **Search without q=** — `r/A/search.rss?type=self&sort=new` — search endpoint, lag possible, but no query string
3. **Search with q=** — `r/A/search.rss?q=flair%3AComics&sort=new` — search endpoint, lag possible, query filtering active

---

### Source Field Aliases

The source field must be recognized under any of these keys in YAML config, CLI, or Python:
`source`, `sources`, `subreddit`, `subreddits`, `reddit`, `reddits`

All of these are equivalent and must be normalized to a single internal value before reaching URLBuilder. Normalization happens in `config.py` `get_task_config()` — check for any of the alias keys, collapse whichever one is present into `source`, remove the alias key.

Priority if somehow multiple aliases appear in the same task: `source` > `sources` > `subreddit` > `subreddits` > `reddit` > `reddits`. First one wins.

The value can be a string or a list in any alias form:
```yaml
subreddits: "news"          # string — fine
source: "news+pics"         # directly translates to multi-reddit — no problem
reddit: ["news", "pics"]    # list — fine
sources: ["news", "pics"]   # list — fine, preferred format in documentation.
```
All produce the same internal value going into URLBuilder. URLBuilder only ever sees `source` — it never knows which alias was used.

### Extending our query search results via `after=` 
(Out of Scope Now, But Viable Later)

Reddit supports `before=`, `after=`, and `limit=` as URL parameters on the **browse endpoint** (no search lag). `after=t3_postid` takes the fullname of the last post from the previous page and returns the next 25 results from that point.

A future `paginate: true` or `max_results: 75` feature could work like this:
1. Fetch first page, parse 25 results, read last post ID
2. Make second call with `after=t3_{last_id}`
3. Repeat until `max_results` is satisfied or Reddit stops returning new posts

Caveats to document when implementing:
- Results shift between calls as new posts are made — pages are not perfectly stable
- Reddit will throttle aggressive pagination
- The current `offset` parameter (local list slicing) is a weak substitute — it still only operates on the same 25 results. True pagination requires chaining calls. These are two different things and should not be conflated.
- `after=` works on browse endpoint — does not force search mode, no lag penalty















# Documentation points of interest guide


README should mention somewhere that reddit2md is forgiving about how you specify things. Users coming from different mental models of Reddit's structure will naturally reach for different terms. The module meets them where they are.

### Concepts that took us investigation to understand — users will hit the same confusion



**Browse vs Search mode**
This is the biggest one. A user who adds `label: Comics` to what was previously a simple feed task needs to understand they just changed the fundamental nature of that task. It's no longer a live feed — it's a search. The lag implication is real and affects how they should think about `min_age_hours` and freshness.

**Why `sources` as a list is one call, not many**
The old behavior was one call per subreddit. The new behavior is one combined URL. Users migrating from old configs need to know this changed, and users who *want* separate calls need to know they do that by listing separate routine entries.

**`time_filter` works with every sort method**
Non-obvious. Most people assume it only pairs with `sort: top` because that's how Reddit's UI presents it. Explicitly showing `sort: new` + `time_filter: week` as a valid and useful combination is worth a real example.

**`blacklist_terms` now runs twice**
Once in the URL as `NOT` operators (reducing the 25-result pool), and once locally as a safety net. Users don't need to do anything differently — it just works better than before. But worth a sentence explaining why.

---

### Nomenclature that needs clarifying

**`label` vs `flair`**
We support both as aliases. Users coming from Reddit's own terminology will write `flair`, users familiar with the module will write `label`. Document that both work and mean the same thing.

Flair and label are both supported as aliases throughout. For exact matching, same pattern — flair_exact and label_exact both accepted, translate to flair: in the URL. Add both rows to the implementation map.

**`source` vs `sources`**
Same deal — aliases. Single string or list, both accepted.

**`selftext`**
Reddit's internal term that means "the body text of a text post." Not obvious to non-technical users. Worth a plain English sentence before showing the YAML example.

**`search` vs operator fields**
A user might wonder why there's both a `search` key AND separate `author`, `title`, `label` keys — since they all end up in `q=`. The answer is that `search` is freeform and puts you in control of the raw query string, while the named keys are structured and validated. A power user writes `search: "author:jeff123 AND title:update"`. A normal user writes `author: jeff123` and `title: update` separately. Both produce the same URL. Document this clearly.

**`post_type: self`**
"Self" is Reddit jargon. In the README this should be explained as "text posts" and "link posts" in plain English, with `self` and `link` as the values.

### Source Field — Flexible Naming

Flag for README: users shouldn't need to memorize which exact key name to use. Show all aliases explicitly with a note that they're interchangeable. Also: **remove the `"news+pics"` plus-joined string example entirely from the README** — that was an internal URL implementation detail that leaked into the docs. Users never write `+` joined strings. They write lists. The joining is done invisibly by the system.

Current README text to remove:
```yaml
- source: "movies+marvelstudios"
```
Replace with:
```yaml
- source: ["movies", "marvelstudios"]
```
And add a note that `source`, `sources`, `subreddit`, `subreddits`, `reddit`, `reddits` all work identically.

---

### Pagination — Current Limitation Worth Being Honest About

Reddit caps RSS results at 25 per call. The current `offset` parameter skips the first N items from those 25 — it does not get you results 26–50. That's a common misconception worth addressing directly in the README. True multi-page pagination is a planned future capability.

---

### time_filter — Works With Every Sort Method
Worth explicitly correcting a common misconception: Reddit's UI surfaces t= most prominently alongside "Top" posts, so users assume it only applies there. It does not. t= restricts the pool of posts to that time window before any sorting is applied. Every combination is valid:

- sort: top + time_filter: week → highest upvoted posts from the past 7 days
- sort: new + time_filter: week → newest posts, but only from the past 7 days
- sort: hot + time_filter: month → hot algorithm applied only to posts from the past month

The README should show at least two non-top examples to actively break the misconception. Never describe time_filter as "only useful with sort: top."

Can you paste the current state of both saved documents so I can audit what's actually in them vs what we think is there? That way we go into the coding phase with a clean confirmed spec rather than assumptions.

---

`search` / `query` are aliases for the same freeform `q=` field. Content is inserted as-is with no parsing or validation — the user is responsible for correct syntax. When combined with structured fields (`author`, `title`, `label` etc.), structured fields are assembled first and `search` content is appended last, all joined with `AND`. Never parse the contents of `search` — treat it as an opaque string.

---

README needs a dedicated Advanced Search section. Key points: what `search` accepts, how it composes with structured keys, the YAML quoting note, and an explicit statement that the user is in control and conflicts are not handled by the module.

**Advanced Search**

All structured keys (`label`, `blacklist_terms`, `source`, etc.) are assembled into the URL automatically. For anything beyond what structured keys support — filtering by author, title, post body, domain, or complex boolean logic — use the `search` field.

```yaml
# Structured keys handle the common cases
source: MarvelComics
label: Comics
blacklist_terms: [megathread, weekly]

# search handles everything else
search: 'author:jeff123 AND title:avengers'
```

If you use `search` alongside structured keys, both apply — structured keys are assembled first, your `search` value is appended with AND. If they conflict, your `search` value wins in practice because it's more specific. reddit2md does not attempt to detect or resolve conflicts — the user is in control.

> **Note:** `search` accepts any Reddit Lucene syntax. See [Reddit's search documentation] for the full operator list. Remember that YAML requires single quotes around values containing double quotes — `search: '"exact phrase"'` not `search: "exact phrase"`.


### `search` YAML quoting

We never parse or modify the `search` field value — URL-encode it and insert as-is.

The problem is specifically when a user wants Reddit's exact phrase match syntax, which requires literal double quotes reaching the `q=` string. Example:

User wants to search for the exact phrase "spider man" — in Reddit's `q=` that needs to look like:
```
q="spider man"
```

But in YAML, if they write:
```yaml
search: "spider man"
```
The outer double quotes are YAML string delimiters — they get stripped. What arrives at the url_builder is just `spider man` with no quotes, which Reddit treats as two separate keywords, not a phrase.

The correct YAML to get literal double quotes through is:
```yaml
search: '"spider man"'    # single quotes wrap the whole value
```

Code does not detect this situation and warn the user.


### Advanced Search — What Forces Search Mode and Why It Matters

README needs a clear section explaining the distinction between browse mode and search mode, and which settings trigger each. Frame it as a spectrum from simple to advanced:

**Simple — always browse mode, always real-time:**
```yaml
source: MarvelComics
sort: new
time_filter: week
```

**Intermediate — forces search mode, no `q=` involved:**
```yaml
post_type: self
allow_nsfw: true
```
These stay outside `q=` but require the search endpoint. Mention lag trade-off.

**Advanced — forces `q=` and search mode:**
```yaml
label: Comics
blacklist_terms: [megathread, weekly]
search: 'author:jeff123 AND title:avengers'
```

README should say explicitly: the more advanced settings you use, the more you are doing a targeted search rather than monitoring a live feed. That's a conscious trade-off, not a flaw.

**The one exception worth highlighting:**
`label_exact`/`flair_exact` with default sort stays on the browse endpoint via `f=flair_name:`. This is the best of both worlds — exact flair filtering with no lag. Worth calling out as the recommended approach when flair filtering is needed and sort order doesn't matter.

**On the future potential removal of structured q= keys:**
Do not document `label`/`flair` partial match, `blacklist_terms`, etc. as permanent features in the advanced section. Frame the `search` field as the primary tool for advanced querying, with structured keys as convenience shortcuts. This way if the decision is made to require raw `search` for all `q=` content, the README edit is additive rather than a contradiction of previous claims.


---

### Things that seem simple but have a gotcha

**`post_type` and `allow_nsfw` silently force search mode**
A user with a simple feed task who adds `post_type: self` will unknowingly introduce search lag. They need to know this is a trade-off, not a free filter.

**`selftext` only works on text posts**
If you set `post_type: link` and `selftext: anything` in the same task, `selftext` will never match anything. Worth a warning note.


**`sort: relevance` and `sort: comments` are search-only**
Those two sort values don't exist on the browse endpoint. Using them implicitly triggers search mode just like a `q=` param would. Worth flagging.

essentially, we are always trying to avoid using the q= field if we can avoid it. once it's unavoiable, we include it, but stil prefer the to set other parameters outside the q= even when it's in use. It's not necesarily a total mode switch, right? it's just trying to avoid using it, and only using it on the minimum parameters possible.




### `max_age_hours` → `t=` mapping:**

**`time_filter` is approximate for `max_age_hours`**

If a user sets `max_age_hours: 30`, the url_builder maps that to `t=day` (closest bucket). They might get some 48-hour-old posts in the results that the local filter then trims. The URL is doing its best but local filtering still has the final word.

The idea is: `t=` is a blunt instrument but it narrows the pool before the 25-cap. The mapping would work like this:

| `max_age_hours` value | Maps to `t=` | Actual window Reddit applies |
|---|---|---|
| 1 or less | `hour` | ~past 60 minutes |
| 2–24 | `day` | ~past 24 hours |
| 25–168 | `week` | ~past 7 days |
| 169–720 | `month` | ~past 30 days |
| 721–8760 | `year` | ~past 365 days |
| over 8760 | `all` | no time restriction |

Practical user scenarios:

- User sets `max_age_hours: 6` → url_builder adds `t=hour`, local filter then discards anything older than 6 hours. Reddit returns up to 25 posts from the past hour, local trims to past 6h. Fine.
- User sets `max_age_hours: 48` → url_builder adds `t=week` (closest bucket that doesn't cut off valid results), local trims to 48h. Reddit returns up to 25 posts from the past week, local trims aggressively. The URL narrowed the pool somewhat but not precisely.
- User sets `max_age_hours: 12` → url_builder adds `t=day`, local trims to 12h. Reasonable overlap.

**The key rule:** always round UP to the next bucket, never down. If you round down you'll silently miss posts that are within the user's `max_age_hours` but outside the `t=` window. Rounding up means some extra posts come through that local filtering then discards — that's fine.


---













=