# Module Standards: Unified Architectural Blueprint

This document defines the strict architectural and philosophical standards for the Sandman suite of scrapers (originally based on the reddit2md project). Whether building a module for Reddit, HackerNews, Twitter, Gmail, or any other platform, every scraper module must adhere to this blueprint.

This document lives in the root `modules/` directory of the Sandman orchestration suite. It ensures that the overarching orchestration layer can interact with any module predictably, and that the end-user experiences a unified, highly controllable knowledge-gathering pipeline. 

## 1. Core Philosophy: The Living Knowledge Base & Data Signal

Modules are not simple data dumpers; they are Knowledge Accumulators designed for professional note-taking environments like Obsidian and AI-automated workflows. We prioritize high-signal output by refining messy raw data into optimized formats.

### Three-Tiered Architecture (The Pipeline)
To avoid "monolithic bloat," modules are categorized by their role in the knowledge pipeline:
    - Tier 1: Source Scrapers (e.g., `reddit2md`, `gmail2md`): These monitor high-level origins. Their job is to extract raw content and, crucially, identify external URLs for secondary processing.
    - Tier 2: Entity Extractors (e.g., `jobs2md`): Specialized modules that take a URL or specific entity ID and transform it into a high-fidelity record using domain-specific tools (like JobSpy for job boards).
    - Tier 3: Utility Scrapers (e.g., `web2md`): The "Universal Fallback." These use advanced noise-removal libraries (like Trafilatura or Crawl4AI) to turn any generic HTML page into clean Markdown.

### Cross-Module Handoff Schema
Modules communicate through the filesystem.
    - Extraction: A Tier 1 module extracts URLs and stores them in the `extracted_links` front-matter field of its generated Markdown file.
    - Queueing: It also sets a `[entity]_scraped: false` (e.g., `jobs_scraped: false`) flag.
    - Processing: The corresponding Tier 2 module scans the output directory for files with this flag set to `false`, processes the links, and then updates the flag to `true` (or the count of items found).

### Markdown is the Ultimate Authority
The file system is the primary source of truth. If a user manually edits a note's front-matter (e.g., changing its categorization or deleting a scheduled re-scrape time), the scraper MUST detect and respect that change on its next run. Notes are structured for maximum clarity and RAG (Retrieval-Augmented Generation) compatibility.
### The Data Triad (Output Agnosticism)
Modules must never assume the user's desired data format. Every module must provide three computationally equivalent repositories of output, allowing users to enable or disable them via configuration:
    1. Markdown Documents: Utilizing an external text template engine (like `string.Template`), allowing users absolute control over frontmatter schema and body layout. Hardcoded layouts are forbidden.
    2. Raw JSON Archives: Providing a noise-free, sanitized JSON structure optimized for token-efficient LLM pipelines or programmatic analysis.
    3. A Detailed SQLite Database: Even if Markdown and JSON outputs are completely disabled, the module must optionally provide a mechanism (e.g., `detailed_db`) to catch the entire rich JSON payload within the SQLite tracking database for native analytical querying.
- Cumulative Knowledge (Living Notes): Scrapers do not blindly overwrite files and history. When an entity is re-scraped (due to an update or reaching maturity), the system updates the metadata but appends the new content (e.g., new comments, replies) to the end of the file. This creates a chronological record of an evolving discussion.
- Safe Vault Coexistence: Modules must assume they are writing into a densely populated, human-curated directory. A scraper must surgically identify its owned files by checking for a specific ID in the front-matter (e.g., post_id). It must never touch or alter unrelated files.
- Zero-Dependency Graceful Degradation: Modules should strive to operate using only the Python Standard Library to ensure maximum portability. However, they must gracefully detect and utilize superior external libraries (like requests over urllib) if present, to handle advanced anti-bot measures (e.g., 403 blocks).

## 2. The Agnostic Interaction Model

Every module supports 100% functional parity across three distinct modes of interaction. This ensures the tool fits perfectly into any workflow, from simple recurring schedules to complex autonomous research pipelines. If a setting exists, it must be accessible everywhere.

### A. The Configuration File (`config.yml`)
YAML Configuration Standard: All Sandman modules MUST use YAML (`config.yml`) for their configuration files. While JSON was considered for strict standard-library portability, YAML is the officially supported standard because it allows for inline comments (`#`), which is critical for user-facing configuration files where complex parameters need explanation.

