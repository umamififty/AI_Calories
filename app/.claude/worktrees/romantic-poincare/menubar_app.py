import rumps
import sys
import os
import subprocess
import tempfile
from datetime import datetime, timedelta

sys.path.append(os.getcwd())
from app.core.database import FoodDatabase
from app.core.tracker import DailyTracker
from app.ai.engine import AIEngine
from app.core.settings import SettingsManager


class CalorieMenuBarComplete(rumps.App):
    def __init__(self):
        super(CalorieMenuBarComplete, self).__init__("🍽️", quit_button=None)

        db_path = "data/nutrition.db"
        self.db = FoodDatabase(db_path)
        self.ai = AIEngine()
        self.tracker = DailyTracker(self.db, self.ai)
        self.settings = SettingsManager()

        # Notification state — prevent spam
        self._last_meal_reminder_dt: datetime | None = None
        self._evening_nudge_sent_date: str | None = None
        self._weekly_summary_sent_date: str | None = None

        self.refresh_menu()

        # Auto-refresh every 30 seconds
        rumps.Timer(self.auto_refresh, 30).start()
        # Notification check every 15 minutes
        rumps.Timer(self.check_and_notify, 900).start()

    # ─────────────────────────────────────────────────────────
    # MENU BUILDER
    # ─────────────────────────────────────────────────────────

    def refresh_menu(self):
        """Rebuild entire menu with all data."""
        # Re-read settings on every refresh so GUI changes take effect immediately
        self.settings.load()

        summary = self.tracker.get_summary()
        totals = summary['totals']
        self.menu.clear()

        cal_goal = self.settings.get("calorie_goal")

        # ── SECTION 1: QUICK INPUT ────────────────────────────
        self.menu.add(rumps.MenuItem("┏━━━━━━━━━━━━━━━━━━━━━━━━━┓", callback=None))
        self.menu.add(rumps.MenuItem("┃   📝 QUICK LOG          ┃", callback=None))
        self.menu.add(rumps.MenuItem("┗━━━━━━━━━━━━━━━━━━━━━━━━━┛", callback=None))
        self.menu.add(rumps.MenuItem("➕ Click to log food...", callback=self.show_input))
        self.menu.add(rumps.separator)

        # ── SECTION 2: TODAY'S STATS ──────────────────────────
        self.menu.add(rumps.MenuItem("┏━━━━━━━━━━━━━━━━━━━━━━━━━┓", callback=None))
        self.menu.add(rumps.MenuItem("┃   📊 TODAY'S STATS      ┃", callback=None))
        self.menu.add(rumps.MenuItem("┗━━━━━━━━━━━━━━━━━━━━━━━━━┛", callback=None))

        cals = int(totals['calories'])
        percentage = min((cals / cal_goal) * 100, 100) if cal_goal else 0

        self.menu.add(rumps.MenuItem("", callback=None))
        self.menu.add(rumps.MenuItem(f"      🔥 {cals} / {cal_goal} kcal", callback=None))
        self.menu.add(rumps.MenuItem(f"         ({percentage:.1f}% of goal)", callback=None))

        bar_length = 25
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        self.menu.add(rumps.MenuItem(f"      [{bar}]", callback=None))
        self.menu.add(rumps.MenuItem("", callback=None))

        # Core macros
        p_goal = self.settings.get("protein_goal")
        f_goal = self.settings.get("fat_goal")
        c_goal = self.settings.get("carbs_goal")
        s_goal = self.settings.get("sugar_goal")
        fi_goal = self.settings.get("fiber_goal")
        na_goal = self.settings.get("sodium_goal")

        self.menu.add(rumps.MenuItem("   Macros:", callback=None))
        self.menu.add(rumps.MenuItem(
            f"      💪 Protein:  {int(totals['protein'])}g / {p_goal}g", callback=None))
        self.menu.add(rumps.MenuItem(
            f"      🥑 Fat:      {int(totals['fat'])}g / {f_goal}g", callback=None))
        self.menu.add(rumps.MenuItem(
            f"      🍞 Carbs:    {int(totals['carbs'])}g / {c_goal}g", callback=None))
        self.menu.add(rumps.MenuItem(
            f"      🍬 Sugar:    {int(totals['sugar'])}g / {s_goal}g", callback=None))
        self.menu.add(rumps.MenuItem(
            f"      🌿 Fiber:    {int(totals['fiber'])}g / {fi_goal}g", callback=None))
        self.menu.add(rumps.MenuItem(
            f"      🧂 Sodium:   {int(totals['sodium'])}mg / {na_goal}mg", callback=None))

        self.menu.add(rumps.separator)

        # ── SECTION 3: WEEKLY TREND ───────────────────────────
        self.menu.add(rumps.MenuItem("┏━━━━━━━━━━━━━━━━━━━━━━━━━┓", callback=None))
        self.menu.add(rumps.MenuItem("┃   📈 WEEKLY TREND       ┃", callback=None))
        self.menu.add(rumps.MenuItem("┗━━━━━━━━━━━━━━━━━━━━━━━━━┛", callback=None))

        weekly_data = self.get_weekly_data()
        self.add_weekly_chart(weekly_data, cal_goal)

        total_week = sum(weekly_data['calories'])
        avg_week = total_week / 7 if weekly_data['calories'] else 0
        self.menu.add(rumps.MenuItem(f"      Weekly avg: {int(avg_week)} kcal/day", callback=None))
        self.menu.add(rumps.separator)

        # ── SECTION 4: MEAL LOG ───────────────────────────────
        self.menu.add(rumps.MenuItem("┏━━━━━━━━━━━━━━━━━━━━━━━━━┓", callback=None))
        self.menu.add(rumps.MenuItem("┃   🍽️  MEAL LOG          ┃", callback=None))
        self.menu.add(rumps.MenuItem("┗━━━━━━━━━━━━━━━━━━━━━━━━━┛", callback=None))

        logs = summary['log']
        if logs:
            for log in reversed(logs[-6:]):
                name = log.get('name', 'Unknown')
                kcal = int(log.get('calories', 0))
                p = int(log.get('protein', 0))
                if len(name) > 22:
                    name = name[:19] + "..."
                self.menu.add(rumps.MenuItem(f"   • {name}", callback=None))
                self.menu.add(rumps.MenuItem(f"       {kcal} kcal  |  {p}g protein", callback=None))
            if len(logs) > 6:
                self.menu.add(rumps.MenuItem(f"   ... and {len(logs) - 6} more meals", callback=None))
        else:
            self.menu.add(rumps.MenuItem("   No meals logged today", callback=None))
            self.menu.add(rumps.MenuItem("   Click ➕ above to start!", callback=None))

        self.menu.add(rumps.separator)

        # ── SECTION 5: MACRO SPLIT ────────────────────────────
        self.menu.add(rumps.MenuItem("   Macro Split (calories):", callback=None))
        self.add_macro_pie(totals)
        self.menu.add(rumps.separator)

        # ── SECTION 6: ACTIONS ────────────────────────────────
        self.menu.add(rumps.MenuItem("📊 Open Detailed Charts", callback=self.show_charts))
        self.menu.add(rumps.MenuItem("📤 Export Data", callback=self.show_export))
        self.menu.add(rumps.MenuItem("⚙️ Settings & Goals", callback=self.show_settings))
        self.menu.add(rumps.MenuItem("🔄 Refresh Now", callback=self.manual_refresh))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("❌ Quit App", callback=rumps.quit_application))

        self.title = f"🍽️ {cals}" if cals > 0 else "🍽️"

    # ─────────────────────────────────────────────────────────
    # CHART HELPERS
    # ─────────────────────────────────────────────────────────

    def add_weekly_chart(self, data, goal: int):
        if not data['calories'] or sum(data['calories']) == 0:
            self.menu.add(rumps.MenuItem("      No data this week", callback=None))
            return

        today = datetime.now().strftime('%a')
        for day, cal in zip(data['dates'], data['calories']):
            bar_length = 15
            filled = min(int((cal / goal) * bar_length), bar_length) if goal else 0
            bar_char = "▁" if cal < goal * 0.5 else ("▉" if cal > goal * 1.2 else "▓")
            bar = bar_char * filled + "░" * (bar_length - filled)
            marker = "→" if day == today else " "
            cal_str = str(int(cal)).rjust(4)
            self.menu.add(rumps.MenuItem(f"   {marker} {day} │{bar}│ {cal_str}", callback=None))

    def add_macro_pie(self, totals):
        p_cal = totals['protein'] * 4
        f_cal = totals['fat'] * 9
        c_cal = totals['carbs'] * 4
        total = p_cal + f_cal + c_cal

        if total == 0:
            self.menu.add(rumps.MenuItem("      No macros logged yet", callback=None))
            return

        bar_length = 20
        for emoji, cal in [("💪", p_cal), ("🥑", f_cal), ("🍞", c_cal)]:
            pct = (cal / total) * 100
            bar = "█" * int((pct / 100) * bar_length)
            self.menu.add(rumps.MenuItem(f"      {emoji} {bar} {pct:.0f}%", callback=None))

    def get_weekly_data(self):
        data = {k: [] for k in ['dates', 'calories', 'protein', 'fat', 'carbs', 'sugar', 'fiber', 'sodium']}
        today = datetime.now().date()
        for i in range(7):
            d = today - timedelta(days=6 - i)
            logs = self.db.get_daily_log(d.isoformat())
            daily = {k: 0 for k in ['calories', 'protein', 'fat', 'carbs', 'sugar', 'fiber', 'sodium']}
            for log in logs:
                for key in daily:
                    daily[key] += log.get(key, 0)
            data['dates'].append(d.strftime('%a'))
            for key in daily:
                data[key].append(daily[key])
        return data

    # ─────────────────────────────────────────────────────────
    # FOOD LOGGING
    # ─────────────────────────────────────────────────────────

    def show_input(self, _):
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
        try:
            rumps.notification(title="Processing...", subtitle=text, message="AI is analysing")
            result = self.tracker.log_meal(text)

            if result['status'] == 'success':
                self.refresh_menu()
                summary = self.tracker.get_summary()
                cals = int(summary['totals']['calories'])
                rumps.notification(
                    title="✅ Logged Successfully",
                    subtitle=text,
                    message=f"Total today: {cals} kcal"
                )
            elif result['status'] == 'clarification_needed':
                rumps.alert(title="🤔 Need More Info", message=result['message'])
            else:
                rumps.alert(title="❌ Error", message=result.get('message', 'Failed to log meal'))
        except Exception as e:
            rumps.alert(title="❌ Error", message=f"Something went wrong: {str(e)}")

    # ─────────────────────────────────────────────────────────
    # NOTIFICATIONS
    # ─────────────────────────────────────────────────────────

    def check_and_notify(self, _):
        if not self.settings.get("reminders_enabled"):
            return

        now = datetime.now()
        today_str = now.date().isoformat()
        summary = self.tracker.get_summary()
        cals = summary['totals']['calories']
        cal_goal = self.settings.get("calorie_goal")

        # ── Meal reminder (time since last meal) ──────────────
        interval_h = self.settings.get("reminder_interval_hours")
        last_meal_dt = self.db.get_last_meal_time(today_str)

        if last_meal_dt:
            hours_since = (now - last_meal_dt).total_seconds() / 3600
            already_notified = (
                self._last_meal_reminder_dt is not None
                and (now - self._last_meal_reminder_dt).total_seconds() / 3600 < interval_h
            )
            if hours_since >= interval_h and not already_notified:
                rumps.notification(
                    title="🍽️ Meal Reminder",
                    subtitle=f"{int(hours_since)}h since your last meal",
                    message=f"Today: {int(cals)} / {cal_goal} kcal logged"
                )
                self._last_meal_reminder_dt = now

        # ── Evening nudge (7pm, <50% of goal) ────────────────
        if now.hour >= 19 and self._evening_nudge_sent_date != today_str:
            if cal_goal and cals < cal_goal * 0.5:
                rumps.notification(
                    title="📊 Daily Check-in",
                    subtitle="You're well under your calorie goal",
                    message=f"{int(cals)} / {cal_goal} kcal — remember to eat enough!"
                )
            self._evening_nudge_sent_date = today_str

        # ── Weekly summary (Monday 9am) ───────────────────────
        if now.weekday() == 0 and now.hour == 9 and self._weekly_summary_sent_date != today_str:
            weekly_data = self.get_weekly_data()
            avg = sum(weekly_data['calories']) / 7
            rumps.notification(
                title="📈 Weekly Summary",
                subtitle=f"Last 7 days avg: {int(avg)} kcal/day",
                message=f"Your goal is {cal_goal} kcal/day"
            )
            self._weekly_summary_sent_date = today_str

    # ─────────────────────────────────────────────────────────
    # SUBWINDOWS (all launched as subprocesses)
    # ─────────────────────────────────────────────────────────

    def show_settings(self, _):
        try:
            subprocess.Popen([sys.executable, "app/ui/settings_window.py"])
        except Exception as e:
            rumps.alert(title="Error", message=f"Could not open settings: {e}")

    def show_export(self, _):
        try:
            subprocess.Popen([sys.executable, "app/ui/export.py"])
        except Exception as e:
            rumps.alert(title="Error", message=f"Could not open export: {e}")

    def show_charts(self, _):
        cal_goal = self.settings.get("calorie_goal")
        chart_script = f'''
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import sys, os

sys.path.append(os.getcwd())
from app.core.database import FoodDatabase

db = FoodDatabase("data/nutrition.db")
GOAL = {cal_goal}

data = {{'dates': [], 'calories': [], 'protein': [], 'fat': [], 'carbs': [], 'sugar': [], 'fiber': [], 'sodium': []}}
today = datetime.now().date()
for i in range(7):
    date = today - timedelta(days=6-i)
    logs = db.get_daily_log(date.isoformat())
    totals = {{k: 0 for k in ['calories','protein','fat','carbs','sugar','fiber','sodium']}}
    for log in logs:
        for key in totals: totals[key] += log.get(key, 0)
    data['dates'].append(date.strftime('%a'))
    for key in ['calories','protein','fat','carbs','sugar','fiber','sodium']:
        data[key].append(totals[key])

today_logs = db.get_daily_log(today.isoformat())

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
fig.patch.set_facecolor('#F5F5F5')
fig.suptitle('Nutrition Dashboard', fontsize=18, fontweight='bold')

bars = ax1.bar(data['dates'], data['calories'], color='#3498DB', alpha=0.8)
ax1.axhline(y=GOAL, color='#E74C3C', linestyle='--', linewidth=2, label=f'Goal ({{GOAL}})')
ax1.set_title('Weekly Calorie Intake', fontweight='bold')
ax1.set_ylabel('Calories (kcal)')
ax1.legend()
ax1.grid(axis='y', alpha=0.3)
for bar in bars:
    h = bar.get_height()
    if h > 0:
        ax1.text(bar.get_x()+bar.get_width()/2., h, f'{{int(h)}}', ha='center', va='bottom', fontsize=9)

macro_totals = {{
    'Protein': sum(log.get('protein',0)*4 for log in today_logs),
    'Fat':     sum(log.get('fat',0)*9 for log in today_logs),
    'Carbs':   sum(log.get('carbs',0)*4 for log in today_logs),
}}
if sum(macro_totals.values()) > 0:
    colors = ['#E74C3C','#F39C12','#3498DB']
    wedges, texts, autotexts = ax2.pie(macro_totals.values(), labels=macro_totals.keys(),
        colors=colors, autopct='%1.1f%%', startangle=90)
    for at in autotexts:
        at.set_color('white'); at.set_fontweight('bold')
else:
    ax2.text(0.5, 0.5, 'No data yet', ha='center', va='center', fontsize=12)
ax2.set_title("Today\'s Macro Split", fontweight='bold')

if sum(data['protein']) > 0:
    ax3.stackplot(data['dates'], data['protein'], data['fat'], data['carbs'],
        labels=['Protein','Fat','Carbs'], colors=['#E74C3C','#F39C12','#3498DB'], alpha=0.7)
    ax3.legend(loc='upper left')
else:
    ax3.text(0.5, 0.5, 'No data yet', ha='center', va='center', fontsize=12)
ax3.set_title('Weekly Macro Trends', fontweight='bold')
ax3.set_ylabel('Grams')
ax3.grid(axis='y', alpha=0.3)

total_cals = sum(log.get('calories',0) for log in today_logs)
pct = min((total_cals / GOAL) * 100, 150) if GOAL else 0
color = '#2ECC71' if pct <= 100 else '#E74C3C'
ax4.barh(['Progress'], [min(pct,100)], height=0.5, color=color, alpha=0.8)
if pct > 100:
    ax4.barh(['Progress'], [pct-100], left=100, height=0.5, color='#E74C3C', alpha=0.5)
ax4.set_xlim(0, 150)
ax4.set_xlabel('Percentage of Goal')
ax4.set_yticks([])
ax4.text(75, 0, f'{{int(total_cals)}} / {{GOAL}} kcal\\n{{pct:.1f}}%',
    ha='center', va='center', fontsize=11, fontweight='bold')
ax4.set_title("Today\'s Calorie Progress", fontweight='bold')

plt.tight_layout()

# Bring window to front
mgr = plt.get_current_fig_manager()
mgr.window.lift()
mgr.window.attributes("-topmost", True)
mgr.window.after(500, lambda: mgr.window.attributes("-topmost", False))
mgr.window.focus_force()

plt.show()
'''
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(chart_script)
                script_path = f.name
            subprocess.Popen([sys.executable, script_path])
        except Exception as e:
            rumps.alert(title="Chart Error", message=f"Failed to open charts: {str(e)}")

    # ─────────────────────────────────────────────────────────
    # REFRESH
    # ─────────────────────────────────────────────────────────

    def manual_refresh(self, _):
        self.refresh_menu()
        rumps.notification(title="Refreshed", subtitle="", message="All data updated")

    def auto_refresh(self, _):
        self.refresh_menu()


if __name__ == "__main__":
    CalorieMenuBarComplete().run()
