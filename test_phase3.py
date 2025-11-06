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

# 2. Add sample data (ONLY ONE ITEM)
print("Adding sample data...")
db.add_food({
    "name": "apple",
    "calories": 95,
    "protein": 0.5,
    "fat": 0.3,
    "carbs": 25
})

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
print("\n--- SCENARIO 1: Mix of known and unknown ---")
# "apple" is in DB.
# "miso soup" and "sandwich" are NOT.
status1 = tracker.log_meal("I had an apple, some miso soup, and a sandwich")
print(f"Status: {status1}")

print("\n--- SCENARIO 2: Log one of the estimated items AGAIN ---")
# "miso soup" should NOW be in the database.
status2 = tracker.log_meal("I had another miso soup for dinner")
print(f"Status: {status2}")


# 6. --- Final Verification ---
print("\n\n--- FINAL VERIFICATION ---")
summary = tracker.get_summary()
print("\n--- Daily Summary ---")
print(json.dumps(summary, indent=2, ensure_ascii=False))

print("\n--- Database Contents (data/nutrition.json) ---")
# We load the DB from disk to prove it was saved
final_db_data = db._load_db() 
print(json.dumps(final_db_data, indent=2, ensure_ascii=False))

# 7. Test the results
print("\n--- ASSERTIONS ---")

# Test 1: Did we log an apple from the DB?
assert "apple" in status1["logged_from_db"]
print("✅ Test 1 Passed: 'apple' was logged from DB.")

# Test 2: Did we estimate the new items?
# Note: The AI might return "generic sandwich"
assert len(status1["newly_estimated"]) == 2 
print("✅ Test 2 Passed: 2 new items were estimated and logged.")

# Test 3: Are the new items in the database file?
assert "miso soup" in final_db_data
assert final_db_data["miso soup"]["calories"] > 0 # Check that it has data
print("✅ Test 3 Passed: 'miso soup' was saved to the database.")

# Test 4: Did the second log of "miso soup" come from the DB?
assert "miso soup" in status2["logged_from_db"]
assert len(status2["newly_estimated"]) == 0
print("✅ Test 4 Passed: 'miso soup' was correctly retrieved from DB on the 2nd try.")

print("\n🎉 Success! Phase 3 is complete. The app is now self-learning. 🎉")