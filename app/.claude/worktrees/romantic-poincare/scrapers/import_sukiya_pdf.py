import pdfplumber
import sys
import os
import re

# --- Setup ---
sys.path.append(os.getcwd())
from app.core.database import FoodDatabase
from app.ai.engine import AIEngine

PDF_PATH = "nutrition_sukiya.pdf"
DB_PATH = "data/nutrition.json"

# 1. TRANSLATION MEMORY (Cache)
# We pre-fill this with common terms to save time
TRANSLATION_CACHE = {
    "ミニ": "Mini",
    "並盛": "Regular",
    "中盛": "Medium",
    "大盛": "Large",
    "特盛": "Extra Large",
    "メガ": "Mega",
    "牛丼": "Beef Bowl",
    "牛皿": "Beef Plate",
    "カレー": "Curry",
    "定食": "Set Meal",
    "朝食": "Breakfast",
    "サイド": "Side Dish",
    "お子様": "Kids",
    "豚丼": "Pork Bowl",
    "うな丼": "Eel Bowl",
    "海鮮": "Seafood",
    "丼": "Bowl",
    "みそ汁": "Miso Soup",
    "サラダ": "Salad",
    "たまご": "Egg",
    "おしんこ": "Pickles",
    "納豆": "Natto"
}

def clean_number(text):
    if not text: return 0.0
    try:
        clean = re.sub(r'[^\d.]', '', str(text))
        return float(clean)
    except ValueError: return 0.0

def get_translation(ai, text):
    """Checks cache first, then asks AI."""
    if not text: return ""
    text = text.strip().replace("\n", "")
    
    # 1. Check Cache
    if text in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[text]
    
    # 2. Check partial matches (e.g. "Curry" in "Beef Curry")
    # (Optional optimization, keeps it simple)
    
    # 3. Ask AI
    if ai:
        english = ai.translate(text)
        # Clean up AI output (remove quotes, periods)
        english = english.strip('". ')
        # Save to cache so we don't ask again!
        TRANSLATION_CACHE[text] = english
        return english
    
    return text

def import_pdf():
    print(f"📄 Opening {PDF_PATH}...")
    if not os.path.exists(PDF_PATH):
        print("❌ Error: File not found.")
        return

    db = FoodDatabase(DB_PATH)
    
    print("🔌 Connecting to AI...")
    try:
        ai = AIEngine() 
    except:
        print("❌ AI not running. Skipping translations.")
        ai = None

    count = 0
    
    with pdfplumber.open(PDF_PATH) as pdf:
        print(f"   Found {len(pdf.pages)} pages. Starting fast import...")
        
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                last_category = ""
                last_menu = ""
                
                for row in table:
                    # Filter garbage rows
                    row_str = "".join([str(x) for x in row if x])
                    if "kcal" in row_str or "エネルギー" in row_str or len(row_str) < 5:
                        continue
                    
                    # Ensure we have enough columns
                    if len(row) < 5: continue

                    try:
                        # 1. Extract & Fill Down
                        category = row[0] if row[0] else last_category
                        menu_name = row[1] if row[1] else last_menu
                        
                        # Update "Last Seen" for next iteration
                        last_category = category
                        last_menu = menu_name
                        
                        # Skip if we still don't have a menu name
                        if not menu_name: continue

                        size_raw = row[2]

                        # 2. Parse Numbers (Scan for first valid kcal)
                        values = []
                        for col in row[3:]:
                            val = clean_number(col)
                            if val > 0: values.append(val)
                        
                        if not values: continue
                        
                        # Map stats (Best guess based on standard layout)
                        kcal = values[0]
                        prot = values[1] if len(values) > 1 else 0
                        fat = values[2] if len(values) > 2 else 0
                        carb = values[3] if len(values) > 3 else 0

                        # 3. Translate (With Cache)
                        cat_en = get_translation(ai, category)
                        menu_en = get_translation(ai, menu_name)
                        size_en = get_translation(ai, size_raw)
                        
                        full_name = f"Sukiya {menu_en} ({size_en})"
                        
                        # 4. Save
                        item_data = {
                            "name": full_name,
                            "calories": kcal,
                            "protein": prot,
                            "fat": fat,
                            "carbs": carb
                        }
                        
                        db.add_food(item_data)
                        print(f"   + Saved: {full_name}")
                        count += 1
                        
                    except Exception as e:
                        continue
    
    print(f"\n✅ Import Complete! Added {count} items.")

if __name__ == "__main__":
    import_pdf()