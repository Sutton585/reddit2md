# Digestitor: The Reddit to Markdown Digestor
Digestitor is a professional-grade Reddit scraper designed for high-signal knowledge management. It transforms transient Reddit discussions into permanent, well-structured Markdown notes for use in Obsidian vaults, AI-automated workflows, and personalized daily digests.

Whether you are building a research database, feeding an AI agent, or just keeping up with specific subreddits, Digestitor provides the granularity and control needed for a high-quality data pipeline. It requires no external Python libraries, relying entirely on the Python standard library for maximum portability and security.

## System Overview and Core Logic
Digestitor operates on a hierarchical model where data flows from Reddit's RSS and JSON APIs into local structured storage. The system is designed to be resilient, allowing users to manage their data directly through the file system.

### The Multi-Layer Source of Truth
Digestitor uses a tripartite authority model to ensure data integrity:
- **Markdown Files (The Authority):** The ultimate source of truth. If you edit the `flair` or `rescrape_after` date in your Obsidian note, the system detects this on the next run and updates the database. Deleting a note tells the system to "forget" the post entirely.
- **SQLite Database (The Memory):** Acts as a high-speed cache and state-tracker. It handles the logic for maturity delays and history. The DB is "self-healing"—if deleted, it will automatically rebuild itself by scanning your Markdown folders.
- **JSON Archive (The Backup):** Stores sanitized data for every scrape. This allows for a total vault rebuild without re-querying Reddit if your Markdown files are ever lost.

### Safe Vault Coexistence
To allow Digestitor notes to live alongside your existing research, the system uses a surgical ownership check. It only processes files where the `post_id` in the front-matter is present. This prevents the scraper from ever touching unrelated Markdown files in the same directory.

### Cumulative Knowledge (Living Notes)
Standard scrapers overwrite files, losing previous data. Digestitor creates chronological records. When a post is re-scraped (e.g., after it "matures"):
1. The front-matter is updated with the latest score and metadata.
2. The old comment section is preserved.
3. A new `## Updated Comments ([Timestamp])` section is **appended** to the bottom.
This allows you to track how discussions evolve over time within a single note.

### Context vs. Freshness: The Maturity Logic
Scraping a thread the moment it is posted often misses the best discussion. Digestitor uses the `min_post_age_hours` setting to solve this. If a post is "young," it is scraped immediately for freshness, but marked as "Maturing." The system then automatically returns after the age threshold is met to append the final, mature conversation.

## Comprehensive Configuration Guide
Every aspect of Digestitor can be controlled through the config file, the command line, or as a Python dependency.

### Post Limit
...
### Flair
This setting categorizes the post based on its source metadata (e.g., Reddit Flair).
- In the config file, use "flair".
- On the CLI, use --flair. 
- In Python, pass 'flair' in the overrides dictionary.

### Post Link
This field in the front-matter contains links to external URLs or internal Obsidian links to related scraped posts.
- In the config file, use "post_link".
- On the CLI, use --post-link.
- In Python, pass 'post_link' in the overrides dictionary.

### Save JSON
This toggle determines whether the sanitized JSON data fetched from Reddit is persisted to your data directory after the Markdown note is generated. Disabling this can save significant disk space if you only need the final notes.
- In the config file, use "save_json".
- On the CLI, use --save-json [True/False].
- In Python, pass 'save_json' in the overrides dictionary.

### Update Scrape Log
This toggle controls whether the human-readable "Scrape Log.md" dashboard is updated during the run.
- In the config file, use "update_log".
- On the CLI, use --update-log [True/False].
- In Python, pass 'update_log' in the overrides dictionary.

### Maximum DB Records
Since the database acts as an essential memory cache, it cannot be disabled. However, you can control its footprint using this setting. When the DB exceeds this limit, the oldest records are pruned (this does not touch your Markdown files).
- In the config file, use "max_db_records".
- On the CLI, use --max-records [Number].
- In Python, pass 'max_db_records' in the overrides dictionary.

### Comment Detail Presets
The system provides several presets to control the exact volume and depth of comments captured. This allows you to balance file size against the depth of the discussion.
- XS Level
    The XS level captures the top 3 top-level comments with 0 replies. This is ideal for high-volume subreddits where you only want the most critical initial reactions.
- SM Level
    The SM level captures the top 5 top-level comments and includes up to 1 reply for each. It provides a brief sense of the conversation without filling the note with deep threads.
- MD Level
    The default MD setting captures the top 8 top-level comments and includes up to 2 replies for each. This is the recommended balance for most users.
- LG Level
    The LG level is designed for deeper research. It captures the top 10 top-level comments, up to 3 replies for each of those (Level 2), and up to 1 sub-reply for those (Level 3). This captures a significant portion of the most active discussions.
- XL Level
    The XL level is a special mode that removes all limits. It recursively captures every single comment and reply available in the thread, providing a complete and total archive of the discussion.

