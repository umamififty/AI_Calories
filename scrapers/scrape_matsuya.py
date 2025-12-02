import requests
from bs4 import BeautifulSoup
import re
import sys
import os
from urllib.parse import urljoin

# --- Setup to import from our main app ---
sys.path.append(os.getcwd())
from app.core.database import FoodDatabase

BASE_URL = "https://www.matsuyafoods.co.jp/english/menu/"

# --- UPDATED CATEGORY LIST ---
KNOWN_CATEGORIES = [
    ("Gyumeshi", "https://www.matsuyafoods.co.jp/english/menu/gyumeshi/index.html"),
    ("Curry", "https://www.matsuyafoods.co.jp/english/menu/curry/index.html"),
    ("Set Meal", "https://www.matsuyafoods.co.jp/english/menu/teishoku/index.html"),
    ("Breakfast", "https://www.matsuyafoods.co.jp/english/menu/morning/index.html"),
    ("Side Dish", "https://www.matsuyafoods.co.jp/english/menu/sidemenu/index.html"),
    ("Bowl", "https://www.matsuyafoods.co.jp/english/menu/don/index.html"),
    ("Drinks", "https://www.matsuyafoods.co.jp/english/menu/drink/index.html"),
    ("Toppings", "https://www.matsuyafoods.co.jp/english/menu/topping/index.html")
]

def clean_value(text, pattern):
    """Helper to extract a float number from text using regex."""
    match = re.search(pattern, text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0
    return 0.0

def get_category_links():
    """Step 1: Visits the main menu page and finds all category URLs."""
    print(f"🕷️ Crawling Main Menu: {BASE_URL}")
    categories = []
    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'index.html' in href:
                full_url = urljoin(BASE_URL, href)
                if full_url != BASE_URL and full_url != BASE_URL + "index.html":
                    slug = full_url.replace(BASE_URL, "").replace("/index.html", "").replace("index.html", "").strip("/")
                    if slug:
                        name = slug.capitalize()
                        if (name, full_url) not in categories:
                            categories.append((name, full_url))

        print(f"-> Discovered {len(categories)} categories.")
        return categories

    except Exception as e:
        print(f"Error finding categories: {e}")
        return []

def get_item_links(category_name, category_url):
    """Step 2: Visits a category page and finds all individual item URLs."""
    print(f"   📂 Scanning Category: {category_name}...")
    links = []
    try:
        response = requests.get(category_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.endswith('.html') and 'index.html' not in href and 'http' not in href:
                full_url = urljoin(category_url, href)
                if full_url not in links:
                    links.append(full_url)
        
        print(f"   -> Found {len(links)} items in {category_name}.")
        return links

    except Exception as e:
        print(f"   Error scanning category {category_name}: {e}")
        return []

def scrape_item_page(url, category_name, db):
    """Step 3: Scrapes a single item page for nutrition data using matched lists."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- 1. Get Accurate Item Name ---
        item_name = "Unknown Item"
        # Try the specific class provided by user: <h3 class="page_title_bg">
        title_tag = soup.find('h3', class_='page_title_bg')
        
        if title_tag:
            item_name = title_tag.get_text(strip=True)
        else:
            # Fallback to page title if specific tag is missing
            if soup.title and soup.title.string:
                item_name = soup.title.string.split('|')[0].strip()

        # --- 2. Get Sizes from Price List ---
        # <ul class="priceList"> <li>Small: ...</li> </ul>
        price_sizes = []
        price_list_ul = soup.find('ul', class_='priceList')
        
        if price_list_ul:
            for li in price_list_ul.find_all('li'):
                text = li.get_text(strip=True)
                # Extract "Small" from "Small: ¥630"
                if ':' in text:
                    size_label = text.split(':')[0].strip()
                    price_sizes.append(size_label)
                else:
                    # If no colon, just use the text before any digits (heuristic)
                    # or just default to the whole text if it's short
                    price_sizes.append(text)

        # --- 3. Get Nutrition Rows ---
        nutrition_rows = []
        # Find all <li> that contain "Calories:"
        for li in soup.find_all('li'):
            if "Calories:" in li.get_text():
                nutrition_rows.append(li)

        # --- 4. Match and Save ---
        
        # Scenario A: Perfect Match (3 sizes, 3 nutrition tables)
        if len(price_sizes) > 0 and len(price_sizes) == len(nutrition_rows):
            # print(f"      + Matched {len(price_sizes)} sizes for: {item_name}")
            
            for i in range(len(price_sizes)):
                size_label = price_sizes[i]
                row_li = nutrition_rows[i]
                row_text = row_li.get_text(strip=True)
                
                save_food_to_db(db, item_name, size_label, row_text)

        # Scenario B: No Price List found, or mismatch
        # Fallback to reading the size from the nutrition row itself (e.g. "Regular. Calories:...")
        else:
            # print(f"      ~ Fallback scraping for: {item_name}")
            for row_li in nutrition_rows:
                row_text = row_li.get_text(strip=True)
                
                # Try to extract size from the text before "Calories"
                parts = row_text.split("Calories:")
                if len(parts) > 1:
                    size_label = parts[0].strip(" -. \t\n")
                else:
                    size_label = ""
                
                save_food_to_db(db, item_name, size_label, row_text)
        
        # Verify something was saved by checking if nutrition rows existed
        if nutrition_rows:
             print(f"      + Saved: {item_name}")

    except Exception as e:
        pass

def save_food_to_db(db, base_name, variant_name, text_data):
    """Helper to format the name and save to DB."""
    
    # Build Name: "Matsuya Beef Bowl (Regular)"
    if variant_name:
        full_name = f"{base_name} ({variant_name})"
    else:
        full_name = base_name
    
    if "Matsuya" not in full_name:
        full_name = f"Matsuya {full_name}"
    
    # Extract Stats
    calories = clean_value(text_data, r'Calories:\s*([\d\.]+)kcal')
    protein = clean_value(text_data, r'Protein:\s*([\d\.]+)g')
    fat = clean_value(text_data, r'Total Fat:\s*([\d\.]+)g')
    carbs = clean_value(text_data, r'Carbohydrate:\s*([\d\.]+)g')
    
    if calories > 0:
        food_item = {
            "name": full_name,
            "calories": calories,
            "protein": protein,
            "fat": fat,
            "carbs": carbs
        }
        db.add_food(food_item)

def main():
    db_path = "data/nutrition.json"
    db = FoodDatabase(db_path)
    
    print("🚀 Starting Matsuya Crawler (Matched Logic)...")
    
    categories = get_category_links()
    
    # Always merge known categories with discovered ones to be safe
    # (This ensures Drinks/Toppings are included even if auto-discovery fails)
    if not categories:
        print("⚠️  Auto-discovery failed. Using known list.")
        categories = KNOWN_CATEGORIES
    else:
        # Optional: You could merge KNOWN_CATEGORIES into discovered ones here if you wanted
        pass 
    
    # Override for this run to ensure we get everything
    categories = KNOWN_CATEGORIES

    for cat_name, cat_url in categories:
        item_links = get_item_links(cat_name, cat_url)
        for link in item_links:
            scrape_item_page(link, cat_name, db)
            
    print("\n✅ Crawling complete. Database updated.")

if __name__ == "__main__":
    main()