import os
import json
from app.core.database import FoodDatabase
from app.core.tracker import DailyTracker
from app.ai.engine import AIEngine

# --- Setup ---
DB_FILE = "data/nutrition.json"
os.makedirs("data", exist_ok=True)

# 1. Initialize the Database (and clear it for a clean test)
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

print("Initializing database...")
db = FoodDatabase(DB_FILE)

# 2. Add sample data
print("\nAdding sample data...")
db.add_food({
    "name": "apple",
    "calories": 95,
    "protein": 0.5,
    "fat": 0.3,
    "carbs": 25
})
db.add_food({
    "name": "白ご飯",  # "White Rice" (original)
    "calories": 160,
    "protein": 2.7,
    "fat": 0.3,
    "carbs": 36
})

# --- NEW TEST DATA ---
db.add_food({
    "name": "white rice", # Add the English key
    "calories": 160,
    "protein": 2.7,
    "fat": 0.3,
    "carbs": 36
})
db.add_food({
    "name": "natto",
    "calories": 100,
    "protein": 8.5,
    "fat": 5.0,
    "carbs": 7.5
})
db.add_food({
    "name": "banana",
    "calories": 105,
    "protein": 1.3,
    "fat": 0.4,
    "carbs": 27
})
# --- END NEW TEST DATA ---


# 3. Initialize the AI Engine
print("\nInitializing AI engine...")
try:
    ai = AIEngine(model="qwen3:0.6b")
except Exception as e:
    print(f"\n---FATAL ERROR---")
    print("Could not initialize AI Engine. Is Ollama running?")
    print(f"Have you run 'ollama pull qwen3:0.6b'?")
    exit()


# 4. Initialize the Tracker
print("\nInitializing tracker...")
tracker = DailyTracker(database=db, ai_engine=ai)

# 5. --- Run Scenarios ---
print("\n--- SCENARIO 1: Clear input, items found ---")
# "apple" is in DB, "miso soup" is not.
status1 = tracker.log_meal("I had an apple and some miso soup for lunch")
print(f"Status: {status1}")


print("\n--- SCENARIO 2: Japanese input, items found ---")
# "white rice" and "natto" are now in our DB.
status2 = tracker.log_meal("朝ご飯は白ご飯と納豆でした") # "Breakfast was white rice and natto"
print(f"Status: {status2}")


print("\n--- SCENARIO 3: Ambiguous input ---")
# This should now trigger the "clarification" response
status3 = tracker.log_meal("I ate a sandwich")
print(f"Status: {status3}")


print("\n--- SCENARIO 4: Quantity input ---")
# This should now log "apple" twice and "banana" once.
status4 = tracker.log_meal("two apples and a banana")
print(f"Status: {status4}")


# 6. --- Final Summary ---
print("\n\n--- FINAL DAILY SUMMARY ---")
summary = tracker.get_summary()
print(json.dumps(summary, indent=2, ensure_ascii=False))

# 7. Test the totals
# Expected: 95 (apple) + 160 (white rice) + 100 (natto) + 95 (apple) + 95 (apple) + 105 (banana)
# Note: Scenario 3 (sandwich) should log 0 calories.
expected_calories = 95 + 160 + 100 + 95 + 95 + 105
print(f"\nReported Calories: {summary['totals']['calories']}")
print(f"Expected Calories: {expected_calories}")
assert summary['totals']['calories'] == expected_calories
print("Success! Phase 2 is complete.")