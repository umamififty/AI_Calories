from datetime import date
from typing import Dict, Any, List
from .database import FoodDatabase
from app.ai.engine import AIEngine  

class DailyTracker:
    """
    Manages the user's daily nutritional intake and handles daily resets.
    """

    OVERRIDE_KEYWORDS = [
        'kcal', 'calories', 'cal', 
        'protein', 'prot', 'p:',
        'fat', 'f:',
        'carbs', 'carb', 'c:'
    ]
    
    def __init__(self, database: FoodDatabase, ai_engine: AIEngine): 
        """
        Initializes the tracker.
        
        Args:
            database (FoodDatabase): An instance of our FoodDatabase.
            ai_engine (AIEngine): An instance of our AIEngine.
        """
        self.database = database
        self.ai_engine = ai_engine # <-- STORE IT
        self.today_str = self._get_today_str()
        self.daily_totals: Dict[str, float] = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        self.log: List[Dict[str, Any]] = []

    # ... (all the _private methods are UNCHANGED) ...
    def _get_today_str(self) -> str:
        """Helper to get the current date in YYYY-MM-DD format."""
        return date.today().isoformat()

    def _reset_day(self):
        """Resets the tracker for a new day."""
        print(f"It's a new day! Resetting tracker for {self.today_str}.")
        self.daily_totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        self.log = []

    def _check_for_reset(self):
        """
        Checks if the current date is different from the tracked date.
        If so, it triggers a reset.
        """
        current_date_str = self._get_today_str()
        if current_date_str != self.today_str:
            self.today_str = current_date_str
            self._reset_day()

    # --- THIS METHOD IS NOW "PRIVATE" ---
    # We rename it by adding a single underscore_
    def _add_food_item(self, food_name: str) -> bool:
        """
        Internal method to log a single food item from the database.
        
        Args:
            food_name (str): The name of the food (e.g., "apple").
        
        Returns:
            bool: True if the food was found and logged, False otherwise.
        """
        food_data = self.database.get_food(food_name)
        
        if food_data:
            print(f"Tracker: Found '{food_name}' in database. Logging.")
            # Add nutritional values to our daily totals
            for key in self.daily_totals:
                self.daily_totals[key] += food_data.get(key, 0.0)
            
            # Add to our simple log
            self.log.append(food_data)
            return True
        else:
            print(f"Tracker: '{food_name}' not found in database.")
            # In Phase 3, this is where we will use the AI to estimate
            return False

    # --- REPLACE THE OLD log_meal WITH THIS ---
    def log_meal(self, raw_text: str) -> Dict[str, Any]:
        """
        The main public method. Acts as a "traffic cop" to decide
        if this is a manual override or a normal lookup.
        """
        self._check_for_reset()
        print(f"\nProcessing: '{raw_text}'")

        # --- 1. TRAFFIC COP: Check for override keywords ---
        is_override = any(key in raw_text.lower() for key in self.OVERRIDE_KEYWORDS)

        if is_override:
            # --- 2. OVERRIDE LANE ---
            print("Tracker: Override keywords detected.")
            override_data = self.ai_engine.parse_override(raw_text)
            
            if override_data and self._log_override_item(override_data):
                return {
                    "status": "success",
                    "logged_override": [override_data.get('name', 'Override Item')]
                }
            else:
                return {"status": "error", "message": "Failed to log override item."}

        else:
            # --- 3. NORMAL LANE ---
            print("Tracker: No override keywords. Parsing for items...")
            parsed_data = self.ai_engine.parse_input(raw_text)
            
            if "clarification" in parsed_data:
                print(f"AI: {parsed_data['clarification']}")
                return {"status": "clarification_needed", "message": parsed_data['clarification']}
            
            if "items" in parsed_data:
                # This will hold our results
                results = {"logged_from_db": [], "newly_estimated": [], "failed": []}
                
                for item_name in parsed_data.get("items", []):
                    # Run the original logic for each item
                    status = self._log_normal_item(item_name)
                    results[status].append(item_name)
                
                return {"status": "success", **results} # Combine dictionaries
            
        return {"status": "error", "message": "Could not parse input."}

    def _log_override_item(self, data: Dict[str, Any]) -> bool:
        """
        Processes and logs a *temporary* item from override data.
        This does the "per unit" math and adds to totals.
        It DOES NOT save to the database.
        """
        try:
            # --- NEW: Helper function to safely convert values ---
            def safe_float(val):
                if val is None:
                    return 0.0
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return 0.0

            # 1. Safely extract all potential numbers
            per_cal = safe_float(data.get('per_unit_calories'))
            per_size = safe_float(data.get('per_unit_size'))
            total_size = safe_float(data.get('total_size'))

            # Get base stats *first*
            calories = safe_float(data.get('calories'))
            protein = safe_float(data.get('protein'))
            fat = safe_float(data.get('fat'))
            carbs = safe_float(data.get('carbs'))

            # 2. Check for "per unit" math
            # If we have the data, this *overrides* the base calorie number
            if per_cal > 0 and per_size > 0 and total_size > 0:
                calories = (per_cal / per_size) * total_size
                print(f"Tracker: Calculated per-unit calories: {calories:.0f} kcal")
            
            # 3. Build the temporary log entry
            log_item = {
                "name": data.get('name', 'Override Item'),
                "calories": calories,
                "protein": protein,
                "fat": fat,
                "carbs": carbs
            }

            # 4. Add to daily totals and log
            for key in self.daily_totals:
                self.daily_totals[key] += log_item.get(key, 0.0)
            
            self.log.append(log_item)
            print(f"Tracker: Logged override item '{log_item['name']}' ({log_item['calories']:.0f} kcal)")
            return True
            
        except Exception as e:
            # We add the 'e' so we can see the error in the future
            print(f"Tracker Error: Failed to process override data. Error: {e}")
            return False
        
    def _log_normal_item(self, item_name: str) -> str:
        """
        Processes a normal item via the "database -> estimate -> save" flow.
        Returns a status string.
        """
        # 1. Check database
        if self.database.get_food(item_name):
            self._add_food_item(item_name)
            return "logged_from_db"
            
        # 2. Not in DB, estimate
        print(f"Tracker: '{item_name}' not in DB. Estimating...")
        new_data = self.ai_engine.estimate_nutrition(item_name)
        
        if new_data:
            # 3. Save to database
            print(f"Tracker: Saving new item '{item_name}' to database.")
            self.database.add_food(new_data)
            
            # 4. Log it
            if self._add_food_item(new_data['name']):
                return "newly_estimated"
            else:
                return "failed"
        else:
            # AI estimation failed
            print(f"Tracker: AI failed to estimate {item_name}. Skipping.")
            return "failed"


    def get_summary(self) -> Dict[str, Any]:
        """
        Returns a summary of the current day.
        """
        self._check_for_reset()
        return {
            "date": self.today_str,
            "totals": self.daily_totals,
            "log": self.log
        }