Used for persistent, automated, persistent setups. It must contain:
-  Settings (`settings`): This section establishes the baseline parameters for any execution (such as output directories, default logging verbose level, and standard timeouts).
-  Routine (`routine`): This section defines an ordered list of specific tasks to execute when the module is run without arguments. 

The routine is a to-do list for calls to this script that don't have any specific parameters. You can have multiple entries in this queue targeting the exact same source with completely different parameters if you choose. It is the default automated routine, enabling the user to run the script without arguments on a recurring schedule and retrieve their customized source of data.

### B. The Command Line Interface (CLI)
Used for ad-hoc exploration, testing, and terminal-based automation (like recurring schedules).
- Must support targeting a specific origin entity (e.g., --target news) for one-off scrape tasks of entities not in the config.
- Must support explicit, typed overrides for every single parameter (e.g., --max-results 5, --detail XL, --save-json False).
    
### C. The Python Resource (Importable Module)
Used for higher-level orchestration (e.g., an LLM agent triggering a scrape or seamless integration into larger suites).
- The main orchestrator class must accept an overrides dictionary in its run() method to bypass any global or task-specific defaults programmatically.

Precedence Order: Direct Overrides (CLI/Python) > Task-Specific Config > Global Defaults Config.

## 3. Internal Class Architecture (The 5 Buckets)

To ensure consistency in AI-driven development and code maintainability, every module must separate its internal logic into five distinct domains or "buckets" (usually structured within a `core/` directory).

1. Config (Settings Management): Handles the logic for merging `settings` with task-specific settings and applying CLI/Python overrides based on the Precedence Order. Validates parameter types.
2. Client (Network Operations): Strictly isolates API and network logic. Manages authentication, headers (e.g., browser-mimicking), rate limiting, and pagination. It should return raw or semi-raw data.
3. Processor (Data Sanitization & Translation): The pure data translation layer. It takes the messy API response from the Client and strictly maps it to the "Standard Schema". It also handles the logic for internal Obsidian link resolution.
4. DatabaseManager (State Tracking): Manages the SQLite index. Responsible for cache pruning, maintaining the `rescrape_after` maturity logic, and executing the State Reconciliation Flow on startup.
5. Scraper / Orchestrator (The Execution Loop): The main entry point. Iterates through the routine queue, coordinates the Config, Client, Processor, and DatabaseManager, and ultimately writes the final Markdown and JSON files to the disk using a Theme Engine / Templates.

## 4. The Execution Architecture: The Routine Model

Modules must not use a simple lookup model (e.g., find the config for X and run it once). Instead, they operate on a Routine.

- Sequential Execution: The config.yml defines an array of tasks in the routine section of the config. The module iterates through this list and executes them in order.
- Multi-Faceted Targeting: A user must be able to define multiple tasks for the exact same origin entity, each with different settings.

## 5. Behavioral Toggles & Limits

Scrapers must allow users to suppress side effects or limit footprints:
- verbose (Integer): Controls the level of terminal output across all modules and the orchestrator.
    - 0: Errors only (Silent operation).
    - 1: Basic progress and warnings (Recommended default).
    - 2: Granular debug and trace information.
- save_json (Boolean): Whether to persist the sanitized JSON data after processing.
- md_log (Boolean): Whether to append the run results to the human-readable Markdown log.
- db_limit (Integer): Maximum number of records to keep in the SQLite index. Older records are pruned to keep the database size manageable.
- min_age_hours / ignore_newer_than_hours (Integer): The minimum age of a post to be considered relevant. Anything newer is entirely ignored.
- max_age_hours / ignore_older_than_hours (Integer): The maximum age of a post to be considered relevant. Anything older is entirely ignored. 
- rescrape_threshold_hours / rescrape_newer_than_hours (Integer): Triggers maturity logic (if supported by module). If a post is younger than this limit, it is scraped but queued for a rescrape later. Setting this to 0 disables maturity/re-scraping logic.
- track (Boolean): Whether the system uses the SQLite database state tracker. Setting to False disables DB tracking completely.
- offset (Integer): Discards the first N results from the source feed before the scraper begins processing.

## 6. State Reconciliation Flow

To maintain the Source of Truth, every module must perform a surgical reconciliation on startup (handled by the Orchestrator and DatabaseManager). This ensures the SQLite cache reflects the current state of the filesystem.

