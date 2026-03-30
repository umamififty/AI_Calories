import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

class FoodDatabase:
    def __init__(self, db_path: str = "data/nutrition.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()
        self._migrate_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS food (
                    name TEXT PRIMARY KEY,
                    calories REAL,
                    protein REAL,
                    fat REAL,
                    carbs REAL,
                    sugar REAL DEFAULT 0,
                    fiber REAL DEFAULT 0,
                    sodium REAL DEFAULT 0,
                    source TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS consumption_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    food_name TEXT,
                    calories REAL,
                    protein REAL,
                    fat REAL,
                    carbs REAL,
                    sugar REAL DEFAULT 0,
                    fiber REAL DEFAULT 0,
                    sodium REAL DEFAULT 0,
                    logged_at TEXT
                )
            ''')
            conn.commit()

    def _migrate_db(self):
        """Safely add new columns to existing databases."""
        new_food_cols = [
            ("sugar", "REAL DEFAULT 0"),
            ("fiber", "REAL DEFAULT 0"),
            ("sodium", "REAL DEFAULT 0"),
        ]
        new_log_cols = [
            ("sugar", "REAL DEFAULT 0"),
            ("fiber", "REAL DEFAULT 0"),
            ("sodium", "REAL DEFAULT 0"),
            ("logged_at", "TEXT"),
        ]
        with self._get_conn() as conn:
            cursor = conn.cursor()
            for col, typedef in new_food_cols:
                try:
                    cursor.execute(f"ALTER TABLE food ADD COLUMN {col} {typedef}")
                except Exception:
                    pass
            for col, typedef in new_log_cols:
                try:
                    cursor.execute(f"ALTER TABLE consumption_log ADD COLUMN {col} {typedef}")
                except Exception:
                    pass
            conn.commit()

    def get_food(self, food_name: str) -> Optional[Dict[str, Any]]:
        if not food_name:
            return None
        key = food_name.strip()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM food WHERE LOWER(name) = LOWER(?)", (key,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def fuzzy_search(self, query: str) -> Optional[Dict[str, Any]]:
        query = query.strip()
        if len(query) < 3:
            return None
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM food WHERE name LIKE ? ORDER BY length(name) ASC LIMIT 1",
                (f"%{query}%",)
            )
            row = cursor.fetchone()
            if row:
                match = dict(row)
                # Reject if the query covers less than 50% of the matched name length.
                # Prevents false positives like "fried chicken" matching
                # "sukiya minty fried chicken curry (mini)".
                if len(query) / max(len(match["name"]), 1) >= 0.5:
                    return match
            return None

    def find_candidates(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        query = query.strip()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM food WHERE name LIKE ? ORDER BY length(name) ASC LIMIT ?",
                (f"%{query}%", limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def add_food(self, food_data: Dict[str, Any]):
        if not food_data.get('name'):
            return
        name = food_data['name'].lower().strip()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO food (name, calories, protein, fat, carbs, sugar, fiber, sodium, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name,
                float(food_data.get('calories', 0)),
                float(food_data.get('protein', 0)),
                float(food_data.get('fat', 0)),
                float(food_data.get('carbs', 0)),
                float(food_data.get('sugar', 0)),
                float(food_data.get('fiber', 0)),
                float(food_data.get('sodium', 0)),
                food_data.get('source', 'manual')
            ))
            conn.commit()

    def log_consumption(self, date_str: str, food_data: Dict[str, Any]):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO consumption_log
                    (date, food_name, calories, protein, fat, carbs, sugar, fiber, sodium, logged_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date_str,
                food_data.get('name', 'Unknown'),
                float(food_data.get('calories', 0)),
                float(food_data.get('protein', 0)),
                float(food_data.get('fat', 0)),
                float(food_data.get('carbs', 0)),
                float(food_data.get('sugar', 0)),
                float(food_data.get('fiber', 0)),
                float(food_data.get('sodium', 0)),
                datetime.now().isoformat()
            ))
            conn.commit()

    def get_daily_log(self, date_str: str) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM consumption_log WHERE date = ?", (date_str,))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item['name'] = item['food_name']
                results.append(item)
            return results

    def get_last_meal_time(self, date_str: str) -> Optional[datetime]:
        """Returns the datetime of the most recently logged meal for the given date."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(logged_at) FROM consumption_log WHERE date = ?",
                (date_str,)
            )
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    return datetime.fromisoformat(row[0])
                except Exception:
                    return None
            return None

    def get_all_logs(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Returns all consumption_log entries between start_date and end_date (inclusive)."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM consumption_log WHERE date >= ? AND date <= ? ORDER BY date, logged_at",
                (start_date, end_date)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