### Minimum Score
The minimum score setting acts as a quality filter. Any post with a score lower than this threshold will be skipped entirely. 
- In the config file, use "min_score". 
- On the CLI, use --min-score. 
- In Python, pass 'min_score' in the overrides dictionary.

### Comment Detail
The comment detail setting selects one of the presets (XS, SM, MD, LG, XL) to control comment depth. 
- In the config file, use "comment_detail". 
- On the CLI, use --detail.
- In Python, pass 'comment_detail' in the overrides dictionary.

### Reddit Sort Method
This setting controls how Digestitor requests the feed from Reddit. You can choose from new, hot, top, or rising. 
- In the config file, use "sort". 
- On the CLI, use --sort. 
- In Python, pass 'sort' in the overrides dictionary.

### Minimum Post Age Hours
This determines the window of time a post must exist before it is considered mature. Posts newer than this will be scheduled for a re-scrape. 
- In the config file, use "min_post_age_hours". 
- On the CLI, use --age. 
- In Python, pass 'min_post_age_hours' in the overrides dictionary.

### Filter Keywords
This is a list of case-insensitive keywords. If any of these words appear in a post's title, the post will be skipped. 
- In the config file, use "filter_keywords" as a JSON list. 
- On the CLI, use --filter with a comma-separated string. 
- In Python, pass 'filter_keywords' as a list.

### URL Blacklist
The URL blacklist prevents specific domains or URL fragments from being included in the story_link metadata of your notes. 
- In the config file, use "url_blacklist" as a JSON list. 
- On the CLI, use --blacklist with a comma-separated string. 
- In Python, pass 'url_blacklist' as a list.

### Debug Mode
Debug mode is a safety toggle that redirects all output into your local data directory. When debug is enabled, the markdown folder and the scrape log are placed inside the data directory instead of your live directory or Obsidian Vault, preventing test runs from polluting your actual records. 
- In the config file, use "debug". 
- On the CLI, use --debug. 
- In Python, set debug=True when initializing the RedditScraper class.

### Data Directory
The data directory is the primary storage hub for Digestitor. It contains the SQLite database file (database.db) and the folder for structured JSON archives (json). 
- In the config file, use "data_directory". 
- On the CLI, use --data-dir.
- In Python, pass 'data_directory' in the overrides dictionary.

### Output Directory
This is the file system path where your generated Markdown notes will be saved during normal (non-debug) runs.
- In the config file, use "output_directory". 
- On the CLI, use --output-dir. 
- In Python, pass 'output_directory' in the overrides dictionary.

### Scrape Log Path
This setting defines the path for the human-readable Markdown dashboard that summarizes your scrape history. 
- In the config file, use "scrape_log_path". 
- On the CLI, use --log-path.
- In Python, pass 'scrape_log_path' in the overrides dictionary.

### Save JSON
This toggle determines whether the sanitized JSON data fetched from Reddit is persisted to your data directory after the Markdown note is generated. Disabling this can save disk space if you only need the final notes.
- In the config file, use "save_json".
- On the CLI, use --save-json [True/False].
- In Python, pass 'save_json' in the overrides dictionary.

### Update Scrape Log
This toggle controls whether the human-readable "Scrape Log.md" dashboard is updated during the run. Often disabled in testing, and if the human-readable log isn't useful, you can use this setting in global defaults to functionally disable it unless overridden.
- In the config file, use "update_log".
- On the CLI, use --update-log [True/False].
- In Python, pass 'update_log' in the overrides dictionary.

### Update Database
This toggle controls whether the scrape is recorded in the local SQLite state database. Disabling this is useful for one-off, transient scrapes where you do not want to track maturity or prevent future re-scrapes.
- In the config file, use "update_db".
- On the CLI, use --update-db [True/False].
- In Python, pass 'update_db' in the overrides dictionary.

## Debug Mode and Path Management
The `debug` flag is a powerful safety toggle designed to protect your live data during testing. Its behavior is consistent across all interfaces:

### How Debug Mode Works
- **When Debug is TRUE (Default/Test State):** All custom path settings for `output_directory`, `data_directory`, and `scrape_log_path` are ignored. The system forces all output into the local `/data` folder within the repository. This ensures that test runs do not pollute your Obsidian vault or live research database.
- **When Debug is FALSE (Production State):** The system respects your custom path settings, allowing you to route Markdown notes and logs directly into your preferred workspace (e.g., an Obsidian Vault).

### Configuring Paths and Debug Mode
You can toggle debug mode and set your production paths in three ways:

#### 1. In config.json (Recommended for persistent setups)
Set your permanent Obsidian paths here, then toggle `debug` to `false` when you are ready to go live.
```json
{
    "global_defaults": {
        "debug": false,
        "output_directory": "/Users/name/Documents/MyVault/Reddit",
        "scrape_log_path": "/Users/name/Documents/MyVault/Dashboards/Scrape Log.md"
    }
}
```
#### 2. Via CLI (Ideal for quick overrides)
You can force debug mode on or off from the terminal, regardless of what is in your config file. Unlike standard flags, these accept explicit boolean values for maximum clarity in orchestration scripts.

