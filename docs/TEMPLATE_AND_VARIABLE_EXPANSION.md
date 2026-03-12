# Template and Variable Expansion (Phase 2 Architecture)

## 1. Overview and Motivation

`reddit2md` utilizes a two-step data extraction process:
1. Translating an RSS feed into a list of URLs linking to detailed JSON payloads.
2. Downloading these massive, unreadable JSON files and passing them through `processor.py` to extract only the fields vital for markdown generation.

As the tool expands its use cases—particularly for users feeding this data directly into Large Language Models (LLMs) or complex Obsidian workflows—the current hardcoded subset of variables is too restrictive. 

By exposing a much wider array of variables extracted from the raw JSON payload, we unlock three major capabilities:
1. Rich JSON Archives: Allowing users to bypass Markdown entirely and use `reddit2md` as a structural data pipeline to feed LLMs.
  > Note: JSON files location are tracked in the same squlite DB that tracks the markdown output and scrape activity. JSON files are retained so long as they are in that DB, so the db_limit governs both.
2. Granular Local Filtering: Using new variables like `upvote_ratio`, `num_comments`, or `is_video` as targetable conditions in `config.yml`'s Local Ignore bucket.
3. Advanced Templating: Redesigning `note.template` to `post.template` so the user has 100% control over both the Markdown body *and* the YAML Frontmatter, using dynamic `${variable}` injection from the expanded JSON payload.

---

## 2. Expanded Variable Extraction

Currently, `processor.py` merely extracts around 10 variables (title, score, author, etc.). Moving forward, we will vastly expand the `clean_json()` method to capture a rich, comprehensive dictionary for every post.

### Proposed New Variables
When `processor.py` parses `post_data`, it will extract and sanitize the following into the final output dictionary:

#### Interaction Metrics
- `score` (Integer): Total upvotes minus downvotes (already exists).
- `upvote_ratio` (Float): Percentage of upvotes (e.g., 0.95). *Useful for filtering controversial posts.*
- `num_comments` (Integer): Total number of comments in the thread.

#### Content Metadata
- `domain` (String): The domain the post links out to (e.g., `github.com` or `self.python`).
  > Note: Using this for filtering via URL is possible using `url` or `site` but would require use of `q=`, this allows local-side filtering.
- `is_video` (Boolean): True if the post contains a native Reddit video.
- `is_gallery` (Boolean): True if the post contains multiple images.
- `stickied` (Boolean): True if the post is a moderator announcement.
- `spoiler` (Boolean): True if the post is marked as a spoiler.
- `over_18` (Boolean): True if the post is NSFW.

#### Author & Community Context
- `author_flair` (String): The user's specific community flair text.
- `post_flair` (String): Replaces/expands the current `label` parameter using `link_flair_text`.
- `subreddit_subscribers` (Integer): Size of the community at time of scrape.

#### Time Timestamps
- `created_utc` (Float): The raw epoch timestamp of post creation.
- `scraped_utc` (Float): The raw epoch timestamp of when the script ran.

---

## 3. Template Architecture Overhaul

With a massive dictionary of variables now attached to every post object, we can completely divorce the Markdown structure from the Python operating logic. 

### The Current Flaw
Currently, `processor.py` creates a Python dictionary of the frontmatter and manually injects it into `${frontmatter}` at the top of `note.template`. This prevents users from altering YAML keys (e.g., trying to rename `source` or change formatting). 

### The New Design (`note.template`)
`processor.py` will no longer hardcode frontmatter. Instead, it will use Python's `string.Template.safe_substitute()` to pass the *entire* expanded JSON dictionary to `post.template`. 

The user's `templates/note.template` will become `templates/post.template`and natively look like this out of the box:

```markdown
---
post_URL: https://reddit.com${permalink}
subreddit: ${source}
flair: ${post_flair}
date_created: ${created_utc}
date_scraped: ${scraped_utc}
post_id: ${post_id}
score: ${score}
upvote_ratio: ${upvote_ratio}
comments_count: ${num_comments}
is_nsfw: ${over_18}
---
# ${title}

${selftext}

---
## Top Comments
${comment_section}

${update_section}
```

