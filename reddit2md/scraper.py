import os
import sys
import argparse
import json
import re
import logging
from datetime import datetime, timedelta, timezone
from .core.database import DatabaseManager
from .core.reddit_client import RedditClient
from .core.processor import PostProcessor
from .core.config import Config

class RedditScraper:
    def __init__(self, config_path="config.yml", debug=None, overrides=None):
        self.config_manager = Config(config_path)
        self.settings = self.config_manager.get_settings()
        if overrides:
            self.settings.update({k: v for k, v in overrides.items() if v is not None})
        
        # Priority: CLI argument > Config file > Default False
        config_debug = self.settings.get('debug', False)
        if isinstance(config_debug, str):
            config_debug = config_debug.lower() == 'true'
        self.debug = debug if debug is not None else config_debug
        
        # Set up logging based on verbose integer (0: ERROR, 1: WARNING, 2: INFO)
        verbose_level = self.settings.get('verbose', 2)
        if verbose_level == 0:
            logging.getLogger().setLevel(logging.ERROR)
        elif verbose_level == 1:
            logging.getLogger().setLevel(logging.WARNING)
        else:
            logging.getLogger().setLevel(logging.INFO)
        
        self.client = RedditClient(verbose=verbose_level)
        
        # Unified Data Directory management
        if self.debug:
            self.data_dir = 'data'
            self.output_dir = os.path.join(self.data_dir, "markdown")
            self.md_log = os.path.join(self.data_dir, "Scrape Log.md")
        else:
            self.data_dir = self.settings.get('data_output_directory', 'data')
            self.output_dir = self.settings.get('md_output_directory', 'data/markdown')
            self.md_log = self.settings.get('md_log', 'data/Scrape Log.md')

        self.db_path = os.path.join(self.data_dir, "database.db")
        self.json_dir = os.path.join(self.data_dir, "json")

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.json_dir, exist_ok=True)
        
        self.db_manager = DatabaseManager(self.db_path)
        
        # Step 0: Treat existing Markdown files as the Source of Truth
        processed_ids = self.db_manager.get_processed_ids()
        if not processed_ids:
            if os.path.exists(self.output_dir):
                self.rebuild_db_from_markdown(self.output_dir)

    def rebuild_db_from_markdown(self, output_dir):
        if self.settings.get("verbose", 2) >= 2:
            print("Rebuilding database from individual Markdown files...")
        processor = PostProcessor(self.db_manager, self.settings.get('blacklist_urls', []))
        rebuilt_count = 0
        
        for root, dirs, files in os.walk(output_dir):
            for filename in files:
                if not filename.endswith(".md") or filename == "Scrape Log.md":
                    continue
                    
                file_path = os.path.join(root, filename)
                frontmatter = processor.parse_frontmatter(file_path)
            
                # Robust identification: Only process files with a post_id in frontmatter
                if frontmatter and 'post_id' in frontmatter:
                    post_id = frontmatter['post_id']
                    if self.db_manager.post_exists(post_id):
                        continue
                        
                    label = frontmatter.get('label', 'N/A')
                    author = frontmatter.get('poster', 'N/A')
                    source = frontmatter.get('source', 'N/A')
                    score_str = frontmatter.get('score', '0')
                    score = int(score_str) if score_str.isdigit() else 0
                    post_date_str = frontmatter.get('date_posted')
                    rescrape_after = frontmatter.get('rescrape_after')
                    
                    # Extract title from the Markdown header if available, otherwise filename
                    title = filename
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith('# '):
                                    title = line[2:].strip()
                                    break
                    except: pass
                    
                    try:
                        post_date = datetime.strptime(post_date_str, "%Y-%m-%d") if post_date_str else datetime.now()
                    except:
                        post_date = datetime.now()
                    
                    # Add to DB (JSON dir is relative to data_dir)
                    self.db_manager.add_or_update_post(
                        post_id, title, author, source, label, score, "rebuilt",
                        post_date, file_path, first_scrape=True, rescrape_after=rescrape_after
                    )
                    rebuilt_count += 1
        
        if rebuilt_count > 0:
            if self.settings.get("verbose", 2) >= 2:
                print(f"  Successfully rebuilt {rebuilt_count} records from Markdown files.")

    def validate_state(self):
        if self.settings.get("verbose", 2) >= 1:
            print("Validating local state (Files vs. Database Authority)...")
        posts = self.db_manager.get_all_posts()
        orphans_count = 0
        for p in posts:
            md_missing = p['file_path'] and not os.path.exists(p['file_path'])
            json_path = os.path.join(self.json_dir, f"{p['id']}.json")
            json_missing = not os.path.exists(json_path)
            
            if md_missing or json_missing:
                self.db_manager.delete_post(p['id'])
                if md_missing and os.path.exists(json_path):
                    os.remove(json_path)
                elif json_missing and p['file_path'] and os.path.exists(p['file_path']):
                    os.remove(p['file_path'])
                orphans_count += 1
        
        if orphans_count > 0:
            if self.settings.get("verbose", 2) >= 1:
                print(f"  Resolved {orphans_count} state conflicts.")
        else:
            if self.settings.get("verbose", 2) >= 1:
                print("  State is healthy.")

    def run(self, source=None, overrides=None):
        self.validate_state()
        
        if source:
            # Targeted ad-hoc task
            task_conf = self.config_manager.get_adhoc_task_config(source)
            routine = [task_conf]
        else:
            # Process all tasks defined in routine
            routine = self.config_manager.get_all_routine_configs()

        new_posts_total = 0
        updated_posts_total = 0
        
        # Track if any task wants to update the log, and which log to update
        final_log_path = self.md_log
        any_log_update = False

        for task_config in routine:
            if not task_config: continue
            if overrides:
                task_config.update({k: v for k, v in overrides.items() if v is not None})
            
            # Behavioral check: log path can be overridden per task
            if not self.debug and 'md_log' in task_config:
                final_log_path = task_config['md_log']
            
            if task_config.get('enable_md_log', True):
                any_log_update = True

            new_count, updated_count = self.execute_task(task_config)
            new_posts_total += new_count
            updated_posts_total += updated_count

        if self.settings.get("verbose", 2) >= 1:
            print("\nChecking for maturing posts in database...")
        maturing_posts = self.db_manager.get_maturing_posts()
        if maturing_posts:
            # If a specific source was requested, only mature those
            if source:
                maturing_posts = [p for p in maturing_posts if p['subreddit'].endswith(source)]
            
            for db_post in maturing_posts:
                target_source = db_post['subreddit']
                if target_source.startswith('r/'): target_source = target_source[2:]
                
                # Use default config for maturity updates (unless targeted run)
                post_config = self.settings.copy()
                if overrides:
                    post_config.update({k: v for k, v in overrides.items() if v is not None})
                
                processor = PostProcessor(self.db_manager, post_config.get('blacklist_urls', []), post_config.get('detail', 'MD'))
                post_url = f"https://www.reddit.com{db_post['subreddit'] if db_post['subreddit'].startswith('/r/') else '/r/'+db_post['subreddit']}/comments/{db_post['id']}"
                post_timestamp = datetime.fromisoformat(db_post['post_timestamp'])
                
                success, is_new = self._process_single_post(db_post['id'], post_url, post_timestamp, db_post, post_config, processor)
                if success and not is_new:
                    updated_posts_total += 1

        if any_log_update:
            self.db_manager.export_to_markdown_log(final_log_path)
            
        # Global DB pruning check (respecting the highest db_limit in the current routine)
        db_limit = 1000
        for config in routine:
            db_limit = max(db_limit, config.get('db_limit', 1000))
        self.db_manager.prune_old_records(db_limit)

        if self.settings.get("verbose", 2) >= 1:
            print(f"\nFinished run. Total New: {new_posts_total}, Total Updated: {updated_posts_total}")

    def execute_task(self, config):
        source = config.get('source', 'Unknown')
        sort = config.get('sort', 'new')
        limit = config.get('max_results', 10)
        offset = config.get('offset', 0)

        rss_url = f"https://www.reddit.com/r/{source}/{sort}/.rss"
        if config.get("verbose", 2) >= 1:
            print(f"\nExecuting Task: {source} (Sort: {sort}, Limit: {limit}, Offset: {offset})")

        processor = PostProcessor(self.db_manager, config.get('blacklist_urls', []), config.get('detail', 'MD'))
        posts = self.client.get_posts_from_rss(rss_url, limit, offset=offset)
        
        new_count = 0
        updated_count = 0

        for post_id, post_url, post_date in posts:
            db_post = self.db_manager.get_post(post_id)
            success, is_new = self._process_single_post(post_id, post_url, post_date, db_post, config, processor)
            if success:
                if is_new: new_count += 1
                else: updated_count += 1

        return new_count, updated_count

    def _process_single_post(self, post_id, post_url, post_date, db_post, config, processor):
        should_scrape = False
        first_scrape = True
        
        if not db_post:
            should_scrape = True
        else:
            rescrape_after = db_post['rescrape_after']
            if rescrape_after:
                rescrape_after_dt = datetime.fromisoformat(rescrape_after)
                if datetime.now(timezone.utc) > rescrape_after_dt:
                    should_scrape = True
                    first_scrape = False

        if db_post and db_post['file_path'] and os.path.exists(db_post['file_path']):
            frontmatter = processor.parse_frontmatter(db_post['file_path'])
            if frontmatter:
                user_label = frontmatter.get('label')
                user_rescrape = frontmatter.get('rescrape_after')
                db_update_needed = False
                current_label = db_post['label']
                current_rescrape = db_post['rescrape_after']
                
                if user_label and user_label != current_label:
                    current_label = user_label
                    db_update_needed = True
                
                if current_rescrape and not user_rescrape:
                    current_rescrape = None
                    db_update_needed = True
                    should_scrape = False
                
                if db_update_needed:
                    self.db_manager.add_or_update_post(
                        post_id, db_post['title'], db_post['author'], db_post['subreddit'],
                        current_label, db_post['score'], db_post['sort_method'],
                        db_post['post_timestamp'], db_post['file_path'],
                        first_scrape=False, rescrape_after=current_rescrape
                    )
        
        if not should_scrape:
            return False, False

        if config.get("verbose", 2) >= 2:
            print(f"  Scraping: {post_id}")
        raw_post_data = self.client.fetch_json_from_url(f"{post_url}.json?limit=1000")
        if not raw_post_data: return False, False

        post_item = raw_post_data[0]['data']['children'][0]['data']
        score = post_item.get('score', 0)
        
        if score < config.get('min_score', 0):
            if config.get("verbose", 2) >= 2:
                print(f"  Skipped: Score {score} is below minimum threshold of {config.get('min_score', 0)}.")
            return False, False
            
        title = post_item.get('title', '')
        if any(kw.lower() in title.lower() for kw in config.get('blacklist_terms', [])):
            return False, False

        cleaned_post = processor.clean_json(raw_post_data, post_date)
        
        # Dynamic Output Management
        active_output_dir = self.output_dir
        if not self.debug and 'md_output_directory' in config:
            active_output_dir = config['md_output_directory']
            
        active_json_dir = self.json_dir
        if not self.debug and 'data_output_directory' in config:
            active_json_dir = os.path.join(config['data_output_directory'], "json")

        os.makedirs(active_output_dir, exist_ok=True)
        os.makedirs(active_json_dir, exist_ok=True)

        # JSON Toggle
        if config.get('save_json', True):
            json_path = os.path.join(active_json_dir, f"{post_id}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_post, f, indent=2)

        rescrape_after_iso = None
        min_age_hours = config.get('min_age_hours', 12)
        if min_age_hours > 0:
            age = datetime.now(timezone.utc) - post_date
            if age < timedelta(hours=min_age_hours):
                rescrape_after = post_date + timedelta(hours=min_age_hours)
                rescrape_after_iso = rescrape_after.isoformat()

        # Cumulative Update Check
        is_update = not first_scrape and db_post and db_post['file_path'] and os.path.exists(db_post['file_path'])
        
        if is_update:
            new_frontmatter, update_block, label, source = processor.generate_markdown(cleaned_post, rescrape_after=rescrape_after_iso, is_update=True)
            
            with open(db_post['file_path'], 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update the frontmatter block
            updated_content = re.sub(r'^---\n.*?\n---\n', new_frontmatter, content, flags=re.DOTALL)
            
            # Append the new comments
            updated_content += update_block
            
            with open(db_post['file_path'], 'w', encoding='utf-8') as f:
                f.write(updated_content)
            md_path = db_post['file_path']
        else:
            markdown_content, _, label, source = processor.generate_markdown(cleaned_post, rescrape_after=rescrape_after_iso, is_update=False)
            
            # Filename: [Subreddit]_[ID].md
            md_filename = f"{source}_{post_id}.md"
            
            if config.get('group_by_source', False):
                md_path = os.path.join(active_output_dir, source, md_filename)
            else:
                md_path = os.path.join(active_output_dir, md_filename)
            
            os.makedirs(os.path.dirname(md_path), exist_ok=True)
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

        # Database update is now mandatory for system logic
        self.db_manager.add_or_update_post(
            post_id, cleaned_post['title'], cleaned_post['poster'],
            cleaned_post['source'], label, score, config.get('sort', 'N/A'), post_date, md_path,
            first_scrape=first_scrape, rescrape_after=rescrape_after_iso
        )

        return True, first_scrape

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def main():
    parser = argparse.ArgumentParser(description="reddit2md v3.0: Granular Reddit-to-Markdown Scraper")
    parser.add_argument("--debug", type=str2bool, nargs='?', const=True, default=None, help="Enable/disable debug mode (local data output).")
    parser.add_argument("--config", default="config.yml", help="Path to config file.")
    parser.add_argument("--source", help="Run an ad-hoc call for a specific source (even if not in config).")
    
    parser.add_argument("--max-results", type=int, help="Override results limit.")
    parser.add_argument("--offset", type=int, help="Skip the first N results from the feed.")
    parser.add_argument("--min-score", type=int, help="Override min score.")
    parser.add_argument("--detail", choices=['XS', 'SM', 'MD', 'LG', 'XL'], help="Override comment detail.")
    parser.add_argument("--verbose", type=int, choices=[0, 1, 2], help="Verbosity level (0: errors, 1: warnings, 2: all/debug).")
    parser.add_argument("--sort", choices=['new', 'hot', 'top', 'rising'], help="Override Reddit sorting.")
    parser.add_argument("--min-age-hours", type=int, help="Minimum age of a post to scrape.")
    parser.add_argument("--rescrape-threshold-hours", type=int, help="Override min post age hours for re-scrape maturity.")
    parser.add_argument("--max-age-hours", type=int, help="Maximum age of a post to scrape.")
    parser.add_argument("--blacklist-terms", help="Comma-separated keywords to filter from titles.")
    parser.add_argument("--blacklist-urls", help="Comma-separated URL fragments to ignore in story links.")
    
    parser.add_argument("--data-dir", help="Consolidated directory for database and JSON archives.")
    parser.add_argument("--output-dir", help="Directory where Markdown files are saved.")
    parser.add_argument("--log-path", help="Path to the Scrape Log markdown file.")
    parser.add_argument("--group-by-source", type=str2bool, help="Whether to generate source-specific folders.")
    
    parser.add_argument("--save-json", type=str2bool, help="Whether to save the sanitized JSON file.")
    parser.add_argument("--enable-md-log", type=str2bool, help="Whether to update the scrape log.")
    parser.add_argument("--db-limit", type=int, help="Maximum number of records to keep in the DB cache.")
    
    args = parser.parse_args()

    overrides = {
        'max_results': args.max_results,
        'offset': args.offset,
        'min_score': args.min_score,
        'detail': args.detail,
        'verbose': args.verbose,
        'sort': args.sort,
        'min_age_hours': args.min_age_hours,
        'rescrape_threshold_hours': args.rescrape_threshold_hours,
        'max_age_hours': args.max_age_hours,
        'data_output_directory': args.data_dir,
        'md_output_directory': args.output_dir,
        'md_log': args.log_path,
        'group_by_source': args.group_by_source,
        'save_json': args.save_json,
        'enable_md_log': args.enable_md_log,
        'db_limit': args.db_limit
    }
    
    if args.blacklist_terms:
        overrides['blacklist_terms'] = [kw.strip() for kw in args.blacklist_terms.split(',')]
    if args.blacklist_urls:
        overrides['blacklist_urls'] = [bl.strip() for bl in args.blacklist_urls.split(',')]

    scraper = RedditScraper(config_path=args.config, debug=args.debug, overrides=overrides)
    scraper.run(source=args.source, overrides=overrides)


if __name__ == "__main__":
    main()
