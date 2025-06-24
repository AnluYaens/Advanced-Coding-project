# 💰 AI Budget Tracker

![Budget Assistant banner](src/assets/icons/Budget_Tracker_Assistant.png)

## ✨ Features

* 🤖 **AI Assistant** – Log expenses in natural language using Google Gemini.
* 📊 **Interactive Visualizations** – Line and donut charts for expense analysis.
* 💱 **Currency Converter** – Real-time exchange rates.
* 📄 **Automatic Import** – Reads CSV and PDF bank statements.
* 📀 **Local Database** – SQLite with SQLAlchemy ORM.
* 🎨 **Modern Interface** – Dark-themed design with CustomTkinter.
* 🏗️ **Modular Architecture** – Clean, maintainable code structure with reusable components.

## 📋 Prerequisites

* Python 3.11 (exact version required)
* pip (Python package manager)
* Google AI Studio account to obtain API key

## 🚀 Installation

**1. Clone the repository**

```bash
git clone https://github.com/yourusername/ai-budget-tracker.git
cd ai-budget-tracker
```

**2. Create a virtual environment with Python 3.11**

```bash
# Verify Python 3.11 installation
py -3.11 --version

# Create virtual environment
py -3.11 -m venv .venv

# Activate on Windows
.venv\Scripts\activate

# Activate on macOS/Linux
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Configure Environment Variables**

Create a `.env` file (you can copy from `.env.example`) and fill in the required values:

```env
# Google Gemini API Key
GOOGLE_API_KEY=your_google_api_key_here

# Optional: Exchange Rate API (https://app.exchangerate-api.com/)
EXCHANGE_API_KEY=your_exchange_api_key_here

# App Configuration
DEBUG=False
LOG_LEVEL=INFO

# Database connection (default is SQLite, leave commented)
# DATABASE_URL=sqlite:///./budget_tracker.db
# DATABASE_URL=postgresql://user:password@localhost/budget_db
```

Register for free API keys:

* [Google Gemini](https://aistudio.google.com/app/apikey)
* [Exchange rate API](https://app.exchangerate-api.com/sign-up)

**5. Run the application**

```bash
python -m src.main
```

## 🎮 Usage

### AI Assistant Commands

The assistant understands commands like:

* "Record a \$50 expense for groceries"
* "Add \$120 for electronics, it was headphones"
* "How much have I spent on entertainment?"
* "Delete the expense with ID 5"


### Main Features

* **Add Expense**: Register new expenses with category and description.
* **Expense Analysis**: View detailed summaries and charts.
* **Set Budget**: Define monthly limits per category.
* **Import Statements**: Automatically load CSV or PDF files.
* **AI Insights**: Get intelligent spending recommendations and predictions.
* **Currency Converter**: Convert between multiple currencies with real-time rates.

### CSV Import Format

CSV files must have:

```csv
Date,Category,Description,Amount
2024-01-15,Groceries,Supermarket,50.00
2024-01-16,Entertainment,Cinema,25.00
```

## 🛠️ Troubleshooting

**Missing GOOGLE\_API\_KEY**

* Ensure `.env` exists and has the correct API key.

**PDF Import Error**

* Install `pdfplumber`: `pip install pdfplumber`

**App won’t start**

* Use Python 3.11 specifically.
* Activate virtual environment (`.venv`).
* Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

## 📁 Project Structure

```
Advanced Coding project/
├── src/
│   ├── __init__.py
│   ├── main.py                         # Entry point
│   ├── assets/
│   │   └── icons/                      # UI icons
│   │       ├── add_expense.png
│   │       ├── ai_insights.png
│   │       ├── all_transactions.png
│   │       ├── analytics.png
│   │       ├── contact.png
│   │       ├── currency.png
│   │       ├── dashboard.png
│   │       └── set_budget.png
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py                 # Database handling
│   │   ├── models.py                   # SQLAlchemy models
│   │   └── ai_engine.py                # Gemini AI integration
│   ├── services/
│   │   ├── __init__.py
│   │   ├── bank_statement_loader.py    # CSV importer
│   │   ├── bank_statement_loader_pdf.py # PDF importer
│   │   └── currency_api.py             # Exchange rate API
│   └── ui/
│       ├── __init__.py
│       ├── main_app.py                 # Main application controller
│       ├── config/                     # UI configuration
│       │   ├── __init__.py
│       │   ├── theme.py                # Color palette & themes
│       │   └── typography.py           # Font system
│       ├── components/                 # Reusable UI components
│       │   ├── __init__.py
│       │   ├── buttons.py              # Button components
│       │   ├── cards.py                # Card components
│       │   ├── charts.py               # Chart visualizations
│       │   ├── indicators.py           # Loading indicators
│       │   ├── sidebar.py              # Navigation sidebar
│       │   └── widgets.py              # Complex widgets
│       ├── utils/                      # UI utilities
│       │   ├── __init__.py
│       │   └── helpers.py              # Helper functions
│       └── views/                      # Application views
│           ├── __init__.py
│           ├── dashboard.py            # Dashboard view
│           ├── expenses.py             # Add expense & transactions
│           ├── analytics.py            # Analytics view
│           ├── insights.py             # AI insights view
│           ├── budget.py               # Budget management
│           ├── currency.py             # Currency converter
│           └── contact.py              # About/contact view
├── requirements.txt                    # Dependencies
├── README.md                           # This file
├── .env                                # Configuration (created from example)
├── .gitignore                          # Ignored files
└── budget_tracker.db                   # SQLite database
```

## 🏗️ Architecture Overview

The application follows a **modular MVC architecture** with clean separation of concerns:

### **UI Layer** (`src/ui/`)
- **Config**: Centralized theme and typography configuration
- **Components**: Reusable UI components (buttons, cards, charts, etc.)
- **Views**: Feature-specific views following a consistent pattern
- **Utils**: Shared helper functions

### **Business Logic** (`src/core/`)
- **Models**: SQLAlchemy ORM models
- **Database**: Database connection and session management
- **AI Engine**: Google Gemini integration

### **Services** (`src/services/`)
- **Bank Statement Loaders**: CSV and PDF import functionality
- **Currency API**: Real-time exchange rates

### Key Benefits:
- ✅ **Maintainable**: Average file size ~150-200 lines
- ✅ **Scalable**: Easy to add new features
- ✅ **Testable**: Components can be tested in isolation
- ✅ **Performance**: Proper resource management and cleanup

## 🔒 Security

* API keys stored locally, not committed.
* SQLite database stored locally.
* Environment variables for sensitive configuration.

## 🤝 Contributing

Contributions welcome! Follow these steps:

* Fork the project.
* Create branch: `git checkout -b feature/NewFeature`
* Commit changes: `git commit -m 'Add new feature'`
* Push branch: `git push origin feature/NewFeature`
* Open a Pull Request.

### Development Guidelines:
- Follow the existing modular architecture
- Create reusable components when possible
- Add appropriate documentation
- Test your changes thoroughly

## 📄 License

Licensed under the MIT License.

## 🙏 Acknowledgments

* CustomTkinter – Modern UI toolkit
* Google Gemini – Natural language AI
* Matplotlib – Charts and visualizations
* SQLAlchemy – Database ORM
* Pdfplumber – PDF parsing
* ExchangeRate-API – Currency conversion

## 📞 Support

* Open an issue on GitHub.
* Contact the developer directly.

---

**Made by Angel Jaen**