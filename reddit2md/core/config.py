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
            "max_results": 8,
            "detail": "MD",
            "verbose": 2,
            "group_by_source": False,
            "save_json": True,
            "enable_md_log": True,
            "db_limit": 1000,
            "track": True,

            # Routine identity
            "name": None,

            # URL-level, no q=
            "post_type": None,
            "allow_nsfw": False,
            "timeframe": None,

            # URL-level, forces q= (exclude group)
            "search": None,
            "label": None,
            "label_exact": None,
            "exclude_label": [],
            "exclude_terms": ["[Marvel Rewatch]", "Recurring Free Talk"],
            "exclude_urls": [],
            "exclude_author": [],

            # Local only (ignore group)
            "ignore_urls": ["reddit.com/r/marvelstudiosspoilers/wiki"],
            "ignore_below_score": 50,
            "ignore_older_than_hours": None,
            "ignore_older_than_days": None,
            "ignore_newer_than_hours": None,
            "ignore_newer_than_days": None,
            "rescrape_newer_than_hours": 12,
            "rescrape_newer_than_days": None,
            "ignore_below_upvote_ratio": None,
            "ignore_below_comments": None,
            
            # Additional API-level parameters
            "author": [],
            "domain": [],
            "selftext": [],
            "title_search": [],
            "nsfw_only": False,
            "spoiler": False,
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
        """Returns the raw list of scrape routines from the config."""
        # Fallback to 'jobs' or 'sources' if people haven't updated yet, but prefer 'routine'
        return self.data.get('routine', self.data.get('jobs', self.data.get('sources', self.DEFAULT_CONFIG['routine'])))

    def get_routine_config(self, routine_data):
        """Merges global defaults with a specific routine's overrides, and normalizes aliases."""
        settings = self.get_settings()
        config = settings.copy()
        config.update(routine_data)

        # 1. Source aliases
        for alias in ['sources', 'subreddit', 'subreddits', 'reddit', 'reddits']:
            if alias in config:
                if 'source' not in config: config['source'] = config[alias]
                del config[alias]
                
        # 2. label/flair
        if 'flair' in config:
            if 'label' not in config or not config['label']: config['label'] = config['flair']
            del config['flair']

        # 3. label_exact/flair_exact (and old exact_flair fix)
        for alias in ['flair_exact', 'exact_flair']:
            if alias in config:
                if 'label_exact' not in config or not config['label_exact']: config['label_exact'] = config[alias]
                del config[alias]

        # 4. exclude_label/exclude_flair
        if 'exclude_flair' in config:
            if 'exclude_label' not in config or not config['exclude_label']: config['exclude_label'] = config['exclude_flair']
            del config['exclude_flair']

        # 5. exclude_terms & blacklists
        for alias in ['exclude', 'excludes', 'exclude_term', 'blacklist', 'blacklist_terms', 'blacklist_term', 'blacklists']:
            if alias in config:
                if 'exclude_terms' not in config or not config['exclude_terms']: config['exclude_terms'] = config[alias]
                del config[alias]

        # 6. exclude_author/exclude_authors
        if 'exclude_authors' in config:
            if 'exclude_author' not in config or not config['exclude_author']: config['exclude_author'] = config['exclude_authors']
            del config['exclude_authors']

        # 7. ignore_urls & blacklist_urls
        for alias in ['ignore_url', 'blacklist_urls', 'blacklist_url']:
            if alias in config:
                if 'ignore_urls' not in config or not config['ignore_urls']: config['ignore_urls'] = config[alias]
                del config[alias]

        # 8. ignore_below_score/min_score
        if 'min_score' in config:
            if 'ignore_below_score' not in config or config['ignore_below_score'] is None: config['ignore_below_score'] = config['min_score']
            del config['min_score']

        # 9. timeframe/time_filter
        if 'time_filter' in config:
            if 'timeframe' not in config or not config['timeframe']: config['timeframe'] = config['time_filter']
            del config['time_filter']

        # 10/11. ignore_older_than_hours (max_age) and ignore_newer_than (min_age)
        if 'max_age_hours' in config:
            if 'ignore_older_than_hours' not in config or config['ignore_older_than_hours'] is None: config['ignore_older_than_hours'] = config['max_age_hours']
            del config['max_age_hours']

        if 'min_age_hours' in config:
            if 'ignore_newer_than_hours' not in config or config['ignore_newer_than_hours'] is None: config['ignore_newer_than_hours'] = config['min_age_hours']
            del config['min_age_hours']

        # 13. rescrape_threshold_hours
        for alias in ['rescrape_threshold_hours', 'rescrape_threshold']:
            if alias in config:
                if 'rescrape_newer_than_hours' not in config or config['rescrape_newer_than_hours'] is None: config['rescrape_newer_than_hours'] = config[alias]
                del config[alias]

        # 14. _days conversions
        for base in ['ignore_older_than', 'ignore_newer_than', 'rescrape_newer_than']:
            days_key = f"{base}_days"
            hours_key = f"{base}_hours"
            if days_key in config and config[days_key] is not None:
                if hours_key not in config or config[hours_key] is None:
                    config[hours_key] = config[days_key] * 24
                del config[days_key]

        # 15. search/query
        if 'query' in config:
            if 'search' not in config or not config['search']: config['search'] = config['query']
            del config['query']

        # 16. List normalizations
        list_keys = ['label', 'exclude_label', 'exclude_terms', 'exclude_urls', 'exclude_author', 'ignore_urls', 'author', 'domain', 'selftext', 'title_search']
        for k in list_keys:
            if k in config:
                if isinstance(config[k], str):
                    config[k] = [config[k]] if config[k] else []
                elif config[k] is None:
                    config[k] = []

        return config

    def get_all_routine_configs(self):
        """Returns a list of all fully-merged configurations in the routine."""
        return [self.get_routine_config(t) for t in self.get_routine()]

    def get_adhoc_routine_config(self, source):
        """Creates a default configuration for a source not in the regular routine list."""
        settings = self.get_settings()
        config = settings.copy()
        config['source'] = source
        return config
