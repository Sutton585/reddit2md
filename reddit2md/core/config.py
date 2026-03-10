import yaml
import os
import sys

class Config:
    DEFAULT_CONFIG = {
        "settings": {
            "debug": False,
            "data_output_directory": "data",
            "md_output_directory": "data/markdown",
            "md_log": "data/Scrape Log.md",
            "rescrape_threshold_hours": 12,
            "min_score": 50,
            "max_results": 8,
            "detail": "MD",
            "verbose": 2,
            "group_by_source": False,
            "save_json": True,
            "md_log": True,
            "db_limit": 1000,
            "blacklist_terms": ["[Marvel Rewatch]", "Recurring Free Talk"],
            "blacklist_urls": ["reddit.com/r/marvelstudiosspoilers/wiki"]
        },
        "routine": [
            {
                "source": "MarvelStudiosSpoilers",
                "sort": "new"
            }
        ]
    }

    def __init__(self, config_path="config.yml"):
        self.config_path = config_path
        self.data = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            print(f"Config file {self.config_path} not found. Creating template.")
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self.DEFAULT_CONFIG, f, default_flow_style=False)
                return self.DEFAULT_CONFIG
            except Exception as e:
                print(f"Error creating {self.config_path}: {e}", file=sys.stderr)
                return self.DEFAULT_CONFIG

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading {self.config_path}: {e}", file=sys.stderr)
            return self.DEFAULT_CONFIG

    def get_settings(self):
        return self.data.get('settings', self.DEFAULT_CONFIG['settings'])

    def get_routine(self):
        """Returns the raw list of scrape tasks from the routine."""
        # Fallback to 'jobs' or 'sources' if people haven't updated yet, but prefer 'routine'
        return self.data.get('routine', self.data.get('jobs', self.data.get('sources', self.DEFAULT_CONFIG['routine'])))

    def get_task_config(self, task_data):
        """Merges global defaults with a specific task's overrides."""
        settings = self.get_settings()
        config = settings.copy()
        config.update(task_data)
        return config

    def get_all_routine_configs(self):
        """Returns a list of all fully-merged task configurations in the routine."""
        return [self.get_task_config(t) for t in self.get_routine()]

    def get_adhoc_task_config(self, source):
        """Creates a default task configuration for a source not in the list."""
        settings = self.get_settings()
        config = settings.copy()
        config['source'] = source
        return config
