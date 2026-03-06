
import json
import re
import os
from datetime import datetime

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

    def __init__(self, db_manager=None, url_blacklist=None, comment_detail='MD'):
        self.db_manager = db_manager
        self.url_blacklist = url_blacklist or []
        self.comment_detail = comment_detail
        self.comment_limits = self.COMMENT_PRESETS.get(comment_detail, self.COMMENT_PRESETS['MD'])

    def clean_json(self, raw_post_data, post_date):
        post_data = raw_post_data[0]['data']['children'][0]['data']
        comments_data = raw_post_data[1]['data']['children']

        cleaned_post = {
            'id': post_data.get('id'),
            'title': post_data.get('title'),
            'author': post_data.get('author'),
            'subreddit': post_data.get('subreddit_name_prefixed'),
            'permalink': post_data.get('permalink'),
            'selftext': post_data.get('selftext', ''),
            'score': post_data.get('score', 0),
            'post_timestamp': post_date.timestamp(),
            'link_flair_text': post_data.get('link_flair_text'),
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
                'author': data.get('author', 'N/A'),
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

    def generate_markdown(self, cleaned_post, rescrape_after=None, is_update=False):
        post_id = cleaned_post['id']
        selftext = cleaned_post['selftext']
        subreddit_name = cleaned_post['subreddit']
        if subreddit_name.startswith('r/'):
            subreddit_name = subreddit_name[2:]
        
        # Resolve internal links in selftext
        selftext = self.resolve_links(selftext)

        # Frontmatter Construction
        flair_text = cleaned_post.get('link_flair_text')
        flair = "N/A"
        post_type = "reddit-thread"
        if flair_text:
            if ':' in flair_text:
                flair = flair_text.split(':', 1)[0].strip()
            else:
                flair = flair_text
            if "Weekly" in flair_text:
                post_type = 'megathread'

        # Post Link Processing (formerly story_link)
        all_urls = []
        if cleaned_post.get('url_overridden_by_dest'):
            all_urls.append(cleaned_post['url_overridden_by_dest'])
        body_urls = re.findall(self.URL_REGEX, cleaned_post['selftext'])
        all_urls.extend(body_urls)
        
        unique_urls = sorted(list(set(all_urls)))
        filtered_urls = [url for url in unique_urls if not any(bl_item in url for bl_item in self.url_blacklist)]
        
        # Resolve internal links in post links
        resolved_post_links = []
        for url in filtered_urls:
            reddit_id_match = re.search(self.REDDIT_PERMALINK_REGEX, url)
            if reddit_id_match and self.db_manager:
                target_post_id = reddit_id_match.group(1)
                target_post = self.db_manager.get_post(target_post_id)
                if target_post:
                    target_sub = target_post['subreddit'][2:] if target_post['subreddit'].startswith('r/') else target_post['subreddit']
                    filename = f"{target_sub}_{target_post_id}"
                    resolved_post_links.append(f"[[{filename}]]")
                    continue
            resolved_post_links.append(url)

        frontmatter = {
            'tags': '[reddit, scraped]',
            'source_url': f"https://reddit.com{cleaned_post['permalink']}",
            'subreddit': cleaned_post['subreddit'],
            'author': cleaned_post['author'],
            'post_date': datetime.fromtimestamp(cleaned_post['post_timestamp']).strftime("%Y-%m-%d"),
            'scrape_date': datetime.now().strftime("%Y-%m-%d"),
            'post_id': post_id,
            'score': cleaned_post['score'],
            'type': post_type,
            'flair': flair,
        }
        
        if rescrape_after:
            frontmatter['rescrape_after'] = rescrape_after
            
        if resolved_post_links:
            frontmatter['post_link'] = ", ".join(resolved_post_links)

        frontmatter_str = "---\n"
        for key, value in frontmatter.items():
            frontmatter_str += f"{key}: {value}\n"
        frontmatter_str += "---\n"

        def format_comments(comments, depth):
            md = ""
            for c in comments:
                indent = '\t' * depth
                body = c['body'].replace('\n', '\n' + '\t' * (depth + 1))
                # Resolve links in comment body
                body = self.resolve_links(body)
                md += f"{indent}- ==**u/{c['author']}** (Score: {c['score']})==\n{indent}\t{body}\n"
                if c['replies']:
                    md += format_comments(c['replies'], depth + 1)
            return md

        comments_md = format_comments(cleaned_post['comments'], 0)

        if is_update:
            # For updates, we return a block that will be appended
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            update_block = f"\n\n---\n## Updated Comments ({timestamp})\n\n{comments_md}"
            return frontmatter_str, update_block, flair, subreddit_name
        else:
            # For initial scrape, return the full file
            markdown_content = f"""{frontmatter_str}# {cleaned_post['title']}

**Post Body:**
{selftext}

---
## Top Comments

{comments_md}"""
            return markdown_content, None, flair, subreddit_name

        # Sanitize flair for filename (not used anymore, but good for safety)
        safe_flair = flair.replace('/', '-')
        return markdown_content, safe_flair
