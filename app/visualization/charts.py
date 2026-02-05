import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from datetime import datetime, timedelta
from typing import Dict, List
import sys
import os

sys.path.append(os.getcwd())
from app.core.database import FoodDatabase

class NutritionVisualizer:
    def __init__(self, db: FoodDatabase):
        self.db = db
        
    def get_weekly_data(self) -> Dict[str, List]:
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
            
            data['dates'].append(date.strftime('%a'))  # Mon, Tue, etc.
            data['calories'].append(daily_totals['calories'])
            data['protein'].append(daily_totals['protein'])
            data['fat'].append(daily_totals['fat'])
            data['carbs'].append(daily_totals['carbs'])
        
        return data
    
    def show_dashboard(self):
        """Open a Tkinter window with multiple charts"""
        root = tk.Tk()
        root.title("Nutrition Dashboard")
        root.geometry("1200x800")
        
        # Create matplotlib figure with subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
        fig.patch.set_facecolor('#F5F5F5')
        
        # Get data
        weekly_data = self.get_weekly_data()
        today_data = self.db.get_daily_log(datetime.now().date().isoformat())
        
        # 1. Weekly Calories Bar Chart
        self._plot_weekly_calories(ax1, weekly_data)
        
        # 2. Today's Macro Breakdown (Pie Chart)
        self._plot_macro_pie(ax2, today_data)
        
        # 3. Weekly Macros (Stacked Area)
        self._plot_weekly_macros(ax3, weekly_data)
        
        # 4. Progress to Goal (Gauge-style)
        self._plot_daily_progress(ax4, today_data)
        
        plt.tight_layout()
        
        # Embed in Tkinter
        canvas = FigureCanvasTkAgg(fig, master=root)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add refresh button
        refresh_btn = tk.Button(
            root,
            text="Refresh Data",
            command=lambda: self._refresh_charts(canvas, fig),
            bg="#3498DB",
            fg="white",
            font=("SF Pro", 12),
            padx=20,
            pady=10
        )
        refresh_btn.pack(pady=10)
        
        root.mainloop()
    
    def _plot_weekly_calories(self, ax, data):
        """Bar chart of weekly calories"""
        bars = ax.bar(data['dates'], data['calories'], color='#3498DB', alpha=0.8)
        
        # Add goal line
        ax.axhline(y=2000, color='#E74C3C', linestyle='--', linewidth=2, label='Goal (2000)')
        
        # Styling
        ax.set_title('Weekly Calorie Intake', fontsize=14, fontweight='bold')
        ax.set_ylabel('Calories (kcal)', fontsize=11)
        ax.set_ylim(0, max(data['calories'] + [2000]) * 1.1)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2.,
                height,
                f'{int(height)}',
                ha='center',
                va='bottom',
                fontsize=9
            )
    
    def _plot_macro_pie(self, ax, today_logs):
        """Pie chart of today's macros"""
        totals = {'Protein': 0, 'Fat': 0, 'Carbs': 0}
        
        for log in today_logs:
            totals['Protein'] += log.get('protein', 0) * 4  # 4 cal/g
            totals['Fat'] += log.get('fat', 0) * 9  # 9 cal/g
            totals['Carbs'] += log.get('carbs', 0) * 4  # 4 cal/g
        
        if sum(totals.values()) == 0:
            totals = {'Protein': 1, 'Fat': 1, 'Carbs': 1}  # Avoid empty pie
        
        colors = ['#E74C3C', '#F39C12', '#3498DB']
        explode = (0.05, 0.05, 0.05)
        
        ax.pie(
            totals.values(),
            labels=totals.keys(),
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            explode=explode
        )
        ax.set_title("Today's Macro Split (by calories)", fontsize=14, fontweight='bold')
    
    def _plot_weekly_macros(self, ax, data):
        """Stacked area chart of weekly macros"""
        ax.fill_between(data['dates'], data['protein'], alpha=0.7, color='#E74C3C', label='Protein')
        ax.fill_between(data['dates'], data['protein'], 
                        [p+f for p, f in zip(data['protein'], data['fat'])],
                        alpha=0.7, color='#F39C12', label='Fat')
        ax.fill_between([p+f for p, f in zip(data['protein'], data['fat'])],
                        [p+f+c for p, f, c in zip(data['protein'], data['fat'], data['carbs'])],
                        alpha=0.7, color='#3498DB', label='Carbs')
        
        ax.set_title('Weekly Macro Trends', fontsize=14, fontweight='bold')
        ax.set_ylabel('Grams', fontsize=11)
        ax.legend(loc='upper left')
        ax.grid(axis='y', alpha=0.3)
    
    def _plot_daily_progress(self, ax, today_logs):
        """Gauge-style progress indicator"""
        total_cals = sum(log.get('calories', 0) for log in today_logs)
        goal = 2000
        percentage = min((total_cals / goal) * 100, 100)
        
        # Create semi-circle gauge
        theta = (percentage / 100) * 180
        
        ax.barh(0, percentage, height=0.3, color='#2ECC71' if percentage <= 100 else '#E74C3C')
        ax.barh(0, 100-percentage, left=percentage, height=0.3, color='#ECF0F1')
        
        ax.set_xlim(0, 100)
        ax.set_ylim(-0.5, 0.5)
        ax.axis('off')
        
        # Add text
        ax.text(
            50, 0,
            f'{int(total_cals)} / {goal}\n{percentage:.0f}%',
            ha='center',
            va='center',
            fontsize=20,
            fontweight='bold'
        )
        
        ax.set_title("Today's Progress", fontsize=14, fontweight='bold', pad=20)
    
    def _refresh_charts(self, canvas, fig):
        """Refresh all charts with new data"""
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


# Standalone test
if __name__ == "__main__":
    db = FoodDatabase("data/nutrition.db")
    viz = NutritionVisualizer(db)
    viz.show_dashboard()
