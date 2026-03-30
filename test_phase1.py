import os
import json
from app.core.database import FoodDatabase
from app.core.tracker import DailyTracker

# --- Setup ---
DB_FILE = "data/nutrition.json"

# Ensure the 'data' directory exists
os.makedirs("data", exist_ok=True)

# 1. Initialize the Database
print("Initializing database...")
db = FoodDatabase(DB_FILE)

# 2. Manually add some sample data (to simulate our scraper)
print("\nAdding sample data...")
db.add_food({
    "name": "Apple",
    "calories": 95,
    "protein": 0.5,
    "fat": 0.3,
    "carbs": 25
})
db.add_food({
    "name": "Chicken Breast",
    "calories": 165,
    "protein": 31,
    "fat": 3.6,
    "carbs": 0
})
db.add_food({
    "name": "白ご飯",  # "White Rice"
    "calories": 160,
    "protein": 2.7,
    "fat": 0.3,
    "carbs": 36
})

# 3. Initialize the Tracker
print("\nInitializing tracker...")
tracker = DailyTracker(database=db)

# 4. Log some food
print("\n--- Logging Food ---")
tracker.add_food_item("Apple")
tracker.add_food_item("白ご飯")
tracker.add_food_item("a sandwich") # This one will fail (for now)

# 5. Get the summary
print("\n--- Daily Summary ---")
summary = tracker.get_summary()
print(json.dumps(summary, indent=2, ensure_ascii=False))

# 6. Test the totals
expected_calories = 95 + 160
print(f"\nReported Calories: {summary['totals']['calories']}")
print(f"Expected Calories: {expected_calories}")
assert summary['totals']['calories'] == expected_calories
print("Success! Core engine is working.")