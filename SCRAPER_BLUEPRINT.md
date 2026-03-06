# Scraper Suite: Architectural Blueprint & Design Philosophy

This document defines the standard architecture for the "Digestitor" suite of scrapers. Any new scraper module added to this ecosystem must adhere to these patterns to ensure compatibility with the orchestration layer and provide a consistent experience for power users.

---

## 1. Core Philosophy: "Local-First, High-Signal"
The primary goal of every scraper is to transform transient, high-volume data streams into permanent, structured, and human-readable knowledge.
- **Source of Truth:** The file system is the ultimate authority. While a database (SQLite) is used for high-speed indexing and state tracking, it should be possible to rebuild the state by scanning the output directory.
- **Non-Destructive:** Scrapers must never delete user edits. If a user modifies a file's metadata, the scraper must detect and respect that change during its next run.
- **Portability:** Use the Python Standard Library as much as possible. External dependencies should be optional fallbacks or strictly minimized.

---

## 2. The Trinity of Interaction
Every scraper must support three distinct modes of interaction with 100% parity in functionality. A setting available in the config must be available via CLI and via Python import.

### A. The Configuration File (`config.json`)
Used for persistent, automated workflows. It defines:
- **Global Defaults:** Baseline settings for all runs.
- **Sources:** A list of specific entities (subreddits, feeds, accounts) with their own specific overrides.

### B. The Command Line Interface (CLI)
Used for ad-hoc exploration or cron-job orchestration.
- Must support `--source` for one-off scrapes of entities not in the config.
- Must support explicit overrides for every parameter (e.g., `--limit`, `--output-dir`, `--detail`).
- Must support behavioral toggles: `--save-json`, `--update-log`, and `--update-db` (Boolean).

### C. The Python Resource (Importable Module)
Used for higher-level orchestration (AI agents, custom dashboards).
- The main `Scraper` class must accept an `overrides` dictionary in its `run()` method to bypass any global or source-specific defaults, including all path and behavioral settings.

---

## 3. The Role of "Debug Mode"
Debug mode is the primary safety mechanism for development and troubleshooting.
- **Forced Isolation:** When `debug` is `true`, the scraper **must** ignore all custom output paths. 
- **The /data/ Folder:** All outputs (Database, JSON, Markdown, Logs) are redirected to a local `data/` directory within the module's repository.
- **Safety Guarantee:** A user should be able to turn on `debug` and run any command without fear of polluting their production Obsidian vault or live database.

---

## 4. Behavioral Toggles
Scrapers must allow users to suppress side effects for specialized workflows:
- **`save_json` (Boolean):** Whether to persist the raw JSON data after processing.
- **`update_log` (Boolean):** Whether to append the run results to the human-readable Markdown log.
- **`update_db` (Boolean):** Whether to record the scrape in the SQLite state database (useful for purely transient "view-only" scrapes).

---

## 5. Output Structure & Data Flow
Data flows through three layers of increasing permanence:

1. **JSON Archive (`/data/json/`):** The raw, cleaned data from the source. Used for AI processing or total rebuilds.
2. **SQLite Index (`database.db`):** Tracks metadata, processing status, and file paths. Crucial for handling "maturing" content (re-scraping items after a delay).
3. **Markdown Notes (`output_directory/`):** The final human-readable product. 
    - **Entity Organization:** Files should be organized into subdirectories named after the source entity (e.g., `/SubredditName/`) if the toggle is enabled.
    - **Atomic Naming:** Filenames should follow the pattern `[Subreddit]_[ID].md` to ensure uniqueness and portability.
    - **Cumulative Content:** Updates to a note (e.g., when a post reaches maturity) should **append** new content (like updated comment sections) to the end of the existing file rather than overwriting it.

---

## 5. Metadata and Nomenclature
Standard field names must be used in front-matter and database columns:
- **`flair`:** (Formerly `project`). Used to categorize the post within the source (e.g., Reddit Flair).
- **`post_link`:** (Formerly `story_link`). Used to link to related internal notes or external URLs.

---

## 6. Granular Control & Overrides
The orchestration layer assumes that any specific call can define its own target.
- **Dynamic Pathing:** If a CLI command specifies `--output-dir`, the scraper must use that path for that specific run, even if a different path is defined in `config.json`.
- **Precedence Order:** 
    1. **Direct Overrides:** (CLI arguments or Python method parameters).
    2. **Source-Specific Settings:** (Values defined inside a source object in `config.json`).
    3. **Global Defaults:** (Values defined in the `global_defaults` section of `config.json`).

---

## 6. The Human-Readable Log (`Scrape Log.md`)
Every run must update a Markdown-formatted log. This provides a dashboard for the user to see:
- What was new in the last run.
- What items are currently "maturing" and when they will be re-scraped.
- Errors or blocks (like 403 Forbidden) presented with actionable fixes.

---

## 7. Standard Implementation Checklist
When building a new scraper, ensure the following classes exist:
- `Config`: Manages the hierarchy of defaults and overrides.
- `Client`: Handles HTTP requests (with robust headers/fallbacks to avoid 403s).
- `Processor`: Handles data cleaning and Markdown generation.
- `DatabaseManager`: Manages the SQLite state.
- `Scraper`: The main orchestrator that ties the above together.

---

*By following this blueprint, we ensure that as the suite grows, every module remains a predictable, reliable, and powerful tool for the end user's knowledge pipeline.*
