import ollama
import json
from typing import List, Dict, Any, Optional

class AIEngine:
    """
    Handles all communication with the Ollama model
    to parse user input.
    """
    def __init__(self, model: str = "qwen3:0.6b"):
        """
        Initializes the AI engine.

        Args:
            model (str): The name of the Ollama model to use.
        """
        self.model = model
        self._setup_client()

    def _setup_client(self):
        """Checks if the model is available and provides instructions if not."""
        try:
            ollama.show(self.model)
        except ollama.ResponseError as e:
            print(f"Error: Model '{self.model}' not found.")
            print(f"Please run 'ollama pull {self.model}' in your terminal.")
            raise e

    def parse_input(self, raw_text: str) -> Dict[str, Any]:
        """
        Parses the user's raw text into a structured list of food items.
        
        Args:
            raw_text (str): The user's input, e.g., "I ate two onigiri and a cola".

        Returns:
            Dict[str, Any]: A dictionary containing a list of items
                            or a clarification question.
        """
        
        # --- NEW, MORE AGGRESSIVE PROMPT ---
        system_prompt = f"""
        You are a food item extraction assistant. Your ONLY job is to extract
        food items from user text and return a valid JSON object.
        
        **JSON OUTPUT RULES:**
        1. If the input is clear, return: {{"items": ["item1", "item2"]}}
        2. If the input is ambiguous (like "a sandwich" or "soup"), you MUST
           return: {{"clarification": "What kind of sandwich was it?"}}
        3. DO NOT return "items" if you are asking for "clarification".
        
        **EXTRACTION RULES:**
        1. **QUANTITY:** If the user says "two apples" or "2 eggs", you MUST
           list the item multiple times: ["apple", "apple"] or ["egg", "egg"].
        2. **PLURALS:** ALWAYS return the singular form of an item. "apples" -> "apple".
        3. **LANGUAGE:** If the user uses Japanese (e.g., "白ご飯"), use the
           common English equivalent (e.g., "white rice").
        
        **EXAMPLES:**
        
        User: For breakfast, I had 2 eggs, some bacon, and a coffee.
        Response: {{"items": ["egg", "egg", "bacon", "coffee"]}}
        
        User: I ate a sandwich for lunch.
        Response: {{"clarification": "What kind of sandwich was it?"}}
        
        User: I had two large apples.
        Response: {{"items": ["apple", "apple"]}}
        
        User: 朝ご飯は白ご飯と納豆でした
        Response: {{"items": ["white rice", "natto"]}}
        
        User: just some soup
        Response: {{"clarification": "What kind of soup was it?"}}
        """
        # --- END OF NEW PROMPT ---

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_text},
                ],
                format="json",  # This forces the model to output valid JSON
            )
            
            response_text = response['message']['content']
            
            # --- ADDED A PRINT STATEMENT FOR DEBUGGING ---
            print(f"AI Response: {response_text}")
            
            return json.loads(response_text) # Parse the JSON string into a Python dict

        except json.JSONDecodeError:
            print(f"AI Error: Invalid JSON received: {response_text}")
            return {"clarification": "I'm sorry, I had trouble understanding that. Could you rephrase?"}
        except Exception as e:
            print(f"An error occurred with the AI engine: {e}")
            return {"clarification": "I'm sorry, I'm having trouble connecting to the AI."}
        
    # ... (Keep all your existing methods like __init__, _setup_client, and parse_input) ...

    def _clean_nutrition_data(self, data: Dict[str, Any], food_name: str) -> Dict[str, Any]:
        """
        Private helper to clean and validate AI-generated nutrition data.
        It forces the data into the correct format.
        """
        cleaned = {}
        
        # Ensure name is correct
        cleaned['name'] = data.get('name', food_name).lower()
        
        # Define the keys we care about
        nutrient_keys = ['calories', 'protein', 'fat', 'carbs']
        
        for key in nutrient_keys:
            value = data.get(key, 0)
            
            # Try to convert value to a float, handling strings like "35 kcal" or "10g"
            if isinstance(value, (int, float)):
                cleaned[key] = float(value)
            elif isinstance(value, str):
                try:
                    # Find the first number in the string
                    cleaned[key] = float(''.join(c for c in value if c.isdigit() or c == '.'))
                except ValueError:
                    cleaned[key] = 0.0 # Default to 0 if conversion fails
            else:
                cleaned[key] = 0.0 # Default to 0 for other types
                
        return cleaned

    def estimate_nutrition(self, food_name: str) -> Optional[Dict[str, Any]]:
        """
        Estimates the nutritional information for a single food item.

        Args:
            food_name (str): The name of the food to estimate (e.g., "miso soup").

        Returns:
            Optional[Dict]: A dictionary with the nutritional data or None if failed.
        """
        print(f"AI Engine: Estimating nutrition for '{food_name}'...")
        
        system_prompt = f"""
        You are a nutritional database. Your ONLY task is to return a single,
        precise JSON object with the estimated nutritional information for the
        food item the user provides.
        
        **RULES:**
        1.  **ONLY JSON:** Respond with ONLY the JSON object. Do not include
            any introductory text like "Here is the nutrition...".
        2.  **FIELDS:** The JSON object MUST include these keys:
            "name" (string), "calories" (float), "protein" (float),
            "fat" (float), "carbs" (float).
        3.  **UNITS:** Use grams for protein, fat, and carbs.
        4.  **BEST GUESS:** If the item is vague (e.g., "sandwich"), provide a
            reasonable average (e.g., a "generic turkey sandwich").
            
        **EXAMPLE 1:**
        User: miso soup
        Response: {{"name": "miso soup", "calories": 35.0, "protein": 2.0, "fat": 1.0, "carbs": 5.0}}
        
        **EXAMPLE 2:**
        User: sandwich
        Response: {{"name": "generic sandwich", "calories": 350.0, "protein": 15.0, "fat": 12.0, "carbs": 40.0}}
        """
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": food_name},
                ],
                format="json",
            )
            
            response_text = response['message']['content']
            
            # --- DEBUGGING ---
            print(f"AI Estimation Response: {response_text}")
            
            raw_data = json.loads(response_text)
            
            # Clean and validate the data
            cleaned_data = self._clean_nutrition_data(raw_data, food_name)
            
            return cleaned_data

        except Exception as e:
            print(f"AI Error: Failed to estimate nutrition for {food_name}. Error: {e}")
            return None
    
    # ... (Keep all your existing methods: __init__, _setup_client, parse_input)
    # ... (Keep _clean_nutrition_data and estimate_nutrition) ...
    
    # --- ADD THIS NEW METHOD ---
    def parse_override(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Parses raw text for explicit nutritional data (e.g., "30kcal").
        This bypasses database lookups.
        """
        print(f"AI Engine: Parsing override for '{raw_text}'...")
        
        system_prompt = f"""
        You are a data extraction bot. Your ONLY task is to extract nutritional
        information from the user's text and return a single JSON object.
        
        **RULES:**
        1.  **ONLY JSON:** Respond with ONLY the JSON object.
        2.  **FIELDS:** Extract values for these keys:
            "name" (string), "calories" (float), "protein" (float), "fat" (float), "carbs" (float),
            "per_unit_calories" (float), "per_unit_size" (float, e.g., 100),
            "total_size" (float, e.g., 500).
        3.  **NULL:** If a value is not found, return `null` for that key.
        4.  **NAME:** The "name" should be the food item, including any size/brand.
        5.  **UNITS:** Do not include units (kcal, g, ml) in the numbers.
        
        **EXAMPLE 1 (Total Stats):**
        User: I had a Suntory Boss Coffee, 32 kcal, 1.5p, 0.5f, 5c
        Response: {{
            "name": "Suntory Boss Coffee", "calories": 32, "protein": 1.5, "fat": 0.5, "carbs": 5,
            "per_unit_calories": null, "per_unit_size": null, "total_size": null
        }}

        **EXAMPLE 2 (Per-Unit Stats):**
        User: a big 500ml caffe latte, 30kcal per 100ml
        Response: {{
            "name": "caffe latte 500ml", "calories": null, "protein": null, "fat": null, "carbs": null,
            "per_unit_calories": 30, "per_unit_size": 100, "total_size": 500
        }}
        
        **EXAMPLE 3 (Partial):**
        User: a croissant, 300 calories
        Response: {{
            "name": "croissant", "calories": 300, "protein": null, "fat": null, "carbs": null,
            "per_unit_calories": null, "per_unit_size": null, "total_size": null
        }}
        """
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_text},
                ],
                format="json",
            )
            
            response_text = response['message']['content']
            print(f"AI Override Response: {response_text}")
            return json.loads(response_text)

        except Exception as e:
            print(f"AI Error: Failed to parse override. Error: {e}")
            return None