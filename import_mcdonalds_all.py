import sqlite3
import os
import glob
from bs4 import BeautifulSoup

# Configuration
DB_PATH = "data/nutrition.db"

def clean_float(value_str):
    """Converts strings like '477kcal' or '21.9g' to float 477.0."""
    try:
        # Keep only numbers and dots
        clean = ''.join(c for c in value_str if c.isdigit() or c == '.')
        return float(clean)
    except ValueError:
        return 0.0

def parse_and_import(file_pattern):
    # 1. Connect to Database
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure table exists
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

    # 2. Find all HTML files
    files = glob.glob(file_pattern)
    if not files:
        print("❌ No HTML files found. Make sure they are in this folder.")
        return

    total_count = 0

    for file_path in files:
        print(f"📂 Processing: {os.path.basename(file_path)}...")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")

            # McDonald's nutrition table usually has this class
            rows = soup.select("table.allergy-info__table tbody tr")
            
            file_count = 0
            for row in rows:
                cells = row.find_all("td")
                if not cells: continue

                # Extract Data (Based on McDonald's Japan standard table structure)
                # Col 0: Name (often inside <a>)
                # Col 1: Energy (kcal)
                # Col 2: Protein (g)
                # Col 3: Fat (g)
                # Col 4: Carbs (g)
                
                raw_name = cells[0].get_text(strip=True)
                
                # Add Brand Name for easier searching
                if "mcdonald" not in raw_name.lower():
                    name = f"McDonald's {raw_name}"
                else:
                    name = raw_name

                calories = clean_float(cells[1].get_text())
                protein = clean_float(cells[2].get_text())
                fat = clean_float(cells[3].get_text())
                carbs = clean_float(cells[4].get_text())

                # Insert into DB
                cursor.execute('''
                    INSERT OR REPLACE INTO food (name, calories, protein, fat, carbs, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, calories, protein, fat, carbs, 'mcdonalds_jp'))
                
                file_count += 1
                total_count += 1
            
            print(f"   -> Imported {file_count} items.")

        except Exception as e:
            print(f"   ⚠️ Error reading {file_path}: {e}")

    conn.commit()
    conn.close()
    print(f"\n✅ SUCCESS! Total items added to database: {total_count}")

if __name__ == "__main__":
    # This looks for ALL .html files in the current folder
    parse_and_import("*.html")