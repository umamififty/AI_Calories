import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import sys
import os

# --- Import your existing backend ---
sys.path.append(os.getcwd())
from app.core.database import FoodDatabase
from app.core.tracker import DailyTracker
from app.ai.engine import AIEngine

class CalorieApp(toga.App):
    def startup(self):
        """
        Construct and show the Toga application.
        """
        # 1. Initialize the Brains (SQL + AI)
        db_path = "data/nutrition.db"
        self.db = FoodDatabase(db_path) 
        self.ai = AIEngine()
        self.tracker = DailyTracker(self.db, self.ai)
        
        # 2. Main Container
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        # 3. UI Elements
        self.status_label = toga.Label(
            'Welcome! Ready to track.',
            style=Pack(padding=(0, 5), color='gray', font_size=10)
        )
        
        # Big Calorie Counter
        self.progress_label = toga.Label(
            'Calories: 0 / 2000',
            style=Pack(padding_top=10, font_size=20, font_weight='bold', text_align='center')
        )
        
        # Macro Breakdown
        self.macro_label = toga.Label(
            'P: 0g  |  F: 0g  |  C: 0g',
            style=Pack(padding_bottom=10, font_size=12, color='#666666', text_align='center')
        )
        
        # Input Area
        input_box = toga.Box(style=Pack(direction=ROW, padding=5))
        self.text_input = toga.TextInput(
            placeholder='E.g. "Matsuya Beef Bowl"',
            style=Pack(flex=1, padding_right=5)
        )
        send_button = toga.Button(
            'Log Meal',
            on_press=self.handle_log,
            style=Pack(width=80)
        )
        input_box.add(self.text_input)
        input_box.add(send_button)

        # Log History List
        self.log_list = toga.MultilineTextInput(
            readonly=True,
            style=Pack(flex=1, padding=5, font_family='monospace')
        )

        # 4. Assemble the Window
        main_box.add(self.status_label)
        main_box.add(self.progress_label)
        main_box.add(self.macro_label)
        main_box.add(input_box)
        main_box.add(self.log_list)

        self.main_window = toga.MainWindow(title='AI Calorie Tracker')
        self.main_window.content = main_box
        self.main_window.show()
        
        # Load initial stats
        self.refresh_stats()

    def handle_log(self, widget):
        text = self.text_input.value
        if not text:
            return

        self.status_label.text = "Thinking... (AI Processing)"
        
        try:
            result = self.tracker.log_meal(text)
            
            # --- CASE 1: SUCCESS ---
            if result['status'] == 'success':
                self.text_input.value = "" 
                self.status_label.text = "Logged successfully!"
                self.refresh_stats()
                
            # --- CASE 2: CLARIFICATION NEEDED (THE FIX) ---
            elif result['status'] == 'clarification_needed':
                # Show a Pop-Up Dialog so the user CANNOT miss it
                self.main_window.info_dialog(
                    "Please be more specific", 
                    result['message']
                )
                self.status_label.text = "Waiting for specific size..."
                
            # --- CASE 3: ERROR ---
            else:
                self.status_label.text = f"Error: {result.get('message', 'Unknown')}"

        except Exception as e:
             self.status_label.text = f"Error: {e}"

    def refresh_stats(self):
        """Updates labels and list with fresh data from DB."""
        summary = self.tracker.get_summary()
        totals = summary['totals']
        
        # Update Totals
        cals = int(totals['calories'])
        p = int(totals['protein'])
        f = int(totals['fat'])
        c = int(totals['carbs'])
        
        self.progress_label.text = f"Calories: {cals} / 2000"
        self.macro_label.text = f"Prot: {p}g  |  Fat: {f}g  |  Carb: {c}g"
        
        # Update Log List
        log_text = "--- Today's Log ---\n"
        for item in summary['log']:
            name = item.get('name', 'Unknown')
            k = int(item.get('calories', 0))
            p_itm = int(item.get('protein', 0))
            f_itm = int(item.get('fat', 0))
            c_itm = int(item.get('carbs', 0))
            
            log_text += f"• {name}\n"
            log_text += f"  └─ {k} kcal  (P:{p_itm} F:{f_itm} C:{c_itm})\n\n"
            
        self.log_list.value = log_text

def main():
    return CalorieApp('AI Calories', 'org.umamififty.aicalories')

if __name__ == '__main__':
    main().main_loop()