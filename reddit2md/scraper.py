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
from .core.url_builder import URLBuilder

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
        self.url_builder = URLBuilder()
        
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
        processor = PostProcessor(self.db_manager, self.settings.get('ignore_urls', []))
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

    def run(self, source=None, routine_name=None, overrides=None):
        self.validate_state()
        
        if routine_name:
            routines = [c for c in self.config_manager.get_all_routine_configs()
                       if (c.get('name') or '').lower() == routine_name.lower()]
            if not routines:
                print(f"No routine named '{routine_name}' found in config.")
                return
        elif source:
            # Targeted ad-hoc routine
            routine_conf = self.config_manager.get_adhoc_routine_config(source)
            routines = [routine_conf]
        else:
            # Process all routines defined in config
            routines = self.config_manager.get_all_routine_configs()

        new_posts_total: int = 0
        updated_posts_total: int = 0
        
        # Track if any routine wants to update the log, and which log to update
        final_log_path = self.md_log
        any_log_update = False

        for routine_config in routines:
            if not routine_config: continue
            if overrides:
                routine_config.update({k: v for k, v in overrides.items() if v is not None})
            
            # Behavioral check: log path can be overridden per routine
            if not self.debug and 'md_log' in routine_config:
                final_log_path = routine_config['md_log']
            
            if routine_config.get('enable_md_log', True):
                any_log_update = True

            new_count, updated_count = self.execute_routine(routine_config)
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
                
                processor = PostProcessor(self.db_manager, post_config.get('ignore_urls', []), post_config.get('detail', 'MD'))
                post_url = f"https://www.reddit.com{db_post['subreddit'] if db_post['subreddit'].startswith('/r/') else '/r/'+db_post['subreddit']}/comments/{db_post['id']}"
                post_timestamp = datetime.fromisoformat(db_post['post_timestamp'])
                
                success, is_new = self._process_single_post(db_post['id'], post_url, post_timestamp, db_post, post_config, processor)
                if success and not is_new:
                    updated_posts_total = updated_posts_total + 1

        if any_log_update:
            self.db_manager.export_to_markdown_log(final_log_path)
            
        # Global DB pruning check (respecting the highest db_limit in the current routine list)
        db_limit = 1000
        for config in routines:
            db_limit = max(db_limit, config.get('db_limit', 1000))
        self.db_manager.prune_old_records(db_limit)

        if self.settings.get("verbose", 2) >= 1:
            print(f"\nFinished run. Total New: {new_posts_total}, Total Updated: {updated_posts_total}")

    def execute_routine(self, config):
        source = config.get('source', None)
        sort = config.get('sort', 'new')
        limit = config.get('max_results', 10)
        offset = config.get('offset', 0)

        # Build the RSS URL using URLBuilder — this replaces the old one-liner.
        # All advanced query parameters are passed in; URLBuilder decides
        # whether to use a simple browse URL or the search endpoint.
        rss_url = self.url_builder.build_rss_url(
            source=source,
            sort=sort,
            timeframe=config.get('timeframe'),
            post_type=config.get('post_type'),
            allow_nsfw=config.get('allow_nsfw', False),
            label=config.get('label'),
            label_exact=config.get('label_exact'),
            exclude_label=config.get('exclude_label', []),
            exclude_terms=config.get('exclude_terms', []),
            exclude_urls=config.get('exclude_urls', []),
            exclude_author=config.get('exclude_author', []),
            author=config.get('author', []),
            domain=config.get('domain', []),
            selftext=config.get('selftext', []),
            title_search=config.get('title_search', []),
            nsfw_only=config.get('nsfw_only', False),
            spoiler=config.get('spoiler', False),
            search=config.get('search'),
        )

        if config.get("verbose", 2) >= 1:
            r_name = config.get('name')
            display_title = f"{r_name} ({source})" if r_name else (source or 'global')
            print(f"\nExecuting Routine: {display_title} (Sort: {sort}, Limit: {limit}, Offset: {offset})")
        if config.get("verbose", 2) >= 2:
            print(f"  RSS URL: {rss_url}")

        processor = PostProcessor(self.db_manager, config.get('ignore_urls', []), config.get('detail', 'MD'))
        
        new_count: int = 0
        updated_count: int = 0
        accepted_count: int = 0
        
        # Hard cap the deep pagination to prevent abuse/infinite loops
        max_pages: int = 3 
        current_page: int = 0
        current_rss_url: str = str(rss_url)

        while current_page < max_pages and accepted_count < limit:
            if config.get("verbose", 2) >= 2 and current_page > 0:
                print(f"  Paginating (Page {current_page + 1}): {current_rss_url}")
                
            posts = self.client.get_posts_from_rss(current_rss_url, fetch_cap=100, offset=offset if current_page == 0 else 0)
            
            if not posts:
                break
                
            for post_id, post_url, post_date in posts:
                db_post = self.db_manager.get_post(post_id)
                success, is_new = self._process_single_post(post_id, post_url, post_date, db_post, config, processor)
                if success:
                    accepted_count += 1
                    if is_new: new_count += 1
                    else: updated_count += 1
                    
                if accepted_count >= limit:
                    if config.get("verbose", 2) >= 1:
                        print(f"  Reached max_results limit ({limit}). Stopping routine sequence.")
                    break
                    
            if accepted_count >= limit:
                break
                
            # If the current page returned fewer than 25 items, we have exhausted the actual feed on Reddit's side.
            if len(posts) < 25:
                if config.get("verbose", 2) >= 2:
                    print("  Feed returned fewer than 25 items. Exhausted source, stopping pagination.")
                break
                
            # Prepare for the next page
            last_post_id = posts[-1][0]
            if "?" in rss_url:
                current_rss_url = f"{rss_url}&after=t3_{last_post_id}"
            else:
                current_rss_url = f"{rss_url}?after=t3_{last_post_id}"
                
            current_page += 1

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
        if not raw_post_data or not isinstance(raw_post_data, list): return False, False

        post_item = raw_post_data[0].get('data', {}).get('children', [{}])[0].get('data', {})
        score = post_item.get('score', 0)
        title = post_item.get('title', '')
        source = post_item.get('subreddit', config.get('source', 'Unknown'))
        
        ignore_below_score = config.get('ignore_below_score', 0)
        if score < ignore_below_score:
            if config.get("verbose", 2) >= 2:
                print(f"  Skipped: Score {score} is below minimum threshold of {ignore_below_score}.")
            self.db_manager.add_or_update_post(post_id, title, None, source, None, score, config.get('sort', 'N/A'), post_date, None, first_scrape=first_scrape, ignored_reason=f"Score below {ignore_below_score}")
            return False, False
            
        upvote_ratio = post_item.get('upvote_ratio', 0.0)
        ignore_below_upvote_ratio = config.get('ignore_below_upvote_ratio')
        if ignore_below_upvote_ratio is not None and upvote_ratio < ignore_below_upvote_ratio:
            if config.get("verbose", 2) >= 2:
                print(f"  Skipped: Upvote ratio {upvote_ratio} is below threshold of {ignore_below_upvote_ratio}.")
            self.db_manager.add_or_update_post(post_id, title, None, source, None, score, config.get('sort', 'N/A'), post_date, None, first_scrape=first_scrape, ignored_reason=f"Upvote ratio below {ignore_below_upvote_ratio}")
            return False, False

        num_comments = post_item.get('num_comments', 0)
        ignore_below_comments = config.get('ignore_below_comments')
        if ignore_below_comments is not None and num_comments < ignore_below_comments:
            if config.get("verbose", 2) >= 2:
                print(f"  Skipped: Comments {num_comments} is below threshold of {ignore_below_comments}.")
            self.db_manager.add_or_update_post(post_id, title, None, source, None, score, config.get('sort', 'N/A'), post_date, None, first_scrape=first_scrape, ignored_reason=f"Comments below {ignore_below_comments}")
            return False, False
            
        # Local safety net for exclude_terms
        for kw in config.get('exclude_terms', []):
            if kw.lower() in title.lower():
                self.db_manager.add_or_update_post(post_id, title, None, source, None, score, config.get('sort', 'N/A'), post_date, None, first_scrape=first_scrape, ignored_reason=f"Excluded term: {kw}")
                return False, False

        # Additional local time checks
        age = datetime.now(timezone.utc) - post_date

        ignore_older_than_hours = config.get('ignore_older_than_hours')
        if ignore_older_than_hours is not None:
            if age > timedelta(hours=ignore_older_than_hours):
                self.db_manager.add_or_update_post(post_id, title, None, source, None, score, config.get('sort', 'N/A'), post_date, None, first_scrape=first_scrape, ignored_reason=f"Older than {ignore_older_than_hours}h")
                return False, False
                
        ignore_newer_than_hours = config.get('ignore_newer_than_hours')
        if ignore_newer_than_hours is not None:
            if age < timedelta(hours=ignore_newer_than_hours):
                self.db_manager.add_or_update_post(post_id, title, None, source, None, score, config.get('sort', 'N/A'), post_date, None, first_scrape=first_scrape, ignored_reason=f"Newer than {ignore_newer_than_hours}h")
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

        json_path = None
        # JSON Toggle
        if config.get('save_json', True):
            json_path = os.path.join(active_json_dir, f"{post_id}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_post, f, indent=2)

        rescrape_after_iso = None
        rescrape_newer_than_hours = config.get('rescrape_newer_than_hours')
        if rescrape_newer_than_hours is not None and rescrape_newer_than_hours > 0:
            if age < timedelta(hours=rescrape_newer_than_hours):
                rescrape_after = post_date + timedelta(hours=rescrape_newer_than_hours)
                rescrape_after_iso = rescrape_after.isoformat()

        # Cumulative Update Check
        is_update = not first_scrape and db_post and db_post['file_path'] and os.path.exists(db_post['file_path'])
        
        md_path = db_post['file_path'] if db_post else None
        
        # Markdown Toggle
        if config.get('save_md', True):
            if is_update:
                new_frontmatter, update_block, label, source = processor.generate_markdown(cleaned_post, rescrape_after=rescrape_after_iso, is_update=True)
                
                with open(db_post['file_path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Specifically update score and rescraped_date via Regex
                content = re.sub(r'(^score:\s*)\d+', rf'\g<1>{cleaned_post.get("score", 0)}', content, flags=re.MULTILINE)
                
                # Safely delete rescrape_after
                content = re.sub(r'^rescrape_after:.*?$\n', '', content, flags=re.MULTILINE)
                
                # Append rescraped_date before closing frontmatter
                updated_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                content = re.sub(r'^---$', f'rescraped_date: {updated_date}\n---', content, count=1, flags=re.MULTILINE)
                
                # Append the new comments
                updated_content = content + "\n" + update_block
                
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
        else:
            # If MD output is suppressed but JSON is not, we still need basic metadata for DB
            label = cleaned_post.get('post_flair', 'N/A')
            source = cleaned_post.get('source', '')

        # If detailed_db is True, or if JSON saving is disabled (but we're still scraping), 
        # push the rich data to the database
        detailed_data = None
        if config.get('detailed_db', False) or not config.get('save_json', True):
            detailed_data = cleaned_post

        # Database update is now mandatory for system logic
        self.db_manager.add_or_update_post(
            post_id, cleaned_post['title'], cleaned_post['poster'],
            cleaned_post['source'], label, score, config.get('sort', 'N/A'), post_date, md_path,
            first_scrape=first_scrape, rescrape_after=rescrape_after_iso, json_path=json_path, ignored_reason=None,
            detailed_data=detailed_data
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
    parser = argparse.ArgumentParser(description="reddit2md v3.1: Advanced Reddit-to-Markdown Scraper")
    parser.add_argument("--debug", type=str2bool, nargs='?', const=True, default=None, help="Enable/disable debug mode (local data output).")
    parser.add_argument("--config", default="config.yml", help="Path to config file.")
    parser.add_argument("--source", help="Run an ad-hoc call for a specific source (even if not in config).")
    parser.add_argument("--routine", help="Run a specific named routine from the config.")
    
    parser.add_argument("--max-results", type=int, help="Override results limit.")
    parser.add_argument("--offset", type=int, help="Skip the first N results from the feed.")
    parser.add_argument("--ignore-below-score", type=int, help="Discard posts below score threshold.")
    parser.add_argument("--min-score", type=int, help="(Alias for ignore-below-score)")
    parser.add_argument("--ignore-below-upvote-ratio", type=float, help="Discard posts below upvote ratio (e.g., 0.90 for 90%%).")
    parser.add_argument("--ignore-below-comments", type=int, help="Discard posts with fewer than N comments.")
    parser.add_argument("--detail", choices=['XS', 'SM', 'MD', 'LG', 'XL'], help="Override comment detail.")
    parser.add_argument("--verbose", type=int, choices=[0, 1, 2], help="Verbosity level (0: errors, 1: warnings, 2: all/debug).")
    parser.add_argument("--sort", choices=['new', 'hot', 'top', 'relevance', 'comments'], help="Override Reddit sorting.")
    
    parser.add_argument("--ignore-older-than-hours", type=int, help="Local only — discard posts too old.")
    parser.add_argument("--ignore-older-than-days", type=int, help="Converted to hours internally.")
    parser.add_argument("--ignore-newer-than-hours", type=int, help="Local only — discard posts too fresh.")
    parser.add_argument("--ignore-newer-than-days", type=int, help="Converted to hours internally.")
    parser.add_argument("--rescrape-newer-than-hours", type=int, help="Scrape now, mark for return visit.")
    parser.add_argument("--rescrape-newer-than-days", type=int, help="Converted to hours internally.")
    
    parser.add_argument("--exclude-terms", help="Comma-separated keywords to filter from titles.")
    parser.add_argument("--exclude-urls", help="Comma-separated domains to exclude.")
    parser.add_argument("--exclude-author", help="Comma-separated authors to exclude.")
    parser.add_argument("--ignore-urls", help="Comma-separated URL fragments to strip from output.")
    
    parser.add_argument("--data-dir", help="Consolidated directory for database and JSON archives.")
    parser.add_argument("--output-dir", help="Directory where Markdown files are saved.")
    parser.add_argument("--log-path", help="Path to the Scrape Log markdown file.")
    parser.add_argument("--group-by-source", type=str2bool, help="Whether to generate source-specific folders.")
    
    parser.add_argument("--save-md", type=str2bool, help="Whether to save the Markdown file.")
    parser.add_argument("--save-json", type=str2bool, help="Whether to save the sanitized JSON file.")
    parser.add_argument("--detailed-db", type=str2bool, help="Force SQLite to catch all JSON properties.")
    parser.add_argument("--enable-md-log", type=str2bool, help="Whether to update the scrape log.")
    parser.add_argument("--db-limit", type=int, help="Maximum number of records to keep in the DB cache.")

    # --- Advanced Query Parameters (new in v3.1) ---
    parser.add_argument("--search", help="Freeform Lucene search string.")
    parser.add_argument("--query", help="(Alias for search)")
    parser.add_argument("--label", help="Filter by flair (partial match).")
    parser.add_argument("--flair", help="(Alias for label)")
    parser.add_argument("--label-exact", help="Exact flair filter (browse-safe when sort=new).")
    parser.add_argument("--exclude-label", help="Exclude by flair (NOT flair: in q=).")
    parser.add_argument("--exclude-flair", help="(Alias for exclude-label)")
    parser.add_argument("--timeframe", choices=['hour', 'day', 'week', 'month', 'year', 'all'], help="URL-level time window.")
    parser.add_argument("--post-type", choices=['link', 'self'], help="Filter by post format: 'link' (images/URLs) or 'self' (text posts only).")
    parser.add_argument("--nsfw-only", type=str2bool, help="Restricts feed to ONLY NSFW-marked posts.")
    parser.add_argument("--spoiler", type=str2bool, help="Restricts feed to ONLY spoiler-marked posts.")
    
    parser.add_argument("--author", help="Comma-separated authors to require in feed.")
    parser.add_argument("--domain", help="Comma-separated domains to require in feed (e.g., youtube.com).")
    parser.add_argument("--selftext", help="Comma-separated keywords to search for within post body.")
    parser.add_argument("--title-search", help="Comma-separated keywords to search for within post title.")
    
    args = parser.parse_args()

    overrides = {
        'max_results': args.max_results,
        'offset': args.offset,
        'ignore_below_score': args.ignore_below_score or args.min_score,
        'detail': args.detail,
        'verbose': args.verbose,
        'sort': args.sort,
        'ignore_older_than_hours': args.ignore_older_than_hours,
        'ignore_older_than_days': args.ignore_older_than_days,
        'ignore_newer_than_hours': args.ignore_newer_than_hours,
        'ignore_newer_than_days': args.ignore_newer_than_days,
        'rescrape_newer_than_hours': args.rescrape_newer_than_hours,
        'rescrape_newer_than_days': args.rescrape_newer_than_days,
        'data_output_directory': args.data_dir,
        'md_output_directory': args.output_dir,
        'md_log': args.log_path,
        'group_by_source': args.group_by_source,
        'save_md': args.save_md,
        'save_json': args.save_json,
        'detailed_db': args.detailed_db,
        'enable_md_log': args.enable_md_log,
        'db_limit': args.db_limit,
        'search': args.search or args.query,
        'label_exact': args.label_exact,
        'timeframe': args.timeframe,
        'post_type': args.post_type,
        'allow_nsfw': args.allow_nsfw,
        'ignore_below_upvote_ratio': args.ignore_below_upvote_ratio,
        'ignore_below_comments': args.ignore_below_comments,
        'nsfw_only': args.nsfw_only,
        'spoiler': args.spoiler,
    }
    
    list_args = {
        'exclude_terms': args.exclude_terms,
        'exclude_urls': args.exclude_urls,
        'exclude_author': args.exclude_author,
        'ignore_urls': args.ignore_urls,
        'label': args.label or args.flair,
        'exclude_label': args.exclude_label or args.exclude_flair,
        'author': args.author,
        'domain': args.domain,
        'selftext': args.selftext,
        'title_search': args.title_search,
    }
    for k, v in list_args.items():
        if v:
            overrides[k] = [item.strip() for item in v.split(',')]

    scraper = RedditScraper(config_path=args.config, debug=args.debug, overrides=overrides)
    scraper.run(source=args.source, routine_name=args.routine, overrides=overrides)


if __name__ == "__main__":
    main()
