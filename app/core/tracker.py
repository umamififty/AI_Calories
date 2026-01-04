from datetime import date
from typing import Dict, Any, List
from .database import FoodDatabase
from app.ai.engine import AIEngine
from app.services.off import OpenFoodFactsService 

class DailyTracker:
    OVERRIDE_KEYWORDS = ['kcal', 'calories', 'cal', 'protein', 'prot', 'p:', 'fat', 'f:', 'carbs', 'carb', 'c:']
    KNOWN_CHAINS = {'matsuya', 'sukiya', '7-eleven', 'seven eleven', 'family mart', 'lawson', 'mcdonalds', 'starbucks', 'mos burger'}

    def __init__(self, database: FoodDatabase, ai_engine: AIEngine):
        self.database = database
        self.ai_engine = ai_engine
        self.off_service = OpenFoodFactsService()
        self.today_str = self._get_today_str()
        self.log = []
        self.daily_totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        self._load_today_from_db() 

    def _get_today_str(self) -> str:
        return date.today().isoformat()

    def _load_today_from_db(self):
        print(f"Tracker: Loading history for {self.today_str}...")
        try:
            items = self.database.get_daily_log(self.today_str)
            self.log = items
            for item in items:
                self.daily_totals['calories'] += item.get('calories', 0)
                self.daily_totals['protein'] += item.get('protein', 0)
                self.daily_totals['fat'] += item.get('fat', 0)
                self.daily_totals['carbs'] += item.get('carbs', 0)
        except Exception as e:
            print(f"Tracker Error loading history: {e}")

    def _reset_day(self):
        self.daily_totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        self.log = []

    def _check_for_reset(self):
        current_date_str = self._get_today_str()
        if current_date_str != self.today_str:
            self.today_str = current_date_str
            self._reset_day()
            self._load_today_from_db()

    def _add_food_item(self, food_name: str) -> bool:
        food_data = self.database.get_food(food_name)
        if food_data:
            print(f"Tracker: Found '{food_name}' in database. Logging.")
            for key in self.daily_totals: self.daily_totals[key] += food_data.get(key, 0.0)
            self.log.append(food_data)
            self.database.log_consumption(self.today_str, food_data)
            return True
        return False
    
    def _log_override_item(self, data: Dict[str, Any]) -> bool:
        try:
            calories = float(data.get('calories', 0))
            if data.get('per_unit_calories') and data.get('total_size'):
                 calories = (float(data['per_unit_calories']) / float(data['per_unit_size'])) * float(data['total_size'])
            
            log_item = { "name": data.get('name', 'Override'), "calories": calories, "protein": float(data.get('protein',0)), "fat": float(data.get('fat',0)), "carbs": float(data.get('carbs',0)) }
            for key in self.daily_totals: self.daily_totals[key] += log_item.get(key, 0.0)
            self.log.append(log_item)
            self.database.log_consumption(self.today_str, log_item)
            return True
        except: return False

    def _log_normal_item(self, item_name: str) -> Dict[str, Any]:
        # 1. Exact Match
        if self.database.get_food(item_name):
            self._add_food_item(item_name)
            return {"status": "success"}

        # 2. Chain Search
        detected_chain = next((c for c in self.KNOWN_CHAINS if c in item_name.lower()), None)
        if detected_chain:
            print(f"Tracker: Chain '{detected_chain}' detected.")
            candidates = self.database.find_candidates(item_name)
            if not candidates:
                clean = item_name.lower().replace(detected_chain, "").replace("burger", "").replace("set", "").strip()
                if len(clean) > 2:
                    candidates = self.database.find_candidates(clean)

            if len(candidates) == 1:
                self._add_food_item(candidates[0]['name'])
                return {"status": "success"}
            elif len(candidates) > 1:
                options = [c['name'] for c in candidates[:4]]
                msg = f"Multiple matches found for '{item_name}'.\nDid you mean:\n\n" + "\n".join([f"• {opt}" for opt in options])
                return {"status": "clarification_needed", "message": msg}

        # 3. Fuzzy Match
        fuzzy = self.database.fuzzy_search(item_name)
        if fuzzy:
            self._add_food_item(fuzzy['name'])
            return {"status": "success"}

        # 4. Skip OFF for simple words
        if len(item_name.split()) > 1:
            off_data = self.off_service.find_food(item_name)
            if off_data:
                self.database.add_food(off_data)
                self._add_food_item(off_data['name'])
                return {"status": "success"}

        # 5. AI Estimate
        new_data = self.ai_engine.estimate_nutrition(item_name)
        if new_data:
            self.database.add_food(new_data)
            if self._add_food_item(new_data['name']):
                return {"status": "success"}
                
        return {"status": "failed"}

    def log_meal(self, raw_text: str) -> Dict[str, Any]:
        self._check_for_reset()
        print(f"\nProcessing: '{raw_text}'")

        if self.database.get_food(raw_text):
            self._add_food_item(raw_text)
            return {"status": "success"}

        is_override = any(key in raw_text.lower() for key in self.OVERRIDE_KEYWORDS)
        if is_override:
            override_data = self.ai_engine.parse_override(raw_text)
            if override_data and self._log_override_item(override_data):
                return {"status": "success"}
            return {"status": "error", "message": "Failed to log override."}

        parsed_data = self.ai_engine.parse_input(raw_text)
        
        if "items" in parsed_data:
            for item_name in parsed_data.get("items", []):
                result = self._log_normal_item(item_name)
                # Pass clarification status immediately to UI
                if result.get("status") == "clarification_needed":
                    return result
            return {"status": "success"}
            
        return {"status": "error", "message": "Could not parse input."}

    def get_summary(self) -> Dict[str, Any]:
        self._check_for_reset()
        return { "date": self.today_str, "totals": self.daily_totals, "log": self.log }