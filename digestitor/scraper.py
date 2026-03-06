import os
import sys
import argparse
import json
from datetime import datetime, timedelta, timezone
from .core.database import DatabaseManager
from .core.reddit_client import RedditClient
from .core.processor import PostProcessor
from .core.config import Config

class RedditScraper:
    def __init__(self, config_path="config.json", debug=None):
        self.config_manager = Config(config_path)
        self.global_defaults = self.config_manager.get_global_defaults()
        
        # Priority: CLI argument > Config file > Default False
        config_debug = self.global_defaults.get('debug', False)
        if isinstance(config_debug, str):
            config_debug = config_debug.lower() == 'true'
        self.debug = debug if debug is not None else config_debug
        
        self.client = RedditClient()
        
        # Unified Data Directory management
        if self.debug:
            self.data_dir = 'data'
            self.output_dir = os.path.join(self.data_dir, "markdown")
            self.scrape_log_path = os.path.join(self.data_dir, "Scrape Log.md")
        else:
            self.data_dir = self.global_defaults.get('data_directory', 'data')
            self.output_dir = self.global_defaults.get('output_directory', 'data/markdown')
            self.scrape_log_path = self.global_defaults.get('scrape_log_path', 'data/Scrape Log.md')

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
        print(">>> Rebuilding database from individual Markdown files...")
        processor = PostProcessor(self.db_manager, self.global_defaults['url_blacklist'])
        rebuilt_count = 0
        
        for root, dirs, files in os.walk(output_dir):
            for filename in files:
                if not filename.endswith(".md") or filename == "Scrape Log.md":
                    continue
                    
                file_path = os.path.join(root, filename)
                frontmatter = processor.parse_frontmatter(file_path)
            
                if frontmatter and 'post_id' in frontmatter:
                    post_id = frontmatter['post_id']
                    if self.db_manager.post_exists(post_id):
                        continue
                        
                    project = frontmatter.get('project', 'N/A')
                    author = frontmatter.get('author', 'N/A')
                    subreddit = frontmatter.get('subreddit', 'N/A')
                    score_str = frontmatter.get('score', '0')
                    score = int(score_str) if score_str.isdigit() else 0
                    post_date_str = frontmatter.get('post_date')
                    rescrape_after = frontmatter.get('rescrape_after')
                    title = filename.replace(f"_{post_id}.md", "")
                    
                    try:
                        post_date = datetime.strptime(post_date_str, "%Y-%m-%d") if post_date_str else datetime.now()
                    except:
                        post_date = datetime.now()
                    
                    json_path = os.path.join(self.json_dir, f"{post_id}.json")
                    if os.path.exists(json_path):
                        self.db_manager.add_or_update_post(
                            post_id, title, author, subreddit, project, score, "rebuilt",
                            post_date, file_path, first_scrape=True, rescrape_after=rescrape_after
                        )
                        rebuilt_count += 1
        
        if rebuilt_count > 0:
            print(f"  Successfully rebuilt {rebuilt_count} records from Markdown files.")

    def validate_state(self):
        print(">>> Validating local state (Files vs. Database Authority)...")
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
            print(f"  Resolved {orphans_count} state conflicts.")
        else:
            print("  State is healthy.")

    def run(self, source_name=None, overrides=None):
        self.validate_state()
        
        if source_name:
            source_conf = self.config_manager.get_source_config(source_name)
            sources = [source_conf]
        else:
            sources = self.config_manager.get_all_source_configs()

        new_posts_total = 0
        updated_posts_total = 0
        
        # Track if any source wants to update the log, and which log to update
        final_log_path = self.scrape_log_path
        any_log_update = False

        for source_config in sources:
            if not source_config: continue
            if overrides:
                source_config.update({k: v for k, v in overrides.items() if v is not None})
            
            # Behavioral check: log path can be overridden per source
            if not self.debug and 'scrape_log_path' in source_config:
                final_log_path = source_config['scrape_log_path']
            
            if source_config.get('update_log', True):
                any_log_update = True

            new_count, updated_count = self.scrape_source(source_config)
            new_posts_total += new_count
            updated_posts_total += updated_count

        print("\n>>> Checking for maturing posts in database...")
        maturing_posts = self.db_manager.get_maturing_posts()
        if maturing_posts:
            if source_name:
                maturing_posts = [p for p in maturing_posts if p['subreddit'].endswith(source_name)]
            
            for db_post in maturing_posts:
                sub = db_post['subreddit']
                if sub.startswith('r/'): sub = sub[2:]
                post_config = self.config_manager.get_source_config(sub)
                if not post_config:
                    post_config = self.global_defaults.copy()
                if overrides:
                    post_config.update({k: v for k, v in overrides.items() if v is not None})
                
                processor = PostProcessor(self.db_manager, post_config.get('url_blacklist', []), post_config.get('comment_detail', 'MD'))
                post_url = f"https://www.reddit.com{db_post['subreddit'] if db_post['subreddit'].startswith('/r/') else '/r/'+db_post['subreddit']}/comments/{db_post['id']}"
                post_timestamp = datetime.fromisoformat(db_post['post_timestamp'])
                
                success, is_new = self._process_single_post(db_post['id'], post_url, post_timestamp, db_post, post_config, processor)
                if success and not is_new:
                    updated_posts_total += 1

        if any_log_update:
            self.db_manager.export_to_markdown_log(final_log_path)
            
        print(f"\nFinished run. Total New: {new_posts_total}, Total Updated: {updated_posts_total}")

    def scrape_source(self, config):
        source_name = config.get('name', 'Unknown')
        sort = config.get('sort', 'new')
        limit = config.get('post_limit', 8)
        
        rss_url = f"https://www.reddit.com/r/{source_name}/{sort}/.rss"
        print(f"\n>>> Processing Source: {source_name} (Sort: {sort}, Limit: {limit})")
        
        processor = PostProcessor(self.db_manager, config.get('url_blacklist', []), config.get('comment_detail', 'MD'))
        posts = self.client.get_posts_from_rss(rss_url, limit)
        
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
                user_project = frontmatter.get('project')
                user_rescrape = frontmatter.get('rescrape_after')
                db_update_needed = False
                current_project = db_post['project']
                current_rescrape = db_post['rescrape_after']
                
                if user_project and user_project != current_project:
                    current_project = user_project
                    db_update_needed = True
                
                if current_rescrape and not user_rescrape:
                    current_rescrape = None
                    db_update_needed = True
                    should_scrape = False
                
                if db_update_needed:
                    new_file_path = db_post['file_path']
                    if user_project and user_project != db_post['project']:
                        new_filename = f"{user_project}_{post_id}.md"
                        new_file_path = os.path.join(os.path.dirname(db_post['file_path']), new_filename)
                        try:
                            os.rename(db_post['file_path'], new_file_path)
                        except:
                            new_file_path = db_post['file_path']
                    
                    self.db_manager.add_or_update_post(
                        post_id, db_post['title'], db_post['author'], db_post['subreddit'],
                        current_project, db_post['score'], db_post['sort_method'],
                        db_post['post_timestamp'], new_file_path,
                        first_scrape=False, rescrape_after=current_rescrape
                    )
        
        if not should_scrape:
            return False, False

        print(f"  Scraping: {post_id}")
        raw_post_data = self.client.fetch_json_from_url(f"{post_url}.json?limit=1000")
        if not raw_post_data: return False, False

        post_item = raw_post_data[0]['data']['children'][0]['data']
        score = post_item.get('score', 0)
        
        if score < config.get('min_score', 0):
            return False, False
            
        title = post_item.get('title', '')
        if any(kw.lower() in title.lower() for kw in config.get('filter_keywords', [])):
            return False, False

        cleaned_post = processor.clean_json(raw_post_data, post_date)
        
        # Dynamic Output Management
        active_output_dir = self.output_dir
        if not self.debug and 'output_directory' in config:
            active_output_dir = config['output_directory']
            
        active_json_dir = self.json_dir
        if not self.debug and 'data_directory' in config:
            active_json_dir = os.path.join(config['data_directory'], "json")

        os.makedirs(active_output_dir, exist_ok=True)
        os.makedirs(active_json_dir, exist_ok=True)

        # JSON Toggle
        if config.get('save_json', True):
            json_path = os.path.join(active_json_dir, f"{post_id}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_post, f, indent=2)

        rescrape_after_iso = None
        min_age_hours = config.get('min_post_age_hours', 12)
        if min_age_hours > 0:
            age = datetime.now(timezone.utc) - post_date
            if age < timedelta(hours=min_age_hours):
                rescrape_after = post_date + timedelta(hours=min_age_hours)
                rescrape_after_iso = rescrape_after.isoformat()

        markdown_content, project = processor.generate_markdown(cleaned_post, rescrape_after=rescrape_after_iso)
        
        # Organize into subreddits/folders
        subreddit_name = cleaned_post['subreddit']
        if subreddit_name.startswith('r/'):
            subreddit_name = subreddit_name[2:]
            
        subreddit_dir = os.path.join(active_output_dir, subreddit_name)
        os.makedirs(subreddit_dir, exist_ok=True)
        
        md_filename = f"{project}_{post_id}.md"
        md_path = os.path.join(subreddit_dir, md_filename)
        
        # Ensure the directory for the markdown file exists (in case project has slashes or is N/A)
        os.makedirs(os.path.dirname(md_path), exist_ok=True)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        # Database Toggle
        if config.get('update_db', True):
            self.db_manager.add_or_update_post(
                post_id, cleaned_post['title'], cleaned_post['author'],
                cleaned_post['subreddit'], project, score, config.get('sort', 'N/A'), post_date, md_path,
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
    parser = argparse.ArgumentParser(description="Digestitor v3.0: Granular Reddit-to-Markdown Scraper")
    parser.add_argument("--debug", type=str2bool, nargs='?', const=True, default=None, help="Enable/disable debug mode (local data output).")
    parser.add_argument("--config", default="config.json", help="Path to config file.")
    parser.add_argument("--source", help="Run only a specific source (even if not in config).")
    
    parser.add_argument("--limit", type=int, help="Override post limit.")
    parser.add_argument("--min-score", type=int, help="Override min score.")
    parser.add_argument("--detail", choices=['XS', 'SM', 'MD', 'LG', 'XL'], help="Override comment detail.")
    parser.add_argument("--sort", choices=['new', 'hot', 'top', 'rising'], help="Override Reddit sorting.")
    parser.add_argument("--age", type=int, help="Override min post age hours for re-scrape.")
    parser.add_argument("--filter", help="Comma-separated keywords to filter from titles.")
    parser.add_argument("--blacklist", help="Comma-separated URL fragments to ignore in story links.")
    
    parser.add_argument("--data-dir", help="Consolidated directory for database and JSON archives.")
    parser.add_argument("--output-dir", help="Directory where Markdown files are saved.")
    parser.add_argument("--log-path", help="Path to the Scrape Log markdown file.")
    
    parser.add_argument("--save-json", type=str2bool, help="Whether to save the raw JSON file.")
    parser.add_argument("--update-log", type=str2bool, help="Whether to update the scrape log.")
    parser.add_argument("--update-db", type=str2bool, help="Whether to update the database.")
    
    args = parser.parse_args()

    overrides = {
        'post_limit': args.limit,
        'min_score': args.min_score,
        'comment_detail': args.detail,
        'sort': args.sort,
        'min_post_age_hours': args.age,
        'data_directory': args.data_dir,
        'output_directory': args.output_dir,
        'scrape_log_path': args.log_path,
        'save_json': args.save_json,
        'update_log': args.update_log,
        'update_db': args.update_db
    }
    
    if args.filter:
        overrides['filter_keywords'] = [kw.strip() for kw in args.filter.split(',')]
    if args.blacklist:
        overrides['url_blacklist'] = [bl.strip() for bl in args.blacklist.split(',')]

    scraper = RedditScraper(config_path=args.config, debug=args.debug)
    scraper.run(source_name=args.source, overrides=overrides)


if __name__ == "__main__":
    main()
