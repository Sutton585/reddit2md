import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    author TEXT,
                    source TEXT,
                    label TEXT,
                    score INTEGER,
                    sort_method TEXT,
                    post_timestamp DATETIME,
                    first_scrape_timestamp DATETIME,
                    last_scrape_timestamp DATETIME,
                    rescrape_after DATETIME,
                    file_path TEXT
                )
            ''')
            # Schema Migration & Verification
            cursor.execute("PRAGMA table_info(posts)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'project' in columns and 'label' not in columns:
                cursor.execute("ALTER TABLE posts RENAME COLUMN project TO label")
            
            if 'subreddit' in columns and 'source' not in columns:
                cursor.execute("ALTER TABLE posts RENAME COLUMN subreddit TO source")
            
            if 'score' not in columns:
                cursor.execute("ALTER TABLE posts ADD COLUMN score INTEGER")
            if 'sort_method' not in columns:
                cursor.execute("ALTER TABLE posts ADD COLUMN sort_method TEXT")
            conn.commit()

    def post_exists(self, post_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM posts WHERE id = ?', (post_id,))
            return cursor.fetchone() is not None

    def get_post(self, post_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
            return cursor.fetchone()

    def add_or_update_post(self, post_id, title, author, source, label, score, sort_method, post_timestamp, file_path, first_scrape=True, rescrape_after=None):
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if first_scrape:
                cursor.execute('''
                    INSERT INTO posts (id, title, author, source, label, score, sort_method, post_timestamp, first_scrape_timestamp, last_scrape_timestamp, rescrape_after, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        title=excluded.title,
                        author=excluded.author,
                        source=excluded.source,
                        label=excluded.label,
                        score=excluded.score,
                        sort_method=excluded.sort_method,
                        post_timestamp=excluded.post_timestamp,
                        last_scrape_timestamp=excluded.last_scrape_timestamp,
                        rescrape_after=excluded.rescrape_after,
                        file_path=excluded.file_path
                ''', (post_id, title, author, source, label, score, sort_method, post_timestamp, now, now, rescrape_after, file_path))
            else:
                cursor.execute('''
                    UPDATE posts SET
                        title = ?, author = ?, source = ?, label = ?, score = ?, sort_method = ?, post_timestamp = ?,
                        last_scrape_timestamp = ?, rescrape_after = ?, file_path = ?
                    WHERE id = ?
                ''', (title, author, source, label, score, sort_method, post_timestamp, now, rescrape_after, file_path, post_id))
            conn.commit()

    def get_all_posts(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM posts ORDER BY last_scrape_timestamp DESC')
            return cursor.fetchall()

    def get_processed_ids(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM posts')
            return {row[0] for row in cursor.fetchall()}

    def get_maturing_posts(self):
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM posts WHERE rescrape_after IS NOT NULL AND rescrape_after < ?', (now.isoformat(),))
            return cursor.fetchall()

    def delete_post(self, post_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
            conn.commit()

    def prune_old_records(self, max_records):
        """Removes the oldest records from the database only (does not touch files)."""
        if max_records <= 0: return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM posts')
            count = cursor.fetchone()[0]
            
            if count > max_records:
                to_delete = count - max_records
                if getattr(self, "verbose", 2) >= 2:
                    print(f"Pruning {to_delete} oldest records from database cache...")
                # Delete oldest based on last_scrape_timestamp
                cursor.execute('''
                    DELETE FROM posts WHERE id IN (
                        SELECT id FROM posts ORDER BY last_scrape_timestamp ASC LIMIT ?
                    )
                ''', (to_delete,))
                conn.commit()

    def export_to_markdown_log(self, log_path):
        posts = self.get_all_posts()
        header = "| Status | Label | Title | Score | Sort | Post Date | Last Scrape | Re-scrape After |\n| :| :| :| :| :| :| :| :|\n"
        rows = []
        for p in posts:
            # Determine status icon
            rescrape = p['rescrape_after']
            status = "✅"
            rescrape_display = "-"
            
            if rescrape:
                rescrape_dt = datetime.fromisoformat(rescrape)
                if datetime.now(rescrape_dt.tzinfo) < rescrape_dt:
                    status = "⏳ *Maturing*"
                    rescrape_display = rescrape_dt.strftime("%Y-%m-%d %H:%M")
                else:
                    status = "🔄 *Pending*"
                    rescrape_display = "**Ready Now**"

            # Filename logic: [Source]_[ID].md
            source_clean = p['source'][2:] if p['source'].startswith('r/') else p['source']
            filename = f"{source_clean}_{p['id']}.md"
            title_link = f"[[{filename}|{p['title']}]]" if p['file_path'] else p['title']
            
            post_date = datetime.fromisoformat(p['post_timestamp']).strftime("%Y-%m-%d %H:%M") if p['post_timestamp'] else "N/A"
            last_scrape = datetime.fromisoformat(p['last_scrape_timestamp']).strftime("%Y-%m-%d %H:%M") if p['last_scrape_timestamp'] else "N/A"
            score = p['score'] if 'score' in p.keys() else '-'
            sort_method = p['sort_method'] if 'sort_method' in p.keys() else '-'
            
            rows.append(f"| {status} | {p['label']} | {title_link} | {score} | {sort_method} | {post_date} | {last_scrape} | {rescrape_display} |")
        
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("# 🕵️ Reddit Scrape Dashboard\n\n" + header + "\n".join(rows))

    def migrate_from_markdown(self, log_path):
        if not os.path.exists(log_path):
            return 0
        
        imported_count = 0
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.startswith('|') or '|--' in line or 'Post ID' in line:
                    continue
                parts = [p.strip() for p in line.split('|')]
                if len(parts) > 3:
                    scrape_date_str = parts[1]
                    post_id = parts[2]
                    label = parts[3]
                    
                    if post_id and not self.post_exists(post_id):
                        try:
                            scrape_date = datetime.strptime(scrape_date_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            scrape_date = datetime.now()
                            
                        with sqlite3.connect(self.db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO posts (id, label, first_scrape_timestamp, last_scrape_timestamp)
                                VALUES (?, ?, ?, ?)
                            ''', (post_id, label, scrape_date, scrape_date))
                            conn.commit()
                        imported_count += 1
        return imported_count
