import sqlite3
import os
from typing import Optional, Dict, Any, List

class FoodDatabase:
    def __init__(self, db_path: str = "data/nutrition.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row 
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # We create the table. Note: Changing schema of existing DB is hard in SQLite,
            # so we handle case-insensitivity in the SELECT queries instead.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS food (
                    name TEXT PRIMARY KEY,
                    calories REAL,
                    protein REAL,
                    fat REAL,
                    carbs REAL,
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
                    carbs REAL
                )
            ''')
            conn.commit()

    def get_food(self, food_name: str) -> Optional[Dict[str, Any]]:
        """
        Exact Match Lookup (Case Insensitive).
        """
        if not food_name: return None
        key = food_name.strip() # Don't lower() here, let SQL handle it
        
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # FIX: Use 'LOWER(name) = LOWER(?)' to match regardless of capitalization
            cursor.execute("SELECT * FROM food WHERE LOWER(name) = LOWER(?)", (key,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def fuzzy_search(self, query: str) -> Optional[Dict[str, Any]]:
        """Best single match (limit 1). LIKE is case-insensitive by default."""
        query = query.strip()
        if len(query) < 3: return None
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM food WHERE name LIKE ? ORDER BY length(name) ASC LIMIT 1", (f"%{query}%",))
            row = cursor.fetchone()
            return dict(row) if row else None

    def find_candidates(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Returns a list of potential matches."""
        query = query.strip()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM food WHERE name LIKE ? ORDER BY length(name) ASC LIMIT ?", (f"%{query}%", limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def add_food(self, food_data: Dict[str, Any]):
        if not food_data.get('name'): return
        # We still save as lowercase for consistency in new items
        name = food_data['name'].lower().strip()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO food (name, calories, protein, fat, carbs, source)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                name,
                float(food_data.get('calories', 0)),
                float(food_data.get('protein', 0)),
                float(food_data.get('fat', 0)),
                float(food_data.get('carbs', 0)),
                food_data.get('source', 'manual')
            ))
            conn.commit()

    def log_consumption(self, date_str: str, food_data: Dict[str, Any]):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO consumption_log (date, food_name, calories, protein, fat, carbs)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                date_str,
                food_data.get('name', 'Unknown'),
                float(food_data.get('calories', 0)),
                float(food_data.get('protein', 0)),
                float(food_data.get('fat', 0)),
                float(food_data.get('carbs', 0))
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