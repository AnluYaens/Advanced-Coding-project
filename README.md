💰 AI Budget Tracker
An advanced budget tracking application with integrated AI assistant, interactive visualizations, and intelligent expense management.

✨ Features

🤖 AI Assistant – Log expenses in natural language using Google Gemini
📊 Interactive Visualizations – Line and donut charts for expense analysis
💱 Currency Converter – Real-time exchange rates
📄 Automatic Import – Reads CSV and PDF bank statements
💾 Local Database – SQLite with SQLAlchemy ORM
🎨 Modern Interface – Dark-themed design with CustomTkinter

📋 Prerequisites

* Python 3.11 (exact version required)
* pip (Python package manager)
* Google AI Studio account to obtain API key

🚀 Installation

1. Clone the repository

```bash
git clone https://github.com/yourusername/ai-budget-tracker.git
cd ai-budget-tracker
```

2. Create a virtual environment with Python 3.11

```bash
# Make sure Python 3.11 is installed
py -3.11 --version

# Create environment
py -3.11 -m venv venv311

# Activate on Windows
venv311\Scripts\activate

# Activate on macOS/Linux
source venv311/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Configure environment variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key
# Windows: notepad .env
# macOS/Linux: nano .env
```

5. Obtain Google Gemini API Key

* Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
* Sign in or create an account
* Generate a new API key
* Copy the key and paste it into your `.env` file:

```
GOOGLE_API_KEY=your_api_key_here
```

6. Run the application

```bash
python main.py
```

🎮 Usage

#### AI Assistant Commands

The assistant understands natural commands like:

* "Record a \$50 expense for groceries"
* "Add \$120 for electronics, it was headphones"
* "How much have I spent on entertainment?"
* "Delete the expense with ID 5"

#### Main Features

* **Add Expense**: Register new expenses with category and description
* **Expense Analysis**: View detailed summaries and charts
* **Set Budget**: Define monthly limits per category
* **Import Statements**: Load CSV or PDF files automatically

#### CSV Import Format

CSV files must contain the following columns:

```csv
Date,Category,Description,Amount
2024-01-15,Groceries,Supermarket,50.00
2024-01-16,Entertainment,Cinema,25.00
```

🛠️ Troubleshooting

**Error: "Missing GOOGLE\_API\_KEY"**

* Make sure you created a `.env` file (not just `.env.example`)
* Verify the API key is correctly pasted

**PDF Import Error**

* Install `pdfplumber` if not already installed: `pip install pdfplumber`

**App won’t start**

* Ensure you are using **Python 3.11** (not 3.12+ or 3.10)
* Check that the virtual environment is activated (`venv311`)
* Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

📁 Project Structure

```
Advanced Coding project/
├── src/
│   ├── core/
│   │   ├── database.py            # Database handling
│   │   ├── models.py              # SQLAlchemy models
│   │   └── ai_engine.py           # Gemini AI integration
│   ├── services/
│   │   ├── bank_statement_loader.py     # CSV importer
│   │   ├── bank_statement_loader_pdf.py # PDF importer
│   │   └── currency_api.py              # Exchange rate API
│   └── ui/
│       └── interface_ctk.py       # GUI interface
├── alembic/                       # DB migrations
├── main.py                        # Entry point
├── requirements.txt               # Dependencies
├── README.md                      # This file
└── .env                           # Configuration (created from example)
```

🔒 Security

* API keys are stored in local `.env` files (never pushed to GitHub)
* Database is local (SQLite by default)
* Only external services used:

  * Google Gemini (for AI)
  * Exchange rate API (for currency conversion)

🤝 Contributing
Contributions are welcome! Please:

* Fork the project
* Create a feature branch: `git checkout -b feature/NewFeature`
* Commit your changes: `git commit -m 'Add new feature'`
* Push your branch: `git push origin feature/NewFeature`
* Open a Pull Request

📄 License
This project is licensed under the MIT License. See the LICENSE file for details.

🙏 Acknowledgments

* CustomTkinter – Modern UI toolkit
* Google Gemini – Natural language AI
* Matplotlib – Charts and visualizations
* SQLAlchemy – Database ORM

📞 Support
If you encounter issues or have suggestions:

* Open an issue on GitHub
* Contact the developer
