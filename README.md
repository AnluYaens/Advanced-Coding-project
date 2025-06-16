# 💰 AI Budget Tracker

**An advanced budget tracking application with integrated AI assistant, interactive visualizations, and intelligent expense management.**

## ✨ Features

* 🤖 **AI Assistant** – Log expenses in natural language using Google Gemini.
* 📊 **Interactive Visualizations** – Line and donut charts for expense analysis.
* 💱 **Currency Converter** – Real-time exchange rates.
* 📄 **Automatic Import** – Reads CSV and PDF bank statements.
* 📀 **Local Database** – SQLite with SQLAlchemy ORM.
* 🎨 **Modern Interface** – Dark-themed design with CustomTkinter.

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
py -3.11 -m venv venv311

# Activate on Windows
venv311\Scripts\activate

# Activate on macOS/Linux
source venv311/bin/activate
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
* Activate virtual environment (`venv311`).
* Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

## 📁 Project Structure

```
Advanced Coding project/
🔼️ src/
   🔼️ __init__.py
   🔼️ main.py # Entry point
   🔼️ core/
       🔼️ __init__.py
       🔼️ database.py # Database handling
       🔼️ models.py # SQLAlchemy models
       🔼️ ai_engine.py # Gemini AI integration
   🔼️ services/
       🔼️ __init__.py
       🔼️ bank_statement_loader.py # CSV importer
       🔼️ bank_statement_loader_pdf.py # PDF importer
       🔼️ currency_api.py # Exchange rate API
   🔼️ ui/
       🔼️ __init__.py
       🔼️ interface_ctk.py # GUI interface
🔼️ requirements.txt # Dependencies
🔼️ README.md # This file
🔼️ .env # Configuration (created from example)
🔼️ .gitignore # Ignored files
🔼️ budget_tracker.db # SQLite database
🔼️ budget_tracker.db-wal / .db-shm # SQLite WAL files
```

## 🔒 Security

* API keys stored locally, not committed.
* SQLite database stored locally.

## 🤝 Contributing

Contributions welcome! Follow these steps:

* Fork the project.
* Create branch: `git checkout -b feature/NewFeature`
* Commit changes: `git commit -m 'Add new feature'`
* Push branch: `git push origin feature/NewFeature`
* Open a Pull Request.

## 📄 License

Licensed under the MIT License.

## 🙏 Acknowledgments

* CustomTkinter – Modern UI toolkit
* Google Gemini – Natural language AI
* Matplotlib – Charts and visualizations
* SQLAlchemy – Database ORM

## 📞 Support

* Open an issue on GitHub.
* Contact the developer directly.
