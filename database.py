import sqlite3
from datetime import datetime
from config import DATABASE_PATH


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            platform TEXT,
            url TEXT,
            title TEXT,
            location TEXT,
            latitude REAL,
            longitude REAL,
            subcategory TEXT,
            price_range TEXT,
            tags TEXT,
            description TEXT,
            hashtags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_place(category, platform, url, title, location, latitude, longitude,
               subcategory=None, price_range=None, tags=None, description=None, hashtags=None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO saved_places (category, platform, url, title, location, latitude, longitude,
                                  subcategory, price_range, tags, description, hashtags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (category, platform, url, title, location, latitude, longitude,
          subcategory, price_range, tags, description, hashtags))
    conn.commit()
    conn.close()


def search_places(keyword):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM saved_places
        WHERE title LIKE ? OR location LIKE ? OR description LIKE ? OR tags LIKE ?
        ORDER BY created_at DESC
    """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%")).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_places_by_category(category):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM saved_places
        WHERE category = ?
        ORDER BY created_at DESC
    """, (category,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_places():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM saved_places ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_place_count():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM saved_places").fetchone()[0]
    conn.close()
    return count


def get_category_count(category):
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM saved_places WHERE category = ?", (category,)).fetchone()[0]
    conn.close()
    return count
