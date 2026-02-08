import rumps
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.getcwd())
from app.core.database import FoodDatabase
from app.core.tracker import DailyTracker
from app.ai.engine import AIEngine

class CalorieMenuBarComplete(rumps.App):
    def __init__(self):
        super(CalorieMenuBarComplete, self).__init__("🍽️", quit_button=None)
        
        # Initialize backend
        db_path = "data/nutrition.db"
        self.db = FoodDatabase(db_path)
        self.ai = AIEngine()
        self.tracker = DailyTracker(self.db, self.ai)
        
        # Build initial menu
        self.refresh_menu()
        
        # Auto-refresh every 30 seconds
        rumps.Timer(self.auto_refresh, 30).start()
    
    def refresh_menu(self):
        """Rebuild entire menu with all data"""
        summary = self.tracker.get_summary()
        totals = summary['totals']
        
        # Clear menu
        self.menu.clear()
        
        # ============================================
        # SECTION 1: QUICK INPUT (always at top)
        # ============================================
        self.menu.add(rumps.MenuItem("┏━━━━━━━━━━━━━━━━━━━━━━━━━┓", callback=None))
        self.menu.add(rumps.MenuItem("┃   📝 QUICK LOG          ┃", callback=None))
        self.menu.add(rumps.MenuItem("┗━━━━━━━━━━━━━━━━━━━━━━━━━┛", callback=None))
        
        input_btn = rumps.MenuItem("➕ Click to log food...", callback=self.show_input)
        self.menu.add(input_btn)
        
        self.menu.add(rumps.separator)
        
        # ============================================
        # SECTION 2: TODAY'S DASHBOARD
        # ============================================
        self.menu.add(rumps.MenuItem("┏━━━━━━━━━━━━━━━━━━━━━━━━━┓", callback=None))
        self.menu.add(rumps.MenuItem("┃   📊 TODAY'S STATS      ┃", callback=None))
        self.menu.add(rumps.MenuItem("┗━━━━━━━━━━━━━━━━━━━━━━━━━┛", callback=None))
        
        # Calorie progress
        cals = int(totals['calories'])
        goal = 2000
        percentage = min((cals / goal) * 100, 100)
        
        # Big number display
        self.menu.add(rumps.MenuItem(f"", callback=None))
        self.menu.add(rumps.MenuItem(f"      🔥 {cals} / {goal} kcal", callback=None))
        self.menu.add(rumps.MenuItem(f"         ({percentage:.1f}% of goal)", callback=None))
        
        # Visual progress bar
        bar_length = 25
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        self.menu.add(rumps.MenuItem(f"      [{bar}]", callback=None))
        self.menu.add(rumps.MenuItem(f"", callback=None))
        
        # Macro breakdown
        self.menu.add(rumps.MenuItem("   Macros:", callback=None))
        self.menu.add(rumps.MenuItem(f"      💪 Protein:  {int(totals['protein'])}g", callback=None))
        self.menu.add(rumps.MenuItem(f"      🥑 Fat:      {int(totals['fat'])}g", callback=None))
        self.menu.add(rumps.MenuItem(f"      🍞 Carbs:    {int(totals['carbs'])}g", callback=None))
        
        self.menu.add(rumps.separator)
        
        # ============================================
        # SECTION 3: WEEKLY MINI-CHART
        # ============================================
        self.menu.add(rumps.MenuItem("┏━━━━━━━━━━━━━━━━━━━━━━━━━┓", callback=None))
        self.menu.add(rumps.MenuItem("┃   📈 WEEKLY TREND       ┃", callback=None))
        self.menu.add(rumps.MenuItem("┗━━━━━━━━━━━━━━━━━━━━━━━━━┛", callback=None))
        
        weekly_data = self.get_weekly_data()
        self.add_weekly_chart(weekly_data)
        
        # Weekly summary
        total_week = sum(weekly_data['calories'])
        avg_week = total_week / 7 if weekly_data['calories'] else 0
        self.menu.add(rumps.MenuItem(f"      Weekly avg: {int(avg_week)} kcal/day", callback=None))
        
        self.menu.add(rumps.separator)
        
        # ============================================
        # SECTION 4: TODAY'S MEAL LOG
        # ============================================
        self.menu.add(rumps.MenuItem("┏━━━━━━━━━━━━━━━━━━━━━━━━━┓", callback=None))
        self.menu.add(rumps.MenuItem("┃   🍽️  MEAL LOG          ┃", callback=None))
        self.menu.add(rumps.MenuItem("┗━━━━━━━━━━━━━━━━━━━━━━━━━┛", callback=None))
        
        logs = summary['log']
        if logs:
            # Show last 6 meals
            recent_logs = logs[-6:]
            for log in reversed(recent_logs):
                name = log.get('name', 'Unknown')
                kcal = int(log.get('calories', 0))
                p = int(log.get('protein', 0))
                
                # Truncate long names
                if len(name) > 22:
                    name = name[:19] + "..."
                
                # Format with aligned columns
                meal_line = f"   • {name}"
                self.menu.add(rumps.MenuItem(meal_line, callback=None))
                self.menu.add(rumps.MenuItem(f"       {kcal} kcal  |  {p}g protein", callback=None))
            
            if len(logs) > 6:
                self.menu.add(rumps.MenuItem(f"   ... and {len(logs) - 6} more meals", callback=None))
        else:
            self.menu.add(rumps.MenuItem("   No meals logged today", callback=None))
            self.menu.add(rumps.MenuItem("   Click ➕ above to start!", callback=None))
        
        self.menu.add(rumps.separator)
        
        # ============================================
        # SECTION 5: MACRO PIE CHART (ASCII)
        # ============================================
        self.menu.add(rumps.MenuItem("   Macro Split (calories):", callback=None))
        self.add_macro_pie(totals)
        
        self.menu.add(rumps.separator)
        
        # ============================================
        # SECTION 6: ACTIONS
        # ============================================
        self.menu.add(rumps.MenuItem("📊 Open Detailed Charts", callback=self.show_charts))
        self.menu.add(rumps.MenuItem("🔄 Refresh Now", callback=self.manual_refresh))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("❌ Quit App", callback=rumps.quit_application))
        
        # Update menu bar title
        if cals > 0:
            self.title = f"🍽️ {cals}"
        else:
            self.title = "🍽️"
    
    def add_weekly_chart(self, data):
        """Add ASCII bar chart for weekly calories"""
        if not data['calories'] or sum(data['calories']) == 0:
            self.menu.add(rumps.MenuItem("      No data this week", callback=None))
            return
        
        max_cal = max(data['calories'])
        goal = 2000
        
        for day, cal in zip(data['dates'], data['calories']):
            # Bar length based on goal (not max)
            bar_length = 15
            filled = int((cal / goal) * bar_length) if goal > 0 else 0
            filled = min(filled, bar_length)  # Cap at bar_length
            
            # Color coding (using different characters)
            if cal < goal * 0.5:
                bar_char = "▁"  # Under-eating
            elif cal > goal * 1.2:
                bar_char = "▉"  # Over-eating
            else:
                bar_char = "▓"  # On target
            
            bar = bar_char * filled + "░" * (bar_length - filled)
            
            # Today's day highlighted
            today = datetime.now().strftime('%a')
            marker = "→" if day == today else " "
            
            cal_str = str(int(cal)).rjust(4)
            chart_line = f"   {marker} {day} │{bar}│ {cal_str}"
            self.menu.add(rumps.MenuItem(chart_line, callback=None))
    
    def add_macro_pie(self, totals):
        """Add ASCII representation of macro breakdown"""
        # Calculate calories from each macro
        p_cal = totals['protein'] * 4
        f_cal = totals['fat'] * 9
        c_cal = totals['carbs'] * 4
        total = p_cal + f_cal + c_cal
        
        if total == 0:
            self.menu.add(rumps.MenuItem("      No macros logged yet", callback=None))
            return
        
        # Calculate percentages
        p_pct = (p_cal / total) * 100
        f_pct = (f_cal / total) * 100
        c_pct = (c_cal / total) * 100
        
        # Visual bars
        bar_length = 20
        p_bar = "█" * int((p_pct / 100) * bar_length)
        f_bar = "█" * int((f_pct / 100) * bar_length)
        c_bar = "█" * int((c_pct / 100) * bar_length)
        
        self.menu.add(rumps.MenuItem(f"      💪 {p_bar} {p_pct:.0f}%", callback=None))
        self.menu.add(rumps.MenuItem(f"      🥑 {f_bar} {f_pct:.0f}%", callback=None))
        self.menu.add(rumps.MenuItem(f"      🍞 {c_bar} {c_pct:.0f}%", callback=None))
    
    def get_weekly_data(self):
        """Get last 7 days of nutrition data"""
        data = {
            'dates': [],
            'calories': [],
            'protein': [],
            'fat': [],
            'carbs': []
        }
        
        today = datetime.now().date()
        
        for i in range(7):
            date = today - timedelta(days=6-i)
            date_str = date.isoformat()
            
            logs = self.db.get_daily_log(date_str)
            
            daily_totals = {
                'calories': 0,
                'protein': 0,
                'fat': 0,
                'carbs': 0
            }
            
            for log in logs:
                for key in daily_totals.keys():
                    daily_totals[key] += log.get(key, 0)
            
            data['dates'].append(date.strftime('%a'))
            for key in ['calories', 'protein', 'fat', 'carbs']:
                data[key].append(daily_totals[key])
        
        return data
    
    @rumps.clicked("➕ Click to log food...")
    def show_input(self, _):
        """Show food input dialog"""
        window = rumps.Window(
            message="What did you eat?",
            title="🍽️ Quick Log",
            default_text="",
            ok="Log Meal",
            cancel="Cancel",
            dimensions=(350, 24)
        )
        
        response = window.run()
        
        if response.clicked and response.text.strip():
            self.log_food(response.text.strip())
    
    def log_food(self, text):
        """Process food logging"""
        try:
            # Show processing notification
            rumps.notification(
                title="Processing...",
                subtitle=text,
                message="AI is analyzing"
            )
            
            result = self.tracker.log_meal(text)
            
            if result['status'] == 'success':
                # Refresh menu immediately
                self.refresh_menu()
                
                # Success notification with new total
                summary = self.tracker.get_summary()
                cals = int(summary['totals']['calories'])
                
                rumps.notification(
                    title="✅ Logged Successfully",
                    subtitle=text,
                    message=f"Total today: {cals} kcal"
                )
            
            elif result['status'] == 'clarification_needed':
                rumps.alert(
                    title="🤔 Need More Info",
                    message=result['message']
                )
            
            else:
                rumps.alert(
                    title="❌ Error",
                    message=result.get('message', 'Failed to log meal')
                )
        
        except Exception as e:
            rumps.alert(
                title="❌ Error",
                message=f"Something went wrong: {str(e)}"
            )
    
    @rumps.clicked("📊 Open Detailed Charts")
    def show_charts(self, _):
        """Open chart window in a subprocess to avoid AppKit conflicts"""
        import subprocess
        import sys
        
        # Create a standalone chart script
        chart_script = '''
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.getcwd())
from app.core.database import FoodDatabase

db = FoodDatabase("data/nutrition.db")

# Get weekly data
data = {'dates': [], 'calories': [], 'protein': [], 'fat': [], 'carbs': []}
today = datetime.now().date()
for i in range(7):
    date = today - timedelta(days=6-i)
    logs = db.get_daily_log(date.isoformat())
    totals = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0}
    for log in logs:
        for key in totals.keys():
            totals[key] += log.get(key, 0)
    data['dates'].append(date.strftime('%a'))
    for key in ['calories', 'protein', 'fat', 'carbs']:
        data[key].append(totals[key])

# Get today's data
today_logs = db.get_daily_log(today.isoformat())

# Create charts
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
fig.patch.set_facecolor('#F5F5F5')
fig.suptitle('📊 Nutrition Dashboard', fontsize=18, fontweight='bold')

# Chart 1: Weekly Calories
bars = ax1.bar(data['dates'], data['calories'], color='#3498DB', alpha=0.8)
ax1.axhline(y=2000, color='#E74C3C', linestyle='--', linewidth=2, label='Goal')
ax1.set_title('Weekly Calorie Intake', fontweight='bold')
ax1.set_ylabel('Calories (kcal)')
ax1.legend()
ax1.grid(axis='y', alpha=0.3)
for bar in bars:
    h = bar.get_height()
    if h > 0:
        ax1.text(bar.get_x() + bar.get_width()/2., h, f'{int(h)}',
                ha='center', va='bottom', fontsize=9)

# Chart 2: Macro Pie
macro_totals = {
    'Protein': sum(log.get('protein', 0) * 4 for log in today_logs),
    'Fat': sum(log.get('fat', 0) * 9 for log in today_logs),
    'Carbs': sum(log.get('carbs', 0) * 4 for log in today_logs)
}
if sum(macro_totals.values()) > 0:
    colors = ['#E74C3C', '#F39C12', '#3498DB']
    wedges, texts, autotexts = ax2.pie(
        macro_totals.values(), labels=macro_totals.keys(),
        colors=colors, autopct='%1.1f%%', startangle=90
    )
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
else:
    ax2.text(0.5, 0.5, 'No data yet', ha='center', va='center', fontsize=12)
ax2.set_title("Today's Macro Split", fontweight='bold')

# Chart 3: Weekly Macros
if sum(data['protein']) > 0:
    ax3.stackplot(data['dates'], data['protein'], data['fat'], data['carbs'],
                  labels=['Protein', 'Fat', 'Carbs'],
                  colors=['#E74C3C', '#F39C12', '#3498DB'], alpha=0.7)
    ax3.legend(loc='upper left')
else:
    ax3.text(0.5, 0.5, 'No data yet', ha='center', va='center', fontsize=12)
ax3.set_title('Weekly Macro Trends', fontweight='bold')
ax3.set_ylabel('Grams')
ax3.grid(axis='y', alpha=0.3)

# Chart 4: Progress
total_cals = sum(log.get('calories', 0) for log in today_logs)
goal = 2000
pct = min((total_cals / goal) * 100, 150)
color = '#2ECC71' if pct <= 100 else '#E74C3C'
ax4.barh(['Progress'], [min(pct, 100)], height=0.5, color=color, alpha=0.8)
if pct > 100:
    ax4.barh(['Progress'], [pct - 100], left=100, height=0.5, color='#E74C3C', alpha=0.5)
ax4.set_xlim(0, 150)
ax4.set_xlabel('Percentage of Goal')
ax4.set_yticks([])
ax4.text(75, 0, f'{int(total_cals)} / {goal} kcal\\n{pct:.1f}%',
        ha='center', va='center', fontsize=11, fontweight='bold')
ax4.set_title("Today's Calorie Progress", fontweight='bold')

plt.tight_layout()
plt.show()
'''
        
        try:
            # Write temp script
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(chart_script)
                script_path = f.name
            
            # Run in subprocess
            subprocess.Popen([sys.executable, script_path])
            
        except Exception as e:
            rumps.alert(
                title="Chart Error",
                message=f"Failed to open charts: {str(e)}"
            )
    
    @rumps.clicked("🔄 Refresh Now")
    def manual_refresh(self, _):
        """Manual refresh"""
        self.refresh_menu()
        rumps.notification(
            title="Refreshed",
            subtitle="",
            message="All data updated"
        )
    
    def auto_refresh(self, _):
        """Auto-refresh timer callback"""
        self.refresh_menu()


if __name__ == "__main__":
    CalorieMenuBarComplete().run()