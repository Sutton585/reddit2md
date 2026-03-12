
import json
import re
import os
from datetime import datetime
from .theme_engine import ThemeEngine

class PostProcessor:
    URL_REGEX = r'https?://[^\s)\]]+'
    REDDIT_PERMALINK_REGEX = r'https?://(?:www\.)?reddit\.com/r/[^/]+/comments/([a-z0-9]+)(?:/[^/\s]*)?'
    
    COMMENT_PRESETS = {
        'XS': {0: 3, 1: 0},
        'SM': {0: 5, 1: 1},
        'MD': {0: 8, 1: 2},
        'LG': {0: 10, 1: 3, 2: 1},
        'XL': None # Special handling for "XL"
    }

    def __init__(self, db_manager=None, ignore_urls=None, detail='MD'):
        self.db_manager = db_manager
        self.ignore_urls = ignore_urls or []
        self.detail = detail
        self.comment_limits = self.COMMENT_PRESETS.get(detail, self.COMMENT_PRESETS['MD'])
        
        # Initialize Theme Engine
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        self.theme_engine = ThemeEngine(template_dir)

    def clean_json(self, raw_post_data, post_date):
        post_data = raw_post_data[0]['data']['children'][0]['data']
        comments_data = raw_post_data[1]['data']['children']

        source = post_data.get('subreddit_name_prefixed', '')
        if source.startswith('r/'):
            source = source[2:]

        cleaned_post = {
            'post_id': post_data.get('id'),
            'title': post_data.get('title'),
            'poster': post_data.get('author'),
            'source': source,
            'permalink': post_data.get('permalink'),
            'selftext': post_data.get('selftext', ''),
            'score': post_data.get('score', 0),
            
            # Additional Interaction Metrics
            'upvote_ratio': post_data.get('upvote_ratio', 0.0),
            'num_comments': post_data.get('num_comments', 0),
            
            # Content Metadata
            'domain': post_data.get('domain', ''),
            'is_video': post_data.get('is_video', False),
            'is_gallery': 'is_gallery' in post_data and post_data['is_gallery'],
            'stickied': post_data.get('stickied', False),
            'spoiler': post_data.get('spoiler', False),
            'over_18': post_data.get('over_18', False),

            # Author & Community
            'author_flair': post_data.get('author_flair_text', ''),
            'post_flair': post_data.get('link_flair_text', ''),
            'subreddit_subscribers': post_data.get('subreddit_subscribers', 0),

            # Timestamps
            'created_utc': post_data.get('created_utc', 0.0),
            'scraped_utc': post_date.timestamp(),

            # Internal
            'url_overridden_by_dest': post_data.get('url_overridden_by_dest'),
            'comments': self._process_comments_recursive(comments_data, 0)
        }
        return cleaned_post

    def _process_comments_recursive(self, comments_data, depth):
        if not comments_data: return []
        
        # If we have a limit and we've reached it, return empty
        if self.comment_limits is not None and depth >= len(self.comment_limits):
            return []
        
        valid_comments = []
        for c in comments_data:
            if c.get('kind') == 't1' and c['data'].get('body') not in ('[deleted]', '[removed]') and c['data'].get('author') != '[deleted]' and not c['data'].get('stickied'):
                valid_comments.append(c)
        
        valid_comments.sort(key=lambda c: c['data'].get('score', 0), reverse=True)
        
        # Determine limit for this depth
        limit = None
        if self.comment_limits is not None:
            limit = self.comment_limits.get(depth, 0)
        
        processed = []
        for c in valid_comments[:limit]:
            data = c['data']
            comment_item = {
                'poster': data.get('author', 'N/A'),
                'score': data.get('score', 0),
                'body': data.get('body', ''),
                'replies': []
            }
            if data.get('replies') and isinstance(data['replies'], dict):
                comment_item['replies'] = self._process_comments_recursive(data['replies']['data']['children'], depth + 1)
            processed.append(comment_item)
        return processed

    def parse_frontmatter(self, md_path):
        if not os.path.exists(md_path):
            return None
        
        frontmatter = {}
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Use regex to find frontmatter
                match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
                if match:
                    fm_text = match.group(1)
                    # Parse simple YAML lines
                    for line in fm_text.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            frontmatter[key.strip()] = value.strip()
        except Exception as e:
            print(f"Error parsing frontmatter from {md_path}: {e}")
        
        return frontmatter

    def resolve_links(self, text):
        if not self.db_manager:
            return text
        
        def replace_link(match):
            url = match.group(0)
            reddit_id_match = re.search(self.REDDIT_PERMALINK_REGEX, url)
            if reddit_id_match:
                post_id = reddit_id_match.group(1)
                post = self.db_manager.get_post(post_id)
                if post:
                    # Obsidian internal link format: [Subreddit]_[post_id].md
                    sub_clean = post['subreddit'][2:] if post['subreddit'].startswith('r/') else post['subreddit']
                    filename = f"{sub_clean}_{post_id}"
                    return f"[[{filename}]]"
            return url

        return re.sub(self.URL_REGEX, replace_link, text)

    def _render_comments_recursive(self, comments, depth):
        """Internal helper to render the comments using the comment template."""
        md = ""
        for c in comments:
            indent = '\t' * depth
            body = c['body'].replace('\n', '\n' + '\t' * (depth + 1))
            body = self.resolve_links(body)
            
            replies_md = ""
            if c['replies']:
                replies_md = self._render_comments_recursive(c['replies'], depth + 1)
            
            md += self.theme_engine.render('comment', 
                indent=indent, 
                author=c['poster'], 
                score=c['score'], 
                body=body, 
                replies=replies_md
            )
        return md

    def generate_markdown(self, cleaned_post, rescrape_after=None, is_update=False):
        post_id = cleaned_post['post_id']
        selftext = cleaned_post['selftext']
        source = cleaned_post['source']
        
        # Format dates for template injection
        cleaned_post['date_created'] = datetime.fromtimestamp(cleaned_post['created_utc']).strftime("%Y-%m-%d %H:%M")
        cleaned_post['date_scraped'] = datetime.fromtimestamp(cleaned_post['scraped_utc']).strftime("%Y-%m-%d %H:%M")
        cleaned_post['rescrape_after'] = f"rescrape_after: {rescrape_after}" if rescrape_after else ""
        
        selftext = self.resolve_links(selftext)
        cleaned_post['selftext'] = selftext

        # Label extraction mapping
        flair_text = cleaned_post.get('post_flair')
        label = "N/A"
        if flair_text:
            label = flair_text.split(':', 1)[0].strip() if ':' in flair_text else flair_text

        # Post Link Processing
        all_urls = []
        if cleaned_post.get('url_overridden_by_dest'):
            all_urls.append(cleaned_post['url_overridden_by_dest'])
        all_urls.extend(re.findall(self.URL_REGEX, cleaned_post['selftext']))
        
        unique_urls = sorted(list(set(all_urls)))
        resolved_post_links = []
        for url in unique_urls:
            if any(bl_item in url for bl_item in self.ignore_urls): continue
            reddit_id_match = re.search(self.REDDIT_PERMALINK_REGEX, url)
            if reddit_id_match and self.db_manager:
                target_post_id = reddit_id_match.group(1)
                target_post = self.db_manager.get_post(target_post_id)
                if target_post:
                    target_sub = target_post['source'][2:] if target_post['source'].startswith('r/') else target_post['source']
                    resolved_post_links.append(f"[[{target_sub}_{target_post_id}]]")
                    continue
            resolved_post_links.append(url)

        cleaned_post['post_links'] = f"\npost_links: {', '.join(resolved_post_links)}" if resolved_post_links else ""

        # Prepare Comments
        comments_md = self._render_comments_recursive(cleaned_post['comments'], 0)
        cleaned_post['comment_section'] = comments_md

        if is_update:
            # Generate the update block
            update_block = self.theme_engine.render('update',
                update_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
                comments=comments_md
            )
            # The python logic now natively expects the update block to be appended by the orchestrator
            # We no longer hardcode frontmatter building natively here. 
            return None, update_block, label, source
        else:
            # Generate full note using the expanded payload dict
            cleaned_post['update_section'] = "" # Blank out update macro on new creations
            full_content = self.theme_engine.render('post', **cleaned_post)
            return full_content, None, label, source
