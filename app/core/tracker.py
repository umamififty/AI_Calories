from datetime import date
from typing import Dict, Any, List
from .database import FoodDatabase
from app.ai.engine import AIEngine
# --- 1. IMPORT THE NEW SERVICE ---
from app.services.off import OpenFoodFactsService 

class DailyTracker:
    # ... (OVERRIDE_KEYWORDS list stays here) ...
    OVERRIDE_KEYWORDS = [
        'kcal', 'calories', 'cal', 
        'protein', 'prot', 'p:',
        'fat', 'f:',
        'carbs', 'carb', 'c:'
    ]

    def __init__(self, database: FoodDatabase, ai_engine: AIEngine):
        self.database = database
        self.ai_engine = ai_engine
        # --- 2. INITIALIZE IT ---
        self.off_service = OpenFoodFactsService()
        
        self.today_str = self._get_today_str()
        self.daily_totals: Dict[str, float] = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        self.log: List[Dict[str, Any]] = []

    # ... (Keep _get_today_str, _reset_day, _check_for_reset, _add_food_item, _log_override_item) ...
    # ... (Copy those existing methods from your current file) ...
    # ... (Or paste the whole file if you want me to provide the full text) ...

    # ... Just to ensure nothing is lost, here are the untouched helpers ...
    def _get_today_str(self) -> str:
        return date.today().isoformat()

    def _reset_day(self):
        print(f"It's a new day! Resetting tracker for {self.today_str}.")
        self.daily_totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        self.log = []

    def _check_for_reset(self):
        current_date_str = self._get_today_str()
        if current_date_str != self.today_str:
            self.today_str = current_date_str
            self._reset_day()

    def _add_food_item(self, food_name: str) -> bool:
        food_data = self.database.get_food(food_name)
        if food_data:
            print(f"Tracker: Found '{food_name}' in database. Logging.")
            for key in self.daily_totals:
                self.daily_totals[key] += food_data.get(key, 0.0)
            self.log.append(food_data)
            return True
        return False
    
    def _log_override_item(self, data: Dict[str, Any]) -> bool:
        # ... (Keep your existing robust implementation of this) ...
        try:
            def safe_float(val):
                if val is None: return 0.0
                try: return float(val)
                except (ValueError, TypeError): return 0.0
            
            per_cal = safe_float(data.get('per_unit_calories'))
            per_size = safe_float(data.get('per_unit_size'))
            total_size = safe_float(data.get('total_size'))
            calories = safe_float(data.get('calories'))
            protein = safe_float(data.get('protein'))
            fat = safe_float(data.get('fat'))
            carbs = safe_float(data.get('carbs'))

            if per_cal > 0 and per_size > 0 and total_size > 0:
                calories = (per_cal / per_size) * total_size
                print(f"Tracker: Calculated per-unit calories: {calories:.0f} kcal")
            
            log_item = { "name": data.get('name', 'Override Item'), "calories": calories, "protein": protein, "fat": fat, "carbs": carbs }
            for key in self.daily_totals: self.daily_totals[key] += log_item.get(key, 0.0)
            self.log.append(log_item)
            print(f"Tracker: Logged override item '{log_item['name']}' ({log_item['calories']:.0f} kcal)")
            return True
        except Exception as e:
            print(f"Tracker Error: Failed to process override data. Error: {e}")
            return False


    # --- 3. UPDATED LOGIC FLOW ---
    def _log_normal_item(self, item_name: str) -> str:
        """
        Processes a normal item via the "database -> OFF -> estimate" flow.
        """
        # 1. Check Database
        if self.database.get_food(item_name):
            self._add_food_item(item_name)
            return "logged_from_db"
            
        print(f"Tracker: '{item_name}' not in DB. Checking external sources...")
        
        # 2. Check OpenFoodFacts (NEW!)
        off_data = self.off_service.find_food(item_name)
        if off_data:
            print(f"Tracker: Found '{item_name}' in OpenFoodFacts!")
            # Save to our local DB so it's fast next time
            self.database.add_food(off_data)
            # Log it
            self._add_food_item(off_data['name'])
            return "found_in_off"

        # 3. AI Estimation (Fallback)
        print(f"Tracker: Not in OFF. Asking AI to estimate...")
        new_data = self.ai_engine.estimate_nutrition(item_name)
        
        if new_data:
            print(f"Tracker: Saving new AI-estimated item '{item_name}' to database.")
            self.database.add_food(new_data)
            if self._add_food_item(new_data['name']):
                return "newly_estimated"
            else:
                return "failed"
        else:
            print(f"Tracker: AI failed to estimate {item_name}. Skipping.")
            return "failed"

    def log_meal(self, raw_text: str) -> Dict[str, Any]:
        # ... (This method stays mostly the same, but I'll update the results dict) ...
        self._check_for_reset()
        print(f"\nProcessing: '{raw_text}'")

        is_override = any(key in raw_text.lower() for key in self.OVERRIDE_KEYWORDS)

        if is_override:
            print("Tracker: Override keywords detected.")
            override_data = self.ai_engine.parse_override(raw_text)
            if override_data and self._log_override_item(override_data):
                return {"status": "success", "logged_override": [override_data.get('name')]}
            else:
                return {"status": "error", "message": "Failed to log override item."}

        else:
            print("Tracker: No override keywords. Parsing for items...")
            parsed_data = self.ai_engine.parse_input(raw_text)
            
            if "clarification" in parsed_data:
                print(f"AI: {parsed_data['clarification']}")
                return {"status": "clarification_needed", "message": parsed_data['clarification']}
            
            if "items" in parsed_data:
                # Added "found_in_off" to results categories
                results = {"logged_from_db": [], "newly_estimated": [], "found_in_off": [], "failed": []}
                
                for item_name in parsed_data.get("items", []):
                    status = self._log_normal_item(item_name)
                    if status in results:
                        results[status].append(item_name)
                
                return {"status": "success", **results}
            
        return {"status": "error", "message": "Could not parse input."}

    def get_summary(self) -> Dict[str, Any]:
        self._check_for_reset()
        return { "date": self.today_str, "totals": self.daily_totals, "log": self.log }