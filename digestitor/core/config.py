import json
import os
import sys

class Config:
    DEFAULT_CONFIG = {
        "global_defaults": {
            "debug": False,
            "data_directory": "data",
            "output_directory": "data/markdown",
            "scrape_log_path": "data/Scrape Log.md",
            "min_post_age_hours": 12,
            "min_score": 50,
            "post_limit": 8,
            "comment_detail": "MD",
            "generate_subreddit_folders": False,
            "save_json": True,
            "update_log": True,
            "max_db_records": 1000,
            "filter_keywords": ["[Marvel Rewatch]", "Weekly Free Talk"],
            "url_blacklist": ["reddit.com/r/marvelstudiosspoilers/wiki"]
        },
        "sources": [
            {
                "name": "MarvelStudiosSpoilers",
                "sort": "new"
            }
        ]
    }

    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.data = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            print(f"Config file {self.config_path} not found. Creating template.")
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.DEFAULT_CONFIG, f, indent=4)
                return self.DEFAULT_CONFIG
            except Exception as e:
                print(f"Error creating {self.config_path}: {e}", file=sys.stderr)
                return self.DEFAULT_CONFIG

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {self.config_path}: {e}", file=sys.stderr)
            return self.DEFAULT_CONFIG

    def get_global_defaults(self):
        return self.data.get('global_defaults', self.DEFAULT_CONFIG['global_defaults'])

    def get_sources(self):
        return self.data.get('sources', self.DEFAULT_CONFIG['sources'])

    def get_source_config(self, source_name):
        global_defaults = self.get_global_defaults()
        sources = self.get_sources()
        
        source = next((s for s in sources if s['name'] == source_name), None)
        if not source:
            # Fallback to global defaults for ad-hoc source
            config = global_defaults.copy()
            config['name'] = source_name
            return config
        
        # Merge global defaults with source overrides
        config = global_defaults.copy()
        config.update(source)
        return config

    def get_all_source_configs(self):
        return [self.get_source_config(s['name']) for s in self.get_sources()]