1. Scan Directory: Recursively scan the md_output_directory for all .md files.
2. Verify Ownership: For each file, parse the front-matter. If the post_id field is missing, skip the file entirely (it belongs to the user, not the scraper).
3. Conflict Resolution: Compare the category and rescrape_after values in the Markdown file against the SQLite database. If they differ, the Markdown file wins, so update the database record immediately.
4. Orphan Pruning: Check for records in the SQLite database where the corresponding Markdown file no longer exists on disk. Delete these records from the database (the user has forgotten the post).

## 7. The Data Pipeline & State Management

Data flows through three distinct layers, each serving a specific architectural purpose.

### Layer 1: JSON Archive (The Payload)
- Path: data_output_directory/json/
- Purpose: Stores the sanitized, high-signal JSON data containing the entire payload (never the raw, messy API response).
- Function: Ideally suited for direct LLM ingestion or Python data-science pipelines where Markdown parsing is inefficient. Serves as an offline backup. If the user accidentally deletes their Markdown notes or the SQLite database, the system can rebuild the entire vault from these JSON files without hitting the external API rate limits.

### Layer 2: SQLite Index (The Brain & Data Warehouse)
- Path: data_output_directory/database.db
- Purpose: A high-speed tracking index. It remembers what has been scraped, when it was scraped, and when it is scheduled to be re-scraped. 
- Function: Operates natively as a Self-Healing Cache tracking maturity schedules. Crucially, if configured as a `detailed_db`, it expands into a full Data Warehouse, storing the entirety of the payload (upvote ratios, domains, raw text snippets) natively in SQL columns.
- Pruning: The database footprint is strictly managed by a `db_limit` integer setting. If `db_limit` is reached, it acts as an Active Garbage Collector, automatically deleting the oldest corresponding `.json` files from disk alongside the database records to maintain a lean footprint.

### Layer 3: Markdown Notes (The Final Product)
- Path: md_output_directory/
- Purpose: The human-readable and LLM-parsable final output.
- Function: As detailed in the Core Philosophy, these are living documents that dictate state back to the SQLite cache during reconciliation.

## 8. Anatomy of a Scrape: Maturity & Internal Linking

### Context vs. Freshness (Maturity Logic)
To balance the need for immediate updates with the desire for deep context, modules must implement Maturity Logic.
1. Fresh Scrape: A new post is scraped immediately but marked with a future rescrape_after timestamp in the DB and the Markdown front-matter.
2. Maturation: Once that time passes, the module re-fetches the thread, updates the metadata (e.g., new score/metrics), and appends the finalized conversation to the file.
3. Disablement: Setting `rescrape_newer_than_hours` or `rescrape_threshold_hours` to 0 must disable this entirely, making every scrape final.

### The Exclude vs Ignore Paradigm
All modules must strictly differentiate between parameters that filter at the data source (Exclude) and parameters that filter the payload locally after retrieval (Ignore).
### Exclude
parameters (`exclude_terms`, `exclude_author`, `exclude_urls`) are pushed to the source API's search endpoint to improve the 25-item response pool.
### Ignore
parameters (`ignore_older_than_hours`, `ignore_below_score`) are processed locally in Python to trim unwanted data before disk writes.

### Automatic Internal Linking (The Graph)
Where applicable, scrapers should convert external URLs pointing to the origin platform into internal Markdown links (e.g., [[Origin_ID]]). This allows the generated files to form a cohesive, interconnected graph within tools like Obsidian.

## 9. Standard Metadata & Nomenclature

Consistency across modules is mandatory. Front-matter fields and database columns must use standardized naming for the baseline schema (Module specifics can extend this):

- post_id: The unique, immutable identifier from the source platform.
- metadata_label: (e.g., project or label). Used to categorize the post based on source metadata.
- post_links: (Formerly story_link). Used to link to related internal notes or external URLs.
- rescrape_after: The ISO timestamp dictating when the Living Note should be updated.

## 10. Path Configuration, File Rules & Debug Isolation

### Configurable Paths
Every module must expose the following path variables to the Agnostic Interaction Model (Config, CLI, Python overrides), allowing users or overarching orchestrators granular control over where data lives:
- `md_output_directory`: Where the final Markdown notes are saved (e.g., a specific folder in an Obsidian vault).
- `data_output_directory`: Where the SQLite cache and JSON archives are saved.
- `auth_directory`: Where sensitive API keys, OAuth tokens, or credential files are stored (e.g., `sandman_config/auth/`).

### Filename Pattern
Filenames must be completely decoupled from volatile metadata (like categories or title), using keyIDs generated from URLs or similar to ensure duplicate scrapes are detected.
- Standard: `[OriginEntity]_[post_id].md` (e.g., `reddit_1rm32fu.md`).

