import ollama
import json
from typing import Dict, Any, Optional

class AIEngine:
    def __init__(self, model: str = "llama3.2:1b"):
        self.model = model
        self._setup_client()

    def _setup_client(self):
        try:
            ollama.show(self.model)
        except ollama.ResponseError as e:
            print(f"Error: Model '{self.model}' not found. Please run 'ollama pull {self.model}'")
            raise e

    def parse_input(self, raw_text: str) -> Dict[str, Any]:
        system_prompt = f"""
        You are a food parser API. Your ONLY job is to extract food entities.

        RULES:
        1. Output pure JSON only. NO conversational text.
        2. Format: {{"items": ["item1", "item2"]}}
        3. Extract specific full names.
        4. If quantity is specified ("2 eggs"), list twice: ["egg", "egg"].

        User: I had a McChicken
        Response: {{"items": ["McChicken"]}}
        """

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_text},
                ],
                format="json",
                options={'temperature': 0.0}
            )

            data = json.loads(response['message']['content'])

            if "items" in data and isinstance(data["items"], list):
                clean_items = []
                for item in data["items"]:
                    if isinstance(item, str):
                        clean_items.append(item)
                    elif isinstance(item, dict):
                        parts = []
                        if "brand" in item: parts.append(str(item["brand"]))
                        if "name" in item: parts.append(str(item["name"]))
                        clean_items.append(" ".join(parts).strip())

                seen = set()
                deduped = []
                for x in clean_items:
                    key = x.lower().strip()
                    if key not in seen:
                        deduped.append(x)
                        seen.add(key)

                data["items"] = deduped

            print(f"✅ Cleaned AI Output: {json.dumps(data)}")
            return data

        except Exception as e:
            print(f"AI Error: {e}")
            return {"items": [raw_text]}

    def _clean_nutrition_data(self, data: Dict[str, Any], food_name: str) -> Dict[str, Any]:
        cleaned = {}
        cleaned['name'] = data.get('name', food_name).lower()
        for key in ['calories', 'protein', 'fat', 'carbs', 'sugar', 'fiber']:
            val = data.get(key, 0)
            try:
                cleaned[key] = float(val)
            except Exception:
                cleaned[key] = 0.0
        # Sodium may be given in mg
        val = data.get('sodium', 0)
        try:
            cleaned['sodium'] = float(val)
        except Exception:
            cleaned['sodium'] = 0.0
        return cleaned

    def estimate_nutrition(self, food_name: str) -> Optional[Dict[str, Any]]:
        print(f"AI Engine: Estimating nutrition for '{food_name}'...")
        system_prompt = (
            "Return JSON with these fields: name, calories, protein (g), fat (g), "
            "carbs (g), sugar (g), fiber (g), sodium (mg). No explanations, numbers only."
        )
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": food_name}
                ],
                format="json",
            )
            data = json.loads(response['message']['content'])
            return self._clean_nutrition_data(data, food_name)
        except Exception:
            return None

    def parse_override(self, raw_text: str) -> Optional[Dict[str, Any]]:
        print(f"AI Engine: Parsing override...")
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract JSON: name, calories, protein, fat, carbs, sugar (g), "
                            "fiber (g), sodium (mg), per_unit_calories, per_unit_size, total_size."
                        )
                    },
                    {"role": "user", "content": raw_text},
                ],
                format="json",
            )
            return json.loads(response['message']['content'])
        except Exception:
            return None

    def translate(self, text: str) -> str:
        if len(text) < 2 and text not in ["小", "中", "大"]:
            return text
        print(f"   🤖 AI Translating: '{text}'...")
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': f"Translate to English (Name ONLY): {text}"}],
            )
            return response['message']['content'].strip()
        except Exception:
            return text
