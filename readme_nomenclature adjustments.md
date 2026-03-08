

# More nomenclature standardization
This shoudl standardize ALL user-facing variables. All examples are from the readme.md file

Wrong:
```bash
python reddit2md.py --subreddit news --limit 5 --detail XL --sort top --age 24
```

Correct:
```bash
python reddit2md.py --source news --max_results 5 --detail XL --sort top --post_age_min 24
```

Wrong:
```
scraper.run(subreddit_name="MarvelComics", overrides={'post_limit': 5, 'comment_detail': 'XL'})
```

Correct:
```
scraper.run(subreddit_name="MarvelComics", overrides={'max_results': 5, 'detail': 'XL'})
```


### Using the Configuration File
Wrong:
```json
{
    "global_defaults": {
        "output_directory": "My Vault/Reddit",
        "min_score": 50,
        "data_directory": "data"
    },
    "jobs": [
        { 
            "name": "Python", 
            "sort": "top" 
        },
        { 
            "name": "Python", 
            "comment_detail": "XL" 
        }
    ]
}
```

Correct:
```json
{
    "global_defaults": {
        "output_directory": "My Vault/Reddit",
        "min_score": 50,
        "data_directory": "data"
    },
    "jobs": [
        { 
            "source": "Python", 
            "sort": "top" 
        },
        { 
            "source": "Python", 
            "detail": "XL" 
        }
    ]
}
```


wrong:
```
### Post Limit
Description: The maximum number of new threads reddit2md will attempt to fetch from a subreddit feed during a single run.
- Config: "post_limit": 8
- CLI: --limit 8
- Python: 'post_limit': 8
```

correct:
```
### max_results
Description: The maximum number of new posts reddit2md will attempt to fetch from a subreddit (source) during a single run.
- Config: "max_results": 8
- CLI: --max_results 8
- Python: 'max_results': 8
```
wrong:
```
### Comment Detail Presets
Description: Presets to control the exact volume and depth of comments captured. 
- XS: Top 3 top-level comments, 0 replies (Literal: 3 total).
- SM: Top 5 top-level comments, 1 reply each (Literal: 5 + 5 = 10 max).
- MD (Default): Top 8 top-level comments, 2 replies each (Literal: 8 + 16 = 24 max).
- LG: Top 10 top-level comments, 3 depth (3 replies, 1 sub-reply) (Literal: 10 + 30 + 30 = 70 max).
- XL: No limits. Recursively captures every single comment and reply.
	- Config: "comment_detail": "MD"
	- CLI: --detail MD
	- Python: 'comment_detail': 'MD'
```
correct:
```
### Comment Detail Presets
Description: Presets to control the exact volume and depth of comments captured. 
- XS: Top 3 top-level comments, 0 replies (Literal: 3 total).
- SM: Top 5 top-level comments, 1 reply each (Literal: 5 + 5 = 10 max).
- MD (Default): Top 8 top-level comments, 2 replies each (Literal: 8 + 16 = 24 max).
- LG: Top 10 top-level comments, 3 depth (3 replies, 1 sub-reply) (Literal: 10 + 30 + 30 = 70 max).
- XL: No limits. Recursively captures every single comment and reply.
	- Config: "detail": "MD"
	- CLI: --detail MD
	- Python: 'detail': 'MD'
```
Wrong:
```
### Flair
Description: Categorizes the post based on its source metadata.
- Config: "flair": "Value"
- CLI: --flair Value
- Python: 'flair': 'Value'
```
Correct:
```
### Flair and Labels
Description: Categorizes the post based on its the reddit flair.
- Config: "label": "Value"
- CLI: --label Value
- Python: 'label': 'Value'
```
Wrong:
```
### Post Link
Description: Metadata field for links to external URLs or internal Obsidian links to related scraped posts. The first link will always be the primary link of the reddit post itself.
- Config: "post_link": "URL"
- CLI: --post-link URL
- Python: 'post_link': 'URL'
```
correct:
```
### post_links
Description: Metadata field for links to external URLs. The first link will always be the primary link of the reddit post itself.
- Config: "post_links": "URL"
- CLI: --post-links URL
- Python: 'post_links': 'URL'
```
### Save JSON
Description: Whether the sanitized JSON data fetched from Reddit is persisted to your data directory after the Markdown note is generated.
- Config: "save_json": true
- CLI: --save-json [True/False]
- Python: 'save_json': True

