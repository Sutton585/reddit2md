
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    from urllib import request, error
    _REQUESTS_AVAILABLE = False

class RedditClient:
    def __init__(self, verbose=2):
        self.verbose = verbose

    HEADERS = {
        'User-Agent': 'python:sandman.reddit2md:v3.0 (by /u/sutton585)',
        'Accept': 'application/json, text/plain, */*',
    }

    def _fetch_url(self, url):
        """Internal helper to fetch data using requests or urllib."""
        if _REQUESTS_AVAILABLE:
            response = requests.get(url, headers=self.HEADERS, timeout=15)
            response.raise_for_status()
            return response.content
        else:
            req = request.Request(url, headers=self.HEADERS)
            with request.urlopen(req) as response:
                return response.read()

    def get_posts_from_rss(self, rss_url, post_limit_per_feed, offset=0):
        if getattr(self, "verbose", 2) >= 2:
            print(f"Fetching RSS feed: {rss_url}")
        try:
            xml_data = self._fetch_url(rss_url)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            root = ET.fromstring(xml_data)
            posts = []
            
            entries = root.findall('atom:entry', ns)
            
            # Apply offset to skip the first N items
            if offset > 0:
                entries = entries[offset:]

            for i, entry in enumerate(entries):
                if i >= post_limit_per_feed: break
                id_tag, link_tag, updated_tag = entry.find('atom:id', ns), entry.find('atom:link', ns), entry.find('atom:updated', ns)
                if all((id_tag is not None, link_tag is not None, updated_tag is not None)):
                    try:
                        post_date = datetime.fromisoformat(updated_tag.text.replace('Z', '+00:00'))
                        posts.append((id_tag.text.split('_')[-1], link_tag.get('href'), post_date))
                    except ValueError: continue
            return posts
        except Exception as e:
            if not _REQUESTS_AVAILABLE and "403" in str(e):
                print(f"Error: Reddit is blocking standard Python requests (403 Forbidden).", file=sys.stderr)
                print(f"Fix: Run 'pip install requests' to use a more robust fetching method.", file=sys.stderr)
            else:
                print(f"Error fetching or parsing RSS for {rss_url}: {e}", file=sys.stderr)
            return []

    def fetch_json_from_url(self, json_url):
        if getattr(self, "verbose", 2) >= 2:
            print(f"Fetching JSON from: {json_url}")
        try:
            if _REQUESTS_AVAILABLE:
                response = requests.get(json_url, headers=self.HEADERS, timeout=15)
                response.raise_for_status()
                return response.json()
            else:
                data = self._fetch_url(json_url)
                return json.loads(data.decode('utf-8'))
        except Exception as e:
            print(f"Error fetching JSON for {json_url}: {e}", file=sys.stderr)
            return None

