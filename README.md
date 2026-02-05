# 🍽️ AI Calorie Tracker - macOS Menu Bar Edition

An intelligent calorie tracking app that lives in your macOS menu bar, powered by local AI.

## ✨ Features

- **🎯 Smart Food Recognition**: Natural language parsing (e.g., "Matsuya Beef Bowl regular")
- **📊 Beautiful Visualizations**: Weekly trends, macro breakdowns, progress tracking
- **⚡ Menu Bar Integration**: Quick access from your macOS top bar
- **🤖 AI-Powered**: Uses Ollama for intelligent food parsing and estimation
- **🗄️ Rich Database**: Pre-loaded with Japanese restaurant menus (Matsuya, Sukiya)
- **🌐 OpenFoodFacts**: Fallback to global food database

## 🚀 Quick Start

### Prerequisites

1. **Python 3.9+**
2. **Ollama** - [Download here](https://ollama.ai)
   ```bash
   # Install and pull the model
   ollama pull llama3.2:1b
   ```

### Installation

```bash
# Clone the repo
git clone <your-repo>
cd ai-calorie-tracker

# Install dependencies
pip install -r requirements.txt
```

### Run the App

**Menu Bar App (macOS):**
```bash
python menubar_app.py
```

**Desktop GUI (Cross-platform):**
```bash
python desktop_app.py
```

**Charts Only:**
```bash
python app/visualization/charts.py
```

## 📱 Usage

### Menu Bar App

1. Click the 🍽️ icon in your menu bar
2. Select "Quick Log" to add food
3. Type naturally: "2 eggs and toast" or "Sukiya beef bowl large"
4. View stats in the dropdown
5. Click "View Chart" for detailed visualization

### Chart Dashboard

The visualization window shows:
- **Weekly Calories**: Bar chart with goal line
- **Today's Macros**: Pie chart (by calorie contribution)
- **Weekly Macro Trends**: Stacked area chart
- **Daily Progress**: Gauge showing progress to 2000 kcal goal

## 🎨 Customization

### Change Daily Calorie Goal

Edit `menubar_app.py`:
```python
progress_text = f"📊 {int(totals['calories'])} / 2500 kcal\n"  # Change 2000 to your goal
```

### Add Custom Foods

```python
from app.core.database import FoodDatabase

db = FoodDatabase("data/nutrition.db")
db.add_food({
    'name': 'my custom meal',
    'calories': 450,
    'protein': 30,
    'fat': 15,
    'carbs': 40,
    'source': 'manual'
})
```

### Styling Charts

Edit colors in `app/visualization/charts.py`:
```python
colors = ['#E74C3C', '#F39C12', '#3498DB']  # Protein, Fat, Carbs
```

## 🏗️ Architecture

```
ai-calorie-tracker/
├── app/
│   ├── ai/
│   │   └── engine.py          # Ollama AI integration
│   ├── core/
│   │   ├── database.py        # SQLite operations
│   │   └── tracker.py         # Main logging logic
│   ├── services/
│   │   └── off.py             # OpenFoodFacts API
│   └── visualization/
│       └── charts.py          # Matplotlib dashboards
├── data/
│   ├── nutrition.db           # SQLite database
│   └── nutrition.json         # Pre-loaded Japanese food data
├── menubar_app.py             # macOS menu bar app (rumps)
├── desktop_app.py             # Cross-platform GUI (toga)
└── requirements.txt
```

## 🛠️ Advanced Features

### Manual Override

When you know exact macros:
```
"450 calories, 30g protein, 15g fat, 40g carbs"
```

### Chain Restaurant Detection

The app recognizes chains and searches specifically:
```
"Matsuya" → searches Matsuya menu items only
"Sukiya beef bowl" → suggests sizes if ambiguous
```

### Fuzzy Matching

Typos are handled:
```
"mtsuya bef bowl" → finds "Matsuya Beef Bowl"
```

## 🐛 Troubleshooting

**"Model not found" error:**
```bash
ollama pull llama3.2:1b
```

**Charts won't open:**
```bash
pip install matplotlib tk
```

**Menu bar icon doesn't appear:**
- Ensure you're on macOS
- Grant accessibility permissions: System Settings → Privacy → Accessibility

## 🔮 Future Enhancements

- [ ] Export data to CSV/PDF
- [ ] Barcode scanner integration
- [ ] Photo-based food recognition
- [ ] Integration with Apple Health
- [ ] Multi-user support
- [ ] Custom meal templates
- [ ] Weekly/monthly reports

## 📄 License

MIT License - feel free to modify and distribute!

## 🙏 Credits

Built with:
- [Ollama](https://ollama.ai) - Local AI
- [rumps](https://github.com/jaredks/rumps) - macOS menu bar
- [Toga](https://beeware.org/project/projects/libraries/toga/) - Cross-platform GUI
- [OpenFoodFacts](https://world.openfoodfacts.org/) - Food database API