Wrong:
```
### Update Scrape Log
Description: Whether the human-readable Scrape Log.md dashboard is updated during the run.
- Config: "update_log": true
- CLI: --update-log [True/False]
- Python: 'update_log': True
```
correct:
```
### md_log (Markdown Logging)
Description: Whether the human-readable Scrape Log.md is created/updated.
- Config: "md_log": true
- CLI: --md-log [True/False]
- Python: 'md_log': True
```


Wrong:
```
### Maximum DB Records
Description: Footprint control for the SQLite cache. When the DB exceeds this limit, the oldest records are pruned (does not touch Markdown files).
- Config: "max_db_records": 1000
- CLI: --max-records 1000
- Python: 'max_db_records': 1000
```
correct:
```
### DB size Limit: db_limit
Description: Footprint control for the SQLite cache. When the DB exceeds this limit, the oldest records are pruned (does not touch Markdown files).
- Config: "db_limit": 1000
- CLI: --db_limit 1000
- Python: 'db_limit': 1000
```
### Reddit Sort Method
Description: Choice of sort determines the flavor of your research: new (Default) for real-time tracking, hot for discovery, top for historical quality, or rising for momentum.
- Config: "sort": "new"
- CLI: --sort new
- Python: 'sort': 'new'

Wrong:
```
### Minimum Post Age Hours
Description: The window of time a post must exist before it is considered mature. Set to 0 to disable re-scraping logic entirely.
- Config: "min_post_age_hours": 12
- CLI: --age 12
- Python: 'min_post_age_hours': 12
```
correct:
```
### Minimum Post Age (in hours)
Description: The window of time a post must exist before it is considered mature. Set to 0 to disable re-scraping logic entirely.
- Config: "min_age_hours": 12
- CLI: --min_age_hours 12
- Python: 'min_age_hours': 12
```

wrong:
```
### Filter Keywords
Description: Case-insensitive keywords. If any appear in a post title, the post is skipped.
- Config: "filter_keywords": ["word1", "word2"]
- CLI: --filter "word1, word2"
- Python: 'filter_keywords': ["word1", "word2"]
```
correct:
```
### Blacklist phrases/terms
Description: Case-insensitive keywords. If any appear in a post title, the post is skipped.
- Config: "blacklist_terms": ["word1", "word2"]
- CLI: --blacklist_terms "word1, word2"
- Python: 'blacklist_terms': ["word1", "word2"]
```

wrong:
```
### URL Blacklist
Description: Prevents specific domains or fragments from being included in post_link metadata.
- Config: "url_blacklist": ["fragment1", "fragment2"]
- CLI: --blacklist "fragment1, fragment2"
- Python: 'url_blacklist': ["fragment1", "fragment2"]
```
correct:
```
### Blacklist Links
Description: Prevents specific domains or fragments from being included in post_links field.
- Config: "blacklist_urls": ["fragment1", "fragment2"]
- CLI: --blacklist_urls "fragment1, fragment2"
- Python: 'blacklist_urls': ["fragment1", "fragment2"]
```

wrong:
```
### Subreddit Folders
Description: Whether the system creates a sub-folder for each subreddit within your output directory.
- Config: "generate_subreddit_folders": false
- CLI: --folders [True/False]
- Python: 'generate_subreddit_folders': False
```
correct:
```
### Subfolders for each Subreddit (source)
Description: Whether the system creates a sub-folder for each subreddit within your output directory.
- Config: "group_by_source": false
- CLI: --group_by_source [True/False]
- Python: 'group_by_source': False
```

