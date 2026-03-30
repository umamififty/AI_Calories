import json
import os
from typing import Any

DEFAULTS = {
    "calorie_goal": 2000,
    "protein_goal": 150,
    "fat_goal": 65,
    "carbs_goal": 250,
    "sugar_goal": 50,
    "fiber_goal": 25,
    "sodium_goal": 2300,
    "reminder_interval_hours": 4.0,
    "reminders_enabled": True,
}

class SettingsManager:
    def __init__(self, config_path: str = "data/config.json"):
        self.config_path = config_path
        self._data = dict(DEFAULTS)
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    saved = json.load(f)
                self._data.update(saved)
            except Exception:
                pass

    def save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str) -> Any:
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any):
        self._data[key] = value
        self.save()

    def get_all(self) -> dict:
        return dict(self._data)