### Automated Folder Organization
Modules must support a generate_folders (e.g., group_by_source) boolean toggle.
- True: Files are sorted into subdirectories based on their origin (e.g., md_output_directory/OriginEntity/File.md).
- False: All files are placed directly in the root of the md_output_directory.

### Debug Mode Isolation (CRITICAL)
Each module includes a Debug Mode flag, acting as a hard safety override.
- When True: The module MUST completely ignore all user-configured `md_output_directory` and `data_output_directory` settings. It strictly isolates and forces all operations into a local `./data/` folder relative to the script. This guarantees that a developer can test the scraper without accidentally writing files into a user's live production vault or polluting their research environment.
- Auth Directory Exception: Debug mode MUST NOT override the user's configured `auth_directory`. A developer testing the module must still be able to authenticate using their existing credentials without having to duplicate sensitive keys into the local debug folder.
- Predictable Output & Gitignore: Because debug mode forces output locally, the resulting directories are always consistently named (e.g., a local `/data` folder containing `/data/json`, `/data/database.db`, and a local markdown output folder). Because this structure is predictable, these paths must be universally included in every module's `.gitignore` file to ensure test data is never accidentally committed to the repository.

## 11. The Data Contract: Standard Schema

To avoid duplication, every module must translate its raw platform data into a standardized intermediate dictionary within the Processor class. This allows a shared Theme Engine to render any module's data. Keys include:

- post_id: Immutable unique ID from the platform.
- title: The primary headline (Subject, Post Title, Video Name).
- author: The creator (Sender, Redditor, Channel).
- content: The main body text.
- time_scraped: Timestamp of the original creation of the markdown file.
- time_posted: Timestamp of the original post being scraped.
- metadata_label: The primary category (Reddit post: Flair, Email Label, Folder etc.).
- comments: A recursive list of objects containing author, score, and body (useful for threaded platforms).
- score: int, karma, total upvotes/likes etc.
- module: Which scraper created this file?

## 12. Module Documentation Pattern

To maintain consistency and avoid context rot, every module follows a standardized documentation pattern. The root repository of Sandman holds the global standards, while individual modules only document their specific deviations and implementations.

### Every Module README MUST Include:
#### Key Dependencies
A list of all libraries and resources used, explaining *how* they are used (e.g., "imaplib for Gmail connection") and *why* they were chosen (e.g., "to maintain zero-dependency reliability"). This ensures that any developer (or AI) can quickly grasp the technical stack and its rationale.

### The Universal Blueprint (This Document)
This document (`unified_module_blueprint.md`) lives ONLY at the root of the Sandman project (`modules/unified_module_blueprint.md`). It dictates the architectural rules, class structure (The 5 Buckets), schema baselines, and core philosophies shared across all modules. To prevent duplication, this file is NEVER copied into individual module repositories.

### The User Guide (README.md)
Each module contains a user-facing manual located at the root of its own repo (e.g., `modules/[module_name]/README.md`).
- Context: It references the universal blueprint for global features and usage modes.
- Instructions: It details how to install and quick-start the specific module.
- Platform Specifics: The final section of the README serves as the definitive guide to how this module extends the baseline rules. This includes unique front-matter variables (e.g., adding cc and bcc for Gmail), unique data mapping logic, module-specific configuration toggles (e.g., sort methods for Reddit), and any authentication quirks or rate limit warnings.

### The Architecture Document (architecture.md)
Because the unified blueprint is kept out of individual module repos, a module's `architecture.md` file (stored in a git-ignored `/documentation` or `/docs` folder, e.g., `modules/[module_name]/docs/architecture.md`) serves as the definitive, standalone development guide for that specific module's build process. 

The development process starts with a human developer drafting a rough `README.md` that outlines the module's goals and target platform. From that initial idea, the developer (or an AI assistant) applies the global mandates from this unified blueprint to spawn the `architecture.md` document. It acts as the bridge:
- It translates the "5 Buckets" class architecture into concrete plans for the target platform (e.g., "The Client class will use IMAP for email retrieval").
- It maps out the exact Standard Schema translation from the specific API endpoint.
- It serves as the single source of truth during the coding phase, eliminating the need to cross-reference the global blueprint continually.

