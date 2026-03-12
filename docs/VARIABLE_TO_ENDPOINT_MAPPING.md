# Reddit Variable to Endpoint Filtering Mapping

To ensure `reddit2md` honors the "agnostic and optimal API usage" philosophy, every variable extracted by `processor.py` for template usage MUST be filterable. Crucially, if the variable can be filtered via the Reddit API natively, it MUST be mapped to a param that pushes the logic to the `search.rss` endpoint (Category 2) rather than settling for a local-side `ignore_` Python filter (Category 3).

This document serves as the complete accounting of all variables injected into `post.template` and exactly which parameter/endpoint should be natively supported to filter against it.

---

## The Three Categories of Operation (Refresher)
### Category 1 (Core URL)
Built directly into the browse trajectory (e.g., `t=`, `limit=`). Zero lag.
### Category 2 (API Search Parameter `q=`)
Appended into the Lucene-style search query pushed to `search.rss`. Highly optimal, avoids unnecessary bandwidth.
### Category 3 (Local Python Triage)
Evaluated *after* download. Only to be used for variables Reddit's search engine completely ignores.

---

## 1. Interaction Metrics

| JSON Extracted Variable | Target Param | Optimal Category | API Operator / Local Logic |
| :--- | :--- | :--- | :--- |
| `score` | `ignore_below_score` | Category 3 | Local evaluation. (Reddit search does not support relational `< >` scores natively) |
| `upvote_ratio` | `ignore_below_upvote_ratio` | Category 3 | Local evaluation. |
| `num_comments` | `ignore_below_comments` | Category 3 | Local evaluation. |

---

## 2. Content Metadata

| JSON Extracted Variable | Target Param | Optimal Category | API Operator / Local Logic |
| :--- | :--- | :--- | :--- |
| `domain` | `domain` / `site` | Category 2 | `site:domain.com` |
| `is_video` | *(None native)* | *Category 2* | Wait, can filter via `site:v.redd.it` safely if desired via `domain`. No native boolean param needed. |
| `is_nsfw` (`over_18`) | `nsfw_only` | Category 2 | `nsfw:yes` (vs `allow_nsfw` dictating `include_over_18=on`) |
| `spoiler` | `spoiler` | Category 2 | `spoiler:yes` |
| `title` | `title_search` | Category 2 | `title:text` |
| `selftext` | `selftext` | Category 2 | `selftext:text` |

---

## 3. Author & Community Context

| JSON Extracted Variable | Target Param | Optimal Category | API Operator / Local Logic |
| :--- | :--- | :--- | :--- |
| `poster` (`author`) | `author` | Category 2 | `author:username` |
| `post_flair` | `label` / `flair` | Category 2 | `flair:text` (Note: `label_exact` behaves as Category 1 if `sort=new`) |
| `author_flair` | N/A | N/A | (Currently unactionable via native Search. Rarely requested for filter.) |
| `source` (`subreddit`) | `source` | Category 1 | Evaluated via path `/r/{source}/` |

---

## 4. Time Timestamps

| JSON Extracted Variable | Target Param | Optimal Category | API Operator / Local Logic |
| :--- | :--- | :--- | :--- |
| `created_utc` | `timeframe` | Category 1 | Uses `t=` (hour, day, week) |
| `created_utc` | `ignore_older_than` | Category 3 | Local evaluation for precise hour cutoffs. |

---

## Audit Conclusion & Next Steps

Based on this complete accounting, `reddit2md` is currently missing native parameter mappings for several powerful Category 2 and Category 3 properties.

To complete this architectural phase, we must add explicit parameter routing for:
- `--author` -> `author:` (Category 2)
- `--domain` -> `site:` (Category 2)
- `--selftext` -> `selftext:` (Category 2)
- `--title-search` -> `title:` (Category 2)
- `--nsfw-only` -> `nsfw:yes` (Category 2)
- `--spoiler` -> `spoiler:yes` (Category 2)

And for properties that genuinely require local fallback:
- `--ignore-below-upvote-ratio` (Category 3)
- `--ignore-below-comments` (Category 3)
