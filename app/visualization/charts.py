import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from datetime import datetime, timedelta
from typing import Dict, List
import sys
import os

sys.path.append(os.getcwd())
from app.core.database import FoodDatabase
from app.core.settings import SettingsManager


class NutritionVisualizer:
    def __init__(self, db: FoodDatabase, settings: SettingsManager = None):
        self.db = db
        self.settings = settings or SettingsManager()

    def get_weekly_data(self) -> Dict[str, List]:
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

    def show_dashboard(self):
        root = tk.Tk()
        root.title("📊 Nutrition Dashboard")
        root.geometry("1200x800")

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
        fig.patch.set_facecolor('#F5F5F5')

        weekly_data = self.get_weekly_data()
        today_data = self.db.get_daily_log(datetime.now().date().isoformat())

        self._plot_weekly_calories(ax1, weekly_data)
        self._plot_macro_pie(ax2, today_data)
        self._plot_weekly_macros(ax3, weekly_data)
        self._plot_daily_progress(ax4, today_data)

        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=root)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        tk.Button(
            root,
            text="Refresh Data",
            command=lambda: self._refresh_charts(canvas, fig),
            bg="#3498DB",
            fg="white",
            font=("Helvetica", 12),
            padx=20,
            pady=10,
        ).pack(pady=10)

        root.mainloop()

    def _plot_weekly_calories(self, ax, data):
        goal = self.settings.get("calorie_goal")
        bars = ax.bar(data['dates'], data['calories'], color='#3498DB', alpha=0.8)
        ax.axhline(y=goal, color='#E74C3C', linestyle='--', linewidth=2, label=f'Goal ({goal})')
        ax.set_title('Weekly Calorie Intake', fontsize=14, fontweight='bold')
        ax.set_ylabel('Calories (kcal)', fontsize=11)
        ax.set_ylim(0, max(data['calories'] + [goal]) * 1.1)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2., h, f'{int(h)}',
                        ha='center', va='bottom', fontsize=9)

    def _plot_macro_pie(self, ax, today_logs):
        totals = {'Protein': 0, 'Fat': 0, 'Carbs': 0}
        for log in today_logs:
            totals['Protein'] += log.get('protein', 0) * 4
            totals['Fat'] += log.get('fat', 0) * 9
            totals['Carbs'] += log.get('carbs', 0) * 4

        if sum(totals.values()) == 0:
            totals = {'Protein': 1, 'Fat': 1, 'Carbs': 1}

        ax.pie(
            totals.values(),
            labels=totals.keys(),
            colors=['#E74C3C', '#F39C12', '#3498DB'],
            autopct='%1.1f%%',
            startangle=90,
            explode=(0.05, 0.05, 0.05),
        )
        ax.set_title("Today's Macro Split (by calories)", fontsize=14, fontweight='bold')

    def _plot_weekly_macros(self, ax, data):
        if sum(data['protein']) > 0:
            ax.stackplot(
                data['dates'],
                data['protein'], data['fat'], data['carbs'],
                labels=['Protein', 'Fat', 'Carbs'],
                colors=['#E74C3C', '#F39C12', '#3498DB'],
                alpha=0.7,
            )
            ax.legend(loc='upper left')
        else:
            ax.text(0.5, 0.5, 'No data yet', ha='center', va='center', fontsize=12)
        ax.set_title('Weekly Macro Trends', fontsize=14, fontweight='bold')
        ax.set_ylabel('Grams', fontsize=11)
        ax.grid(axis='y', alpha=0.3)

    def _plot_daily_progress(self, ax, today_logs):
        goal = self.settings.get("calorie_goal")
        total_cals = sum(log.get('calories', 0) for log in today_logs)
        percentage = min((total_cals / goal) * 100, 100) if goal else 0

        color = '#2ECC71' if percentage <= 100 else '#E74C3C'
        ax.barh(0, percentage, height=0.3, color=color)
        ax.barh(0, 100 - percentage, left=percentage, height=0.3, color='#ECF0F1')
        ax.set_xlim(0, 100)
        ax.set_ylim(-0.5, 0.5)
        ax.axis('off')
        ax.text(50, 0, f'{int(total_cals)} / {goal}\n{percentage:.0f}%',
                ha='center', va='center', fontsize=20, fontweight='bold')
        ax.set_title("Today's Progress", fontsize=14, fontweight='bold', pad=20)

    def _refresh_charts(self, canvas, fig):
        for ax in fig.get_axes():
            ax.clear()
        weekly_data = self.get_weekly_data()
        today_data = self.db.get_daily_log(datetime.now().date().isoformat())
        axes = fig.get_axes()
        self._plot_weekly_calories(axes[0], weekly_data)
        self._plot_macro_pie(axes[1], today_data)
        self._plot_weekly_macros(axes[2], weekly_data)
        self._plot_daily_progress(axes[3], today_data)
        canvas.draw()


if __name__ == "__main__":
    db = FoodDatabase("data/nutrition.db")
    viz = NutritionVisualizer(db)
    viz.show_dashboard()
