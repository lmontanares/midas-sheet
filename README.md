# MidasSheet (v0.1 Beta)

A personal financial management system that helps you track expenses and income using a Telegram bot connected to your own Google Sheets.

![Version](https://img.shields.io/badge/version-0.1--beta-blue)
![Python](https://img.shields.io/badge/Python-3.13%2B-green)
![License](https://img.shields.io/badge/license-GPL--3.0-yellow)

## Overview

This project implements a personal financial management system consisting of:

1. A **Telegram bot** for easy access from any device
2. **Google Sheets integration** to store and manage your financial data
3. **OAuth 2.0 authentication** for secure access to your own spreadsheets
4. **SQLite Database** to store encrypted tokens and user preferences
5. **Custom category management** to personalize expense tracking

**Note**: This is a beta version (0.1) released for testing and feedback.

![System Architecture](https://via.placeholder.com/800x400?text=System+Architecture+Diagram)

## Key Features

- **OAuth 2.0 Authentication**: Securely access your own Google Sheets without sharing permissions
- **Encrypted Token Storage**: Secure token management using Fernet cryptography
- **Custom Categories**: Define your own income and expense categories
- **Guided Transaction Flow**: Intuitive interface with buttons for logging transactions
- **Multi-User Support**: Each user accesses their own spreadsheets and uses their own categories
- **Modern Type Hints**: Full use of Python 3.9+ typing features

## Screenshots

![Telegram Bot Interface](https://via.placeholder.com/300x600?text=Telegram+Bot+Interface)
![Category Management](https://via.placeholder.com/300x600?text=Category+Management)
![Transaction Flow](https://via.placeholder.com/300x600?text=Transaction+Flow)

## Getting Started

### Prerequisites

- Python 3.13+
- Telegram bot token (from [@BotFather](https://t.me/botfather))
- Google Cloud Platform OAuth 2.0 credentials
- [`uv` package manager](https://docs.astral.sh/uv/) (required)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/lmontanares/midas-sheet.git
   cd midas-sheet
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration values
   ```

3. Generate a Fernet encryption key:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   # Copy the output to OAUTH_ENCRYPTION_KEY in your .env file
   ```

4. Set up Google Cloud OAuth:
   - Create a project in [Google Cloud Platform](https://console.cloud.google.com/)
   - Enable Google Sheets and Google Drive APIs
   - Create OAuth 2.0 credentials for a web application
   - Add Redirect URI: `http://localhost:8000/oauth2callback` (or your configured host/port)
   - Download credentials and save as `oauth_credentials.json` in the project root

5. Run the application:
   ```bash
   uv run python main.py
   ```

   > Note: `uv run` automatically handles virtual environment creation, dependency installation, and activation.

6. Start interacting with your bot on Telegram!

## Bot Commands

- `/start` - Begin interaction with the bot
- `/help` - Display available commands and usage info
- `/auth` - Start the OAuth authentication process
- `/sheet` - Select a specific spreadsheet
- `/logout` - Revoke access and log out
- `/add` - Add a new expense or income
- `/categories` - View your current expense/income categories
- `/editcat` - Edit your categories (using YAML import/export)
- `/resetcat` - Reset categories to default values

## Transaction Flow

The transaction flow (`/add` command) follows these steps:

1. Select transaction type (income or expense)
2. Select category from your custom list
3. Select subcategory for expenses
4. Enter the amount
5. Optionally add comments
6. Transaction is recorded in your selected Google Sheet

## Category Management

Users can customize categories through:

- **View**: Use `/categories` to see current categories
- **Edit**: Use `/editcat` to import/export categories as YAML files
- **Reset**: Use `/resetcat` to revert to default categories

## Project Structure

```
/midas-sheet/
│
├── src/                  # Source code
│   ├── auth/             # OAuth 2.0 Authentication
│   ├── bot/              # Telegram bot logic
│   ├── config/           # Configurations and category management
│   ├── db/               # Database models and functions
│   ├── server/           # Server for OAuth redirects
│   ├── sheets/           # Google Sheets integration
│   └── utils/            # Common utilities
│
├── tests/                # Automated tests
├── docs/                 # Documentation
├── main.py               # Main entry point
├── pyproject.toml        # Project configuration
└── README.md             # This documentation
```

## Running Tests

```bash
uv run pytest
# or for coverage report
uv run pytest --cov=src tests/
```

## Development

### Code Conventions

- Follow PEP 8
- Use modern Python 3.9+ typing features
- Document all public functions and methods
- Write tests for new functionality

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.

## Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) library
- [gspread](https://github.com/burnash/gspread) for Google Sheets integration
- [SQLAlchemy](https://www.sqlalchemy.org/) for database ORM
- [cryptography](https://github.com/pyca/cryptography) for secure token storage

## Development Note

This project was developed with assistance from Large Language Models (LLMs), primarily [Claude](https://www.anthropic.com/claude) and [Gemini](https://gemini.google.com). LLMs were used for code generation, documentation writing, debugging assistance, and architectural guidance. All LLM-generated content has been reviewed and validated by human developers before inclusion in this project.