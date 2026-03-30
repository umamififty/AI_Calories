import openfoodfacts
from typing import Optional, Dict, Any

class OpenFoodFactsService:
    def __init__(self):
        # It's polite (and required) to define a user_agent so they know who we are
        self.api = openfoodfacts.API(user_agent="AI_Calorie_Tracker/1.0")

    def find_food(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Searches OpenFoodFacts for a product name.
        Returns the first result formatted for our database.
        """
        print(f"   🌍 Searching OpenFoodFacts for '{query}'...")
        
        try:
            # 1. Search the API (Global search)
            # The library doesn't accept 'country' here, so we search everything.
            search_result = self.api.product.text_search(query)
                
            if not search_result or search_result['count'] == 0:
                return None

            # 2. Get the best match (first item)
            product = search_result['products'][0]
            nutriments = product.get('nutriments', {})
            
            # 3. Clean the data
            # OFF often gives data "per 100g".
            calories = nutriments.get('energy-kcal_value') or nutriments.get('energy-kcal_100g')
            protein = nutriments.get('proteins_value') or nutriments.get('proteins_100g')
            fat = nutriments.get('fat_value') or nutriments.get('fat_100g')
            carbs = nutriments.get('carbohydrates_value') or nutriments.get('carbohydrates_100g')
            
            product_name = product.get('product_name', query)
            
            # If calories are missing, this entry is useless
            if not calories:
                return None

            # 4. Format for our DB
            return {
                "name": f"{product_name} (OFF)",
                "calories": float(calories),
                "protein": float(protein) if protein else 0.0,
                "fat": float(fat) if fat else 0.0,
                "carbs": float(carbs) if carbs else 0.0,
                "source": "openfoodfacts" # Metadata
            }

        except Exception as e:
            print(f"   ⚠️ OpenFoodFacts Error: {e}")
            return None