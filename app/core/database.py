import json
import os
from typing import Optional, Dict, Any

class FoodDatabase:
    """
    Handles all interactions with the JSON database file.
    """
    def __init__(self, db_path: str):
        """
        Initializes the database.
        
        Args:
            db_path (str): The file path to the nutrition.json file.
        """
        self.db_path = db_path
        self.db_data = self._load_db()

    def _load_db(self) -> Dict[str, Dict[str, Any]]:
        """
        Loads the database from the JSON file.
        If the file doesn't exist, it returns an empty dictionary.
        """
        if not os.path.exists(self.db_path):
            return {}
        
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Database file {self.db_path} is corrupt. Starting fresh.")
            return {}

    def _save_db(self):
        """
        Saves the current state of the database back to the JSON file.
        """
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.db_data, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"Error: Could not save database to {self.db_path}. Error: {e}")

    def get_food(self, food_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves nutritional info for a food item.
        
        Args:
            food_name (str): The name of the food to look up.
        
        Returns:
            Optional[Dict]: The nutrition data if found, else None.
        """
        # Use .lower() for a simple, case-insensitive lookup
        key = food_name.lower()
        return self.db_data.get(key)

    def add_food(self, food_data: Dict[str, Any]) -> bool:
        """
        Adds or updates a food item in the database.
        
        Args:
            food_data (Dict): A dictionary containing the food's nutritional info.
                              Must include a 'name' key.
        
        Returns:
            bool: True if save was successful, False otherwise.
        """
        if 'name' not in food_data:
            print("Error: 'name' is required to add food to database.")
            return False
            
        key = food_data['name'].lower()
        self.db_data[key] = food_data
        
        # Save after every addition
        self._save_db()
        print(f"Database: Added/Updated '{key}'")
        return True