```bash
# Run a safe test into local /data/ folder
python digestitor.py --debug

# Run a live scrape into your configured Obsidian path
python digestitor.py --no-debug
```


#### 3. As a Python Resource (For developers)
When importing the scraper, pass the `debug` flag directly to the constructor.
```python
from digestitor import RedditScraper
# Initialize in production mode to use your custom config paths
scraper = RedditScraper(debug=False)
```

### Typical Workflow Example
1. **Test:** Set `"debug": true` in your config. Experiment with new subreddits or detail settings. Verify the results in the local `/data/markdown/` directory.
2. **Deploy:** Once satisfied, set `"debug": false` and point your `output_directory` to the live directory, (ie. your Obsidian Vault). All future runs will now populate your vault with beautifully formatted notes organized by subreddit.

## Implementation Examples

### Using the Command Line Interface
The CLI is the most common way to use Digestitor. You can run all configured subreddits by calling the script with no arguments. To scrape any subreddit on the fly, even if it is not in your config, use the --source argument. For example:
```bash
python digestitor.py --source Python --limit 5 --detail XL --sort top --age 24
```

### Using as a Python Dependency
You can import the RedditScraper class into your own projects. This is ideal for building custom AI agents that need fresh Reddit data.
```python
from digestitor import RedditScraper

scraper = RedditScraper(config_path="config.json")
scraper.run(source_name="Python", overrides={'post_limit': 5, 'comment_detail': 'XL'})
```

### Using the Configuration File
The config.json file allows you to set global defaults and then override them for specific subreddits. This is the best way to manage a large list of sources for a daily digest.
```json
{
    "global_defaults": {
        "output_directory": "My Vault/Reddit",
        "min_score": 50,
        "data_directory": "data"
    },
    "sources": [
        { 
            "name": "Python", 
            "sort": "top" 
        },
        { 
            "name": "Obsidian", 
            "comment_detail": "XL" 
        }
    ]
}
```

## Directory Structure and Files
Digestitor organizes its data into three main components. The markdown folder contains the notes you see in your live directory (ie. Obsidian). The json folder inside the data directory contains the structured data used by the system and AI agents. The database.db file inside the data directory acts as the high-speed index. Finally, the Scrape Log.md file provides a more human-readable record showing the status of every post, including which ones are currently maturing and when they are scheduled for their final re-scrape.

## Installation and First Run
To get started, clone the repository to your local machine. Since Digestitor uses only the Python standard library, you do not need to install any external packages. Simply run python digestitor.py in your terminal. On the first run, if no config.json is found, the program will create a template for you. You can then edit this file to add your preferred subreddits and customize your settings.

---
## DOCUMENTATION UPDATES (FOR MANUAL INTEGRATION)
The following blocks should be pasted into the corresponding sections of your README.md.

### PASTE IN SECTION: "Comprehensive Configuration Guide" (After Scrape Log Path)
### Subreddit Folders
This toggle determines whether the system creates a sub-folder for each subreddit within your output directory. If disabled (default), all notes are saved directly into the output directory.
- In the config file, use "generate_subreddit_folders".
- On the CLI, use --folders [True/False].
- In Python, pass 'generate_subreddit_folders' in the overrides dictionary.

### Save JSON
This toggle determines whether the sanitized JSON data fetched from Reddit is persisted to your data directory after the Markdown note is generated. Disabling this can save significant disk space if you only need the final notes.
- In the config file, use "save_json".
- On the CLI, use --save-json [True/False].
- In Python, pass 'save_json' in the overrides dictionary.

### Update Scrape Log
This toggle controls whether the human-readable "Scrape Log.md" dashboard is updated during the run.
- In the config file, use "update_log".
- On the CLI, use --update-log [True/False].
- In Python, pass 'update_log' in the overrides dictionary.

### Update Database
This toggle controls whether the scrape is recorded in the SQLite state database. Disabling this is useful for one-off, transient scrapes where you do not want to track maturity or prevent future re-scrapes.
- In the config file, use "update_db".
- On the CLI, use --update-db [True/False].
- In Python, pass 'update_db' in the overrides dictionary.

### PASTE IN SECTION: "System Overview and Core Logic" (New Subsection)
### Project Name Sanitization
The system automatically sanitizes project names derived from Reddit flairs to ensure they are safe for all file systems. Any forward slashes (`/`) in a project name are replaced with dashes (`-`), preventing unintended nested directory creation.

### PASTE IN SECTION: "Debug Mode and Path Management" (Update CLI Example)
#### 2. Via CLI (Ideal for quick overrides)
You can force debug mode on or off from the terminal. Unlike standard flags, these accept explicit boolean values for maximum clarity in orchestration scripts.
```bash
# Run a safe test into local /data/ folder
python digestitor.py --debug True

# Run a live scrape into your configured production paths
python digestitor.py --debug False
```