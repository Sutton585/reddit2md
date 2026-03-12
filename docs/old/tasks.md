---
what I've done:
    description: "I've made some changes myself to try to make it easier for you to focus on testing to ensure everything works, then refine our approach to documentation updates."
    what I need:
        - "read my explanation of what i changed" 
        - "test that everything works according to how users would expect."
        - "review the new file README_additions.md, expand upon areas that aren't properly addressed. README.md updates must account for all reddit2md functionality across the three interfaces. common use cases are used for helpful examples. Never rewrite the file, make a plan for surgical edits or insertions."
    what has been done:
        reddit2md/core/url_builder.py:
        - "This is the entire new module. It has two URL modes: the original simple browse URL (zero behavior change for existing configs), and the new search endpoint mode that activates automatically when any advanced parameter is present."
        - "The standalone test block at the bottom (python -m reddit2md.core.url_builder) runs 14 cases and passes all of them as far as i can tell. you might want more robust testing."
        config.py:
            "The only change is 6 new default keys added at the bottom of DEFAULT_CONFIG: query, label, exact_flair, time_filter, post_type, allow_nsfw. Everything else is identical."
        scraper.py:
            Two changes:
                execute_task: "swaps out the old one-liner RSS URL for a call to self.url_builder.build_rss_url(...) — that's it for the core log"
                The main() CLI parser: "this gets 6 new --argument entries with the comma-separated label → list handling"
        README_additions.md: "this is a patch guide rather than a rewritten file, per our 'never completely rewrite' rule. It documents 6 surgical changes with exact locations and REPLACE / APPEND / INSERT_AFTER labels so you can revise and apply them."
    One note on tasks.md step 3's instruction about removing config.py's old label behavior: "label was previously a post-fetch filter applied locally. With this refactor it now does double duty — it pre-filters at the URL level AND the frontmatter label field continues to work as before. No removal needed; the semantics just got richer."
---

# Reddit2MD Refactor Plan: Advanced Querying via RSS

This document outlines the step-by-step plan for refactoring `reddit2md` to support robust, complex Reddit queries natively via the RSS URL generation process, without breaking existing core logic.

## 1. Parameter Categorization & Logic

### 1.1 Parameters Integrated into the URL (The URL Builder)
These parameters will be processed by the new URL builder to construct a precise RSS search query.

**URL Native Parameters (`&key=value`):**
- **`source`**: Single subreddit (`MarvelComics`), multiple subreddits (`movies+marvelstudios`), or empty/`all` (global search). Translates to `reddit.com/r/{source}/search.rss`.
- **`sort`**: Order of results (`new`, `top`, `hot`, `relevance`, `comments`).
- **`t` (Time filter)**: Frame for `top` or `relevance` (`hour`, `day`, `week`, `month`, `year`, `all`).
- **`type` (Post type)**: Filter for `link` (links/images) or `self` (text posts only). Config key: `post_type`.
- **`include_over_18` (NSFW)**: Inclusion of NSFW content (`on`/`off`). Config key: `allow_nsfw`.
- **`after` / `count`**: Native Reddit pagination. Used if `offset` needs a native backend implementation.

**Query-Field Operators (`q=...`):**
- **`query` (NEW)**: Literal keyword searches. Support for Lucene syntax (AND, OR, NOT, quotes, parentheses).
- **`label` / `flair`**: Translates to `flair_text:"<value>"` (partial match).
- **`exact_flair` (NEW)**: If true, translates to `flair_name:"<value>"` (exact match).
- **Granular Operators**: Users can now use these directly in the `query` field or we can add optional config keys for them:
    - `author:username`
    - `site:domain.com` or `url:domain.com`
    - `title:keyword` (Search title only)
    - `selftext:keyword` (Search body only)
    - `score:>100` (Filter by upvote count)

---

## 2. Implementation Steps

### Step 1: Create the URL Translation Module
- **Action**: Create `reddit2md/core/url_builder.py`.
- **Functionality**:
    - Accept all parameters: `source`, `query`, `label`, `exact_flair`, `sort`, `time_filter`, `post_type`, `allow_nsfw`, etc.
    - Intelligent `q=` construction: Combine `query`, `flair_text/name`, and other operators with `AND`.
    - Handle `urllib.parse` for perfect URL encoding.
    - Set `restrict_sr=on` automatically if a specific `source` is provided.
- **Documentation & Alignment**: 
    Identify all internal changes and functional shifts. Evaluate how these new capabilities would be described in the `README.md`. Ensure that even as an internal module, the developer documentation (comments/docstrings) fully explains the new logic and use cases.

### Step 2: Ensure the Module Works (Testing)
- **Action**: Standalone verification block in `url_builder.py`.
- **Acceptance Criteria**:
    - `source="LeaksAndRumors", label="Comics", allow_nsfw=False` -> `.../search.rss?q=flair_text%3A%22Comics%22&restrict_sr=on&include_over_18=off`
    - `query="author:sutton585 AND title:update", sort="new"` -> `.../search.rss?q=author%3Asutton585+AND+title%3Aupdate&sort=new`
    - Multi-source: `source="movies+marvel", post_type="link"` -> `.../r/movies+marvel/search.rss?type=link`
- **Documentation & Alignment**: 
    Look at the changes to functionality that occurred before and after this task. What is different? What new or adjusted parameters should we be aware of? Evaluate `README.md` for any inconsistencies or missing parts. When you mark this task "complete", that means the unit tests are passing and the expected URL outputs are perfectly aligned with what the `README.md` will eventually promise.

### Step 3: Refactor Core Config & Scraper
- **Action**: Update `reddit2md/core/config.py` and `reddit2md/scraper.py`.
- **Changes**:
    - Support new config keys: `query`, `time_filter`, `post_type`, `allow_nsfw`, `exact_flair`.
    - Update CLI parser (`argparse`) to include these as overrides.
    - Update `execute_task` in `scraper.py` to call the URL builder.
- **Documentation & Alignment**: 
    Look at the changes to functionality that occurred before and after this task, and the changes when this whole refactor will be complete. What is different? What new or adjusted parameters should we be aware of? Evaluate `README.md` for any inconsistencies or missing parts. New abilities not yet described in the file. Without rewriting the file, only ever appending or injecting, make sure we have full explanations of everything new including common use cases as examples across our three user-facing interfaces (CLI, python, config file). When you mark this task "complete" that means it's not only tested and working, but the `README.md` file is now also up-to-date and has no outdated info, and all relevant new additions.

---

## 3. Acceptance Criteria (For AI Agents)
1. **Full Parameter Support**: Every parameter found in `refactor.md` (including NSFW, Post Type, and Granular Query Operators) must be functional.
2. **Zero-Dependency**: No new libraries; use `urllib.parse`.
3. **No Breaking Changes**: Existing basic configs (just `source` and `sort`) must continue to work perfectly.
4. **Encoding Integrity**: Complex strings with spaces, quotes, and logic operators must be URL-encoded correctly for Reddit's search engine.
5. **Documentation Parity**: No task is complete until the `README.md` (and internal documentation) reflects 100% of the new functionality with clear, actionable examples for CLI, Python, and YAML users.
