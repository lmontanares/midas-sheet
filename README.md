# Financial Management System (v3.3)

This project implements a personal financial management system consisting of several main components:

1.  A Telegram bot to interact with users.
2.  Integration with Google Sheets to store and manage financial data.
3.  OAuth 2.0 authentication for secure access to the user's own spreadsheets.
4.  **SQLite Database (v3.2)** to store encrypted tokens, selected sheets, and custom categories.
5.  **User-specific custom category management system (v3.3)**.

## Requirements

-   Python 3.13+
-   Telegram bot token (obtained via [@BotFather](https://t.me/botfather))
-   Google Cloud Platform OAuth 2.0 credentials
-   A Fernet encryption key to securely store tokens

## Key Features

-   **OAuth 2.0 Authentication**: Each user securely accesses their own Google Sheets.
-   **Persistent SQLite Storage (v3.2)**: Securely saves user settings (selected sheet) and credentials across restarts.
-   **Encrypted Tokens (v3.2)**: Secure storage of OAuth credentials in the database using Fernet cryptography.
-   **User-Specific Custom Categories (v3.3)**: Each user can define, edit, and use their own income and expense categories.
-   **Guided Flow**: Intuitive interface with buttons for logging transactions and managing categories.
-   **Modular Architecture**: Clean design with separation of concerns (auth, bot, db, sheets, etc.).
-   **Modern Static Typing**: Full use of Python 3.9+ typing features for enhanced robustness and clarity.

## Installation

### 1. Clone the repository

```bash
git clone <repository>
cd finanzas
```

### 2. Create and activate virtual environment

Using the `uv` package manager:

```bash
uv venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

### 3. Install dependencies

```bash
uv pip install -r requirements.txt
```

For development:

```bash
uv pip install -e ".[dev]"
```

### 4. Configure environment variables

Copy the example file and fill in the actual values:

```bash
cp .env.example .env
```

Edit the `.env` file with the following values:
-   Telegram bot token (`TELEGRAM_TOKEN`).
-   Path to the OAuth 2.0 credentials file downloaded from Google Cloud Console (`OAUTH_CREDENTIALS_PATH`). By default, `oauth_credentials.json` is expected in the project root.
-   Host and port where the local OAuth server will run (`OAUTH_SERVER_HOST`, `OAUTH_SERVER_PORT`). Defaults to `localhost` and `8000`.
-   Redirect URI configured in Google Cloud Console (`OAUTH_REDIRECT_URI`). Must match the local server configuration (e.g., `http://localhost:8000/oauth2callback`).
-   Fernet encryption key to secure stored OAuth tokens (`OAUTH_ENCRYPTION_KEY`). See the next section to generate it.
-   Database connection URL (`DATABASE_URL`). Defaults to SQLite (`sqlite:///./finanzas.db`).
-   Desired logging level (`LOG_LEVEL`). Defaults to `INFO`.

### 5. Generate Fernet encryption key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the generated key into the `OAUTH_ENCRYPTION_KEY` variable in the `.env` file.

### 6. Configure OAuth in Google Cloud Platform

1.  Create a project in [Google Cloud Platform](https://console.cloud.google.com/)
2.  Enable the Google Sheets and Google Drive APIs
3.  Create OAuth 2.0 credentials for a web application
4.  Add Redirect URI: `http://localhost:8000/oauth2callback` (or your configured host/port)
5.  Download the JSON credentials and save them as `oauth_credentials.json`

## Project Structure

```
/finanzas/
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
│
├── docs/                 # Documentation
│   └── handover.md       # Detailed handover document
│
├── main.py               # Main entry point
├── pyproject.toml        # Project configuration and dependencies
├── pytest.ini            # Pytest configuration
├── .env.example          # Example environment variables
├── .gitignore            # Files ignored by Git
└── README.md             # This documentation

# Note: Files like .env, finanzas.db, oauth_credentials.json are local
# and should not be included in version control.
```

## Available Commands

The bot implements the following commands:

-   `/start`: Starts interaction with the bot
-   `/help`: Shows help about available commands
-   `/auth`: Starts the OAuth authentication process
-   `/sheet`: Selects a specific spreadsheet
-   `/logout`: Logs out and revokes access
-   `/agregar`: Adds a new expense or income with custom categories
-   `/categorias`: Shows the user's current categories
-   `/editarcat`: Provides options to edit categories (YAML)
-   `/resetcat`: Resets the user's categories to default values
-   `/recargar`: Reloads data from the server

## Transaction Logging

The transaction logging flow (`/agregar`) follows these steps:

1.  Select transaction type (income or expense)
2.  Select category (**from the user's custom list**)
3.  Select subcategory for expenses (**from the custom list**)
4.  Enter the amount
5.  Option to add comments (Yes/No)
6.  Log to the corresponding spreadsheet

## Custom Category Management

Users can customize their categories using:

-   **View categories**: `/categorias` command shows current categories
-   **Edit categories**: `/editarcat` command allows importing/exporting YAML files
-   **Reset categories**: `/resetcat` command reverts to default categories

## Usage

To start the application:

```bash
python main.py
```

## Tests

### Running Tests

To run all tests:

```bash
pytest
```

To check coverage:

```bash
pytest --cov=src tests/
```

You can also use the scripts defined in `pyproject.toml` (if they exist) with `uv`:

```bash
# Assuming they are defined in [tool.uv.scripts]
uv run test
uv run lint
```

## Development

### Code Conventions

-   Follow PEP 8
-   Use modern Python 3.9+ typing features
-   Document all public functions and methods
-   Write tests for new functionality
-   For architectural details and design decisions, consult `docs/handover.md`.

### Development Tools

-   ruff: Linter and formatter
-   pytest: Testing framework
-   vulture: Dead code detection

## License

This project is licensed under the MIT License.
