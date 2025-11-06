import os
import json
from app.core.database import FoodDatabase
from app.core.tracker import DailyTracker
from app.ai.engine import AIEngine

# --- Setup ---
DB_FILE = "data/nutrition.json"
os.makedirs("data", exist_ok=True)

if os.path.exists(DB_FILE):
    os.remove(DB_FILE) # Start with a clean DB

print("Initializing database...")
db = FoodDatabase(DB_FILE)

print("\nInitializing AI engine...")
try:
    ai = AIEngine(model="qwen3:0.6b")
except Exception as e:
    print(f"---FATAL ERROR---")
    print("Could not initialize AI Engine. Is Ollama running?")
    exit()

print("\nInitializing tracker...")
tracker = DailyTracker(database=db, ai_engine=ai)

# --- Run Scenarios ---

print("\n--- SCENARIO 1: Normal Lane (Estimation) ---")
# This should use the normal "estimate -> save to DB" logic
status1 = tracker.log_meal("I had an apple")
print(f"Status: {status1}")

print("\n--- SCENARIO 2: Override Lane (Total) ---")
# This should use the override logic and NOT save to DB
status2 = tracker.log_meal("Suntory Boss Coffee, 32 kcal, 1.5p, 0.5f, 5c")
print(f"Status: {status2}")

print("\n--- SCENARIO 3: Override Lane (Per Unit) ---")
# This should do the math (45 * 10 = 450) and NOT save to DB
status3 = tracker.log_meal("1000ml pack of soy milk, 45 kcal per 100ml")
print(f"Status: {status3}")

# --- Final Verification ---
print("\n\n--- FINAL VERIFICATION ---")
summary = tracker.get_summary()
print("\n--- Daily Summary ---")
print(json.dumps(summary, indent=2, ensure_ascii=False))

print("\n--- Database Contents (data/nutrition.json) ---")
final_db_data = db._load_db() 
print(json.dumps(final_db_data, indent=2, ensure_ascii=False))

# --- Assertions ---
print("\n--- ASSERTIONS ---")

# Test 1: Did the "apple" get estimated and saved?
assert "apple" in final_db_data
print("✅ Test 1 Passed: 'apple' was estimated and saved to DB.")

# Test 2: Did the override items NOT get saved?
assert "suntory boss coffee" not in final_db_data
assert "soy milk" not in final_db_data
print("✅ Test 2 Passed: Override items were NOT saved to DB.")

# Test 3: Is the total calorie count correct?
# We expect apple (AI guess, ~95) + Boss Coffee (32) + Soy Milk (450)
apple_cals = final_db_data['apple']['calories']
expected_cals = apple_cals + 32 + 450
actual_cals = summary['totals']['calories']

print(f"Actual Cals: {actual_cals:.0f} | Expected Cals: {expected_cals:.0f}")
assert abs(actual_cals - expected_cals) < 5 # Allow 5 cal margin for AI variance
print("✅ Test 3 Passed: Total calories are correct (Override + Estimation).")

print("\n🎉 Success! Phase 3.5 is complete. The app now has two logic paths. 🎉")