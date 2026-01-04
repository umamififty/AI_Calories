import sqlite3
import json
import os

# Define paths
JSON_PATH = "data/nutrition.json"
DB_PATH = "data/nutrition.db"

def migrate():
    print(f"🚀 Migrating from {JSON_PATH} to {DB_PATH}...")

    # 1. Check if JSON exists
    if not os.path.exists(JSON_PATH):
        print("❌ JSON file not found! Nothing to migrate.")
        return

    # 2. Load JSON Data
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"   Found {len(data)} items in JSON.")

    # 3. Connect to SQLite (Creates file if not exists)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 4. Create the Table
    # We use 'name' as the PRIMARY KEY so we don't have duplicate food items
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

    # 5. Insert Data
    count = 0
    for key, item in data.items():
        # Extract fields safely
        name = item.get('name', key).lower().strip()
        calories = item.get('calories', 0)
        protein = item.get('protein', 0)
        fat = item.get('fat', 0)
        carbs = item.get('carbs', 0)
        source = item.get('source', 'manual') # Default to manual if missing

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO food (name, calories, protein, fat, carbs, source)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, calories, protein, fat, carbs, source))
            count += 1
        except Exception as e:
            print(f"   ⚠️ Error inserting {name}: {e}")

    # 6. Save and Close
    conn.commit()
    conn.close()
    print(f"✅ Successfully migrated {count} items to SQL!")

if __name__ == "__main__":
    migrate()