Example (Gmail Scraper Architecture):
- Objective: Capture emails from specific labels and transform them into chronological Markdown notes.
- Technical Strategy: Support Google OAuth and IMAP in the Client class. Cumulative logic in the Orchestrator dictates that new replies in a thread append to the bottom of the original note.
- Standard Schema Mapping: post_id maps to Message-ID, title to Subject, author to Sender.

Once the architecture document is reviewed and agreed upon, it serves as the complete, unambiguous specification needed to build the module.

## 13. Repository & Module Management

Sandman follows a Monolithic Orchestrator, Distributed Modules architecture to ensure maximum modularity and independent development cycles.

### The Sandman Repository
The root repository acts as the master orchestrator. Its `.gitignore` is configured to ignore everything in the `modules/` directory, except for `.md` documentation and `.json` files. This prevents module code from being committed directly to the Sandman repo, ensuring they remain independent entities.
### Module Repositories
Each module is its own independent GitHub repository.
### Module Registry
The `modules/module_registry.json` file in the Sandman root acts as the central directory. it contains the GitHub URLs for every module, allowing the orchestrator (or a developer) to programmatically `git clone` or `git pull` updates for the entire suite.

## 14. Deployment & Environment Standards

To manage dependencies cleanly and ensure smooth server deployment, the Sandman suite follows a "Monolithic Orchestrator, Distributed Modules" architecture.

### Repository Structure
### The Sandman Repository
The root repository acts as the master orchestrator. Its `.gitignore` explicitly ignores the contents of the `modules/` directory, except for `module_registry.json` and `unified_module_blueprint.md`.
### Module Repositories
Each module is its own independent GitHub repository. The `module_registry.json` file in the Sandman root contains the URLs for these modules, allowing the orchestrator to pull or update them dynamically.

### Virtual Environments (`venv`)
#### Local Module Development
When building or testing a module locally, developers must use a dedicated virtual environment inside the module's directory (e.g., `modules/[module_name]/venv`). All dependencies must be captured in a module-specific `requirements.txt`.
#### Master Orchestrator Environment
When running Sandman natively, a master `venv` is created at the root, installing the aggregated requirements of all pulled modules.

### Docker Deployment
When deployed to a server, Sandman uses a Monolithic Docker approach:
#### One Container
A single Docker container is built for the entire Sandman Orchestration Suite.
#### Volume Mapping
Paths defined in the Configuration (such as `md_output_directory`, `data_output_directory`, and `auth_directory`) are mapped as Docker Volumes. This allows the internal modules to read API keys from the host server and write Markdown files directly to the host's live Obsidian vault.

## 14. Bootstrapping a New Module's Development

To create a new module (e.g: scraper for Gmail, Twitter, etc...) that's consistent with the other modules, we must stick to a unified strategy that is so well defined in our documentation that it provides all the necessary guidance for a developer (human or AI) to follow this process:

1. Create a new directory for the module: `modules/[module_name]/`.
2. Write an initial draft of the `README.md` file, defining the source being scraped, important platform-specific variables to extract, and the overall outline of the resulting JSON/md files.
3. Use this `unified_module_blueprint.md` file to map the requirements from your rough `README.md` into our standard architecture.
4. Create a new Architecture Document (`modules/[module_name]/docs/architecture.md`). Detail the technical strategy, how it implements the "5 Buckets", and define the schema mapping based on the blueprint. This file will guide the entire build process.
5. Review and finalize the architecture document.
6. Scaffold the internal architecture into the "5 Buckets" (Config, Client, Processor, DatabaseManager, Scraper) usually under a `core/` subdirectory.
7. Create a `templates/` folder inside the module with `note.template` and `comment.template`.
8. Implement the Client and Processor.
9. Wire the logic together with the Orchestrator.
10. Add a test task to the master `config.yml` and verify the State Reconciliation Flow.

## Sandman Universal Nomenclature Reference

This reference outlines the unified naming conventions used across the Sandman ecosystem. The names are consistent across all module interfaces, but their context changes depending on where they are used.

### Context Interfaces

#### Config File
The keys used in `config.yml` to define module behavior and default routine.
#### CLI Flag
The command-line arguments used to execute a module directly from the terminal.
#### Python
The argument variables or dictionary keys used when running a module as an imported Python class.
#### Markdown Frontmatter
The structured metadata block at the top of generated `.md` files.
#### JSON Data
The properties within the generated raw `.json` output files.

---

### 1. Sourcing & Identification

These variables define where data is coming from and what it is called.

