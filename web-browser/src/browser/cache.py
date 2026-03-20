from functools import lru_cache
import threading
import time
import sqlite3
import json

class BrowserCache:
    def __init__(self, cache_size=1000):
        self.cache_size = cache_size
        self.cache_db = 'browser_cache.db'
        self.setup_database()
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_entries, daemon=True)
        self.cleanup_thread.start()

    def setup_database(self):
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    url TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp REAL,
                    expire_time REAL
                )
            ''')

    @lru_cache(maxsize=100)
    def get(self, url):
        with sqlite3.connect(self.cache_db) as conn:
            cursor = conn.execute(
                'SELECT data, expire_time FROM cache WHERE url = ?', 
                (url,)
            )
            result = cursor.fetchone()
            
            if result and result[1] > time.time():
                return json.loads(result[0])
        return None

    def set(self, url, data, expire_in=3600):
        expire_time = time.time() + expire_in
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO cache (url, data, timestamp, expire_time) VALUES (?, ?, ?, ?)',
                (url, json.dumps(data), time.time(), expire_time)
            )

    def _cleanup_old_entries(self):
        while True:
            try:
                with sqlite3.connect(self.cache_db) as conn:
                    conn.execute('DELETE FROM cache WHERE expire_time < ?', (time.time(),))
                    conn.execute(
                        'DELETE FROM cache WHERE rowid NOT IN (SELECT rowid FROM cache ORDER BY timestamp DESC LIMIT ?)',
                        (self.cache_size,)
                    )
            except Exception as e:
                print(f"Cache cleanup error: {e}")
            time.sleep(3600)  # Run cleanup every hour
