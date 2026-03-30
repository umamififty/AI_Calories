import os
import json
from app.core.database import FoodDatabase
from app.core.tracker import DailyTracker
from app.ai.engine import AIEngine

# --- 1. Setup ---
DB_FILE = "data/nutrition.json"
os.makedirs("data", exist_ok=True) # Ensure data dir exists

print("Initializing components (this may take a moment)...")

# 1. Init Database
# This will load your EXISTING data/nutrition.json
db = FoodDatabase(DB_FILE)
print(f"Database loaded. Found {len(db.db_data)} existing food items.")

# 2. Init AI Engine
try:
    ai = AIEngine(model="qwen3:0.6b")
except Exception as e:
    print("\n---FATAL ERROR---")
    print("Could not initialize AI Engine. Is Ollama running?")
    print(f"Have you run 'ollama pull qwen3:0.6b'?")
    exit()

# 3. Init Tracker
tracker = DailyTracker(database=db, ai_engine=ai)

print("\n" + "=" * 40)
print("     SIMPLE CALORIE TESTER")
print("  (Logs are saved to data/nutrition.json)")
print("  Type 'exit' or 'quit' to stop.")
print("=" * 40)

# --- 4. Main Loop ---
while True:
    try:
        # Get user input
        user_input = input("\nWhat did you eat? > ")
        
        if user_input.lower() in ['exit', 'quit']:
            print("Goodbye! Your data is saved.")
            break
            
        if not user_input:
            continue
            
        # 5. Process the input
        print(f"\n... Processing: '{user_input}' ...")
        status = tracker.log_meal(user_input)
        
        # 6. Report the status
        print("\n--- Processing Results ---")
        if status['status'] == 'clarification_needed':
            print(f"AI: {status['message']}")
        
        if status['status'] == 'success':
            if status.get('logged_from_db'):
                print(f"✅ Logged from DB: {', '.join(status['logged_from_db'])}")
            if status.get('newly_estimated'):
                print(f"✨ NEW items estimated: {', '.join(status['newly_estimated'])}")
                print(f"  (These are now saved in data/nutrition.json)")
            if status.get('failed'):
                 print(f"❌ Failed to log: {', '.join(status['failed'])}")

        # 7. Show the current day's totals
        summary = tracker.get_summary()
        print("\n--- Today's Totals ---")
        print(f"  Date: {summary['date']}")
        print(f"  Calories: {summary['totals']['calories']:.0f} kcal")
        print(f"  Protein:  {summary['totals']['protein']:.1f}g")
        print(f"  Fat:      {summary['totals']['fat']:.1f}g")
        print(f"  Carbs:    {summary['totals']['carbs']:.1f}g")
        print("-" * 26)

    except KeyboardInterrupt:
        # Allow exiting with Ctrl+C
        print("\nGoodbye! Your data is saved.")
        break
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        print("Please try again.")