| Name | Interface Usage | Description |
| :--- | :--- | :--- |
| `source` | Config / CLI (`--source`) / Python | The platform or sub-community being targeted. Optionally used for subfolders. (e.g., subreddits in the reddit2md module, websites in a web scraper, etc...). |
| | Frontmatter / JSON | Identifies the origin of the scraped post. |
| `post_id` | Frontmatter / JSON | A unique identifier derived from the source platform's own ID system. |
| `post_URL` | Frontmatter / JSON | The direct web link to the original content on the source platform. |
| `poster` | Frontmatter / JSON | The author, OP, or entity that created the post being scraped (e.g., 'employer_name' when scraping indeed job listsings, 'OP' when scraping reddit posts, 'Authur' of articles, etc...). |
| `module` | Frontmatter / JSON | The Sandman module that generated the file (e.g., 'reddit2md'). Identifies the file as scraped/generated output, and the module that created it. |

---

### 2. Search & Filtering

These variables define how to query the source and what to ignore.

| Name | Interface Usage | Description |
| :--- | :--- | :--- |
| `query` | Config / CLI (`--query`) / Python | The main search term (used predominantly in job or web scrapers). |
| `min_score` | Config / CLI (`--min-score`) / Python | The minimum score or upvotes required to process a post. |
| `exclude_terms` | Config / CLI (`--exclude-terms`) / Python | List of keywords. If found in the title/body, the post is skipped and/or filtered at the API level. (Replaces `blacklist_terms`) |
| `exclude_urls` | Config / CLI (`--exclude-urls`) / Python | List of domain fragments to ignore when capturing links. (Replaces `blacklist_urls`) |
| `ignore_newer_than_hours` | Config / CLI (`--ignore-newer-than-hours`) / Python | Minimum time a post must exist before it is considered mature. (Replaces `min_age_hours`) |
| `ignore_older_than_hours` | Config / CLI (`--ignore-older-than-hours`) / Python | Maximum age for a post to be considered fresh/relevant. (Replaces `max_age_hours`) |
| `rescrape_newer_than_hours` | Config / CLI / Python | Triggers maturity queue. If younger than limit, queue for rescrape. (Replaces `rescrape_threshold_hours`) |
| `track` | Config / CLI (`--track`) / Python | Boolean. Enable or disable SQLite DB tracking for this task. Set False for testing. |

---

### 3. Limits & Data Management

These variables dictate the size and retention of your data footprint.

| Name | Interface Usage | Description |
| :--- | :--- | :--- |
| `max_results` | Config / CLI (`--max-results`) / Python | The maximum number of new items to fetch during a single run. |
| `db_limit` | Config / CLI (`--db-limit`) / Python | Footprint control. The maximum number of records to keep in the SQLite cache. |
| `offset` | Config / CLI (`--offset`) / Python | Integer. Skips the first N results before processing. |
| `save_json` | Config / CLI (`--save-json`) / Python | Boolean. Whether to save a sanitized `.json` copy. |
| `save_md` | Config / CLI (`--save-md`) / Python | Boolean. Whether to generate a Markdown file. |
| `detailed_db` | Config / CLI (`--detailed-db`) / Python | Boolean. Expands SQLite schema to capture full JSON payload in DB. |
| `md_log` | Config / CLI (`--md-log`) / Python | Boolean. Whether to append run results to the human-readable Scrape Log. |
| `verbose` | Config / CLI (`--verbose`) / Python | Integer (0, 1, 2). Controls console output verbosity. |

---

### 4. Categorization & Output Formatting

These variables define how the data is presented and organized locally.

| Name | Interface Usage | Description |
| :--- | :--- | :--- |
| `label` | Config / CLI (`--label`) / Python | Custom user-defined categorization override (formerly 'flair'). |
| | Frontmatter / JSON | Classifications provided by the source or overridden by the user. |
| `group_by_source` | Config / CLI (`--group-by-source`) / Python | Boolean. Whether to create sub-folders for each source (e.g., `/reddit/news/`). |
| `detail` | Config / CLI (`--detail`) / Python | Controls output depth (e.g., capturing XS vs XL comment trees). |
| `sort` | Config / CLI (`--sort`) / Python | The sorting method applied to the source feed (e.g., 'new', 'top'). |
| `post_links` | Frontmatter / JSON | A list of all external URLs found within the content. |
| `date_posted` | Frontmatter / JSON | The original publication timestamp of the post. |
| `date_scraped`| Frontmatter / JSON | The timestamp of when Sandman extracted the data. |

