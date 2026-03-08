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

    def get_jobs(self):
        """Returns the raw list of scrape jobs from the config."""
        return self.data.get('jobs', self.data.get('calls', self.data.get('sources', self.DEFAULT_CONFIG['sources'])))

    def get_job_config(self, job_data):
        """Merges global defaults with a specific job's overrides."""
        global_defaults = self.get_global_defaults()
        config = global_defaults.copy()
        config.update(job_data)
        return config

    def get_all_job_configs(self):
        """Returns a list of all fully-merged job configurations."""
        return [self.get_job_config(j) for j in self.get_jobs()]

    def get_adhoc_job_config(self, subreddit_name):
        """Creates a default job configuration for a subreddit not in the list."""
        global_defaults = self.get_global_defaults()
        config = global_defaults.copy()
        config['name'] = subreddit_name
        return config