Benefits:
- A user can now change `source: ${source}` to `source: r/${source}` natively inside the template.
- They can rename keys to match their specific Obsidian vault properties (e.g., changing `date_created` to `published_on`).
- They can add their own tags and folders unconditionally.

### The Rescrape/Update Cycle
Because the user can now alter the YAML structure, python's update cycle cannot assume where the `score` or `rescrape_after` keys are. 
1. During an update, `processor.py` will use Regex to specifically find and replace `score: [old_score]` and safely delete the `rescrape_after: ...` line if it exists, replacing it with `rescraped_date: [timestamp]`.
2. It will then append `update.template` to the bottom of the file as usual.

---

## 4. Disabling Markdown (JSON-Only Mode)

With the JSON payloads drastically expanded, the raw data output becomes the most valuable asset for LLM ingestions.

We will add a new global setting to `config.yml`:
```yaml
settings:
  save_md: true   # Defaults to true
  save_json: true # Defauls to true
```

When `save_md` is false:
- The `reddit2md` orchestrator completely skips formatting and writing Markdown notes.
- It relies entirely on `save_json: true` to dump the highly-detailed, nicely structured JSON arrays into the data directory.
- This creates blazing-fast runs specifically tailored for feeding autonomous AI agents or external database systems.
- if `save_md` and `save_json` are both set to false, and the user doesn't remember to overwrite that during the individual call, the only end result of each run is the sqlite db being updated.

---

## 6. Template Comments and Instructions
Because `string.Template` solely looks for `${variable}` blocks and ignores everything else, we can fully support standard markdown commenting inside the template files.

To provide instructions for users out-of-the-box (like a list of all available dynamic variables), we will use HTML/Markdown comments in the body:
```markdown
<!-- 
AVAILABLE VARIABLES:
${score}: The total upvotes
${upvote_ratio}: The percentage of upvotes
${is_video}: True if post is a video
...
-->
```
And standard YAML comments in the frontmatter:
```yaml
---
# Change the key name below to match your vault's naming standard
community: ${source}
---
```
These comments will render silently in the engine and not clutter the final output for the user.

---

## 7. SQLite Database Expansion & Garbage Collection
Currently, the SQLite database acts as a memory cache for the `rescrape` logic and the Markdown logs. To support the expanded variable tracking and the new JSON-only workflows, the database schema will be upgraded.

New Tracked Columns:
- `json_path` (String): The relative path to the saved JSON archive file.
- `ignored_reason` (String): If a post is fetched but dropped by local filtering, this column records the reason (e.g., "Age Filter", "Score Filter", "Exclude Term"). This allows users to actively audit their filters.

Garbage Collection (`db_limit`):
Currently, when `db_limit` is reached, the database prunes the oldest records but leaves the files on the hard drive. 
Moving forward, `db_limit` will act as a strict garbage collector for JSON Archives. 
- When a database record is pruned, the script will look up the `json_path` and actively delete the older, unneeded JSON file from the hard drive. 
- (Note: Markdown notes will never be automatically deleted, as they are considered User Knowledge Assets, but JSON payloads are considered temporary structural data).

---

## 8. Next Steps for Implementation

1. Python Update `processor.py`: Expand `clean_json()` to map all the new fields into the `cleaned_post` dictionary.
2. Update `post.template`, `comment.template` & `update.template`: Rewrite the default templates to include the raw YAML block, dynamic variables, and commented user instructions. The `post.template` will use `${comment_section}` to host the `comment.template`, and `${update_section}` to host `update.template`.
3. Update `database.py` Schema: Add `json_path` and `ignored_reason`, and implement physical file deletion in `prune_old_records()`.
4. Update File Output Logic (`scraper.py`): Wrap the Markdown saving loop in a check for `save_md`, add `save_json` logic, and pass paths to the database.
