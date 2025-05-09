# MidasSheet - LLM Knowledge Document

## Project Summary
This document contains detailed information about MidasSheet, a personal finance application built with Python that uses a Telegram bot interface and Google Sheets integration. The system allows users to track expenses and income through a structured, categorized approach.

**Version**: 0.1 (Beta)
**License**: GNU General Public License v3.0
**Python Requirement**: 3.13+
**Type Hint System**: Uses Python 3.9+ typing features

## Key Components

1. **Telegram Bot Interface**: User-facing component built with python-telegram-bot v22.0
2. **Google Sheets Integration**: Data storage using gspread with OAuth 2.0
3. **OAuth 2.0 Authentication**: Secure access to user's own spreadsheets
4. **SQLite Database**: Local storage for encrypted tokens and user settings
5. **Custom Category System**: Personalized expense/income categories

## Architecture

The system follows a modular design with the following flow:
```
User (Telegram) → Telegram Bot → OAuth Module → Google Sheets Module → User Sheets
        ↑                   │               │                  │
        │                   │               │                  │
        │                   ▼               ▼                  ▼
        │            ┌─────────────┐ ┌─────────────┐    ┌─────────────┐
        │            │Category Mgr │ │  Encryption │    │  Database   │
        │            │ (User/YAML) │ │   (Fernet)  │◄───┤   (SQLite)  │
        │            └──────┬──────┘ └──────┬──────┘    └──────┬──────┘
        │                   │               │                  │
        └───────────────────┴───────────────┴──────────────────┘
```

## Database Schema

The application uses SQLite with SQLAlchemy ORM and includes four main tables:

1. **users**: Stores Telegram user information
   - `user_id` (TEXT, PK): Telegram user ID
   - `telegram_username` (TEXT, nullable)
   - `first_name` (TEXT, nullable)
   - `last_name` (TEXT, nullable)
   - Timestamps: `created_at`, `updated_at`

2. **auth_tokens**: Stores encrypted OAuth tokens
   - `user_id` (TEXT, PK, FK→users)
   - `encrypted_token` (BLOB): Fernet-encrypted token
   - `token_expiry` (TIMESTAMP, nullable)
   - Timestamps: `created_at`, `updated_at`

3. **user_sheets**: Links users to their Google spreadsheets
   - `user_id` (TEXT, PK, FK→users)
   - `spreadsheet_id` (TEXT)
   - `spreadsheet_title` (TEXT, nullable)
   - `is_active` (BOOLEAN): Default TRUE
   - Timestamps: `created_at`, `updated_at`

4. **user_categories**: Stores custom categories
   - `id` (INTEGER, PK): Auto-incremented
   - `user_id` (TEXT, FK→users)
   - `categories_json` (TEXT): JSON-formatted categories
   - Timestamps: `created_at`, `updated_at`

## User Flow

1. **Authentication**: User initiates with `/auth` command
   - Redirected to Google OAuth consent screen
   - Grants permission to access their sheets
   - Token stored encrypted in the database

2. **Sheet Selection**: User selects sheet with `/sheet` command
   - Bot shows available spreadsheets from the user's Google Drive
   - User selects one for financial tracking
   - Selection stored in the database

3. **Category Management**:
   - View current categories: `/categories`
   - Edit categories via YAML: `/editcat`
   - Reset to defaults: `/resetcat`

4. **Transaction Recording**: User adds transaction with `/add`
   - Select transaction type (income/expense)
   - Select category from personalized list
   - Select subcategory for expenses
   - Enter amount
   - Optionally add comments

## Custom Categories System

Categories are stored as JSON in the following structure:
```json
{
  "expense_categories": {
    "CATEGORY1": ["Subcategory1", "Subcategory2"],
    "CATEGORY2": ["Subcategory3", "Subcategory4"]
  },
  "income_categories": [
    "Income1",
    "Income2"
  ]
}
```

The system supports YAML import/export for editing:
```yaml
# Example categories.yaml
expense_categories:
  HOME:
    - Supermarket
    - Mortgage / Rent
    - Electricity
  TRANSPORTATION:
    - Uber
    - Fuel
    - Public Transport

income_categories:
  - Salary / Wages
  - Interest Income
  - Dividends
```

## Security Features

1. **OAuth 2.0 Authentication**: Each user authenticates directly with Google
2. **Token Encryption**: OAuth tokens encrypted with Fernet before database storage
3. **Environment-based Key Management**: Encryption keys stored in environment variables
4. **Automatic Token Refresh**: Expired tokens refreshed automatically
5. **Token Revocation**: `/logout` command revokes Google access and cleans database

## Technical Implementation Details

### Python Typing System
Uses Python 3.9+ typing features:
```python
# Direct container types 
users: list[str] = []
config: dict[str, str] = {}

# Union operator
def process_amount(amount: str | float | int) -> float:
    # Implementation
    pass

# Specific import of Any
from typing import Any
def get_metadata() -> dict[str, Any]:
    # Implementation
    pass
```

### Design Patterns
- **Client Pattern**: `GoogleSheetsClient` encapsulates API access
- **Factory Pattern**: Bot handler creation
- **Repository Pattern**: Data access via SQLAlchemy
- **State Pattern**: Conversation flow management
- **Proxy Pattern**: OAuth delegation
- **Observer Pattern**: OAuth server-bot communication
- **ORM Pattern**: Database mapping
- **Configuration Pattern**: Environment & YAML config loading

### Error Handling
- Robust exception handling for OAuth, API, and database operations
- Graceful handling of decryption errors
- State recovery for conversation interruptions
- Automatic cleanup of invalid tokens

### Important Command Handlers

1. **Authentication Handlers**:
   - `/auth`: Initiates OAuth flow, generates secure state token
   - `/logout`: Revokes Google access, removes tokens from DB

2. **Sheet Management**:
   - `/sheet`: Lists and selects Google Sheets

3. **Transaction Handlers**:
   - `/add`: Multi-step conversation for recording transactions

4. **Category Management**:
   - `/categories`: Displays current category structure
   - `/editcat`: Manages YAML import/export
   - `/resetcat`: Reverts to default categories

## Code Organization

```
/finanzas/
│
├── src/                  # Source code
│   ├── auth/             # OAuth 2.0 Authentication
│   │   ├── oauth.py      # OAuth manager with encryption
│   │
│   ├── bot/              # Telegram bot logic
│   │   ├── bot.py        # Bot configuration
│   │   ├── handlers.py   # Message and command handlers
│   │   ├── commands.py   # Command definitions
│   │   ├── auth_handlers.py # Authentication handlers
│   │
│   ├── config/           # Configuration management
│   │   ├── categories.py # Category manager
│   │   ├── categories.yaml # Default categories
│   │
│   ├── db/               # Database components
│   │   ├── database.py   # SQLAlchemy models
│   │
│   ├── server/           # OAuth web server
│   │   ├── oauth_server.py # OAuth callback handler
│   │
│   ├── sheets/           # Google Sheets integration
│   │   ├── client.py     # Sheets client
│   │   ├── operations.py # Spreadsheet operations
│   │
│   └── utils/            # Utilities
│       ├── config.py     # Environment configuration
│       ├── logger.py     # Logging setup
│
├── main.py               # Application entry point
```

## Dependencies and Libraries

1. **Core Dependencies**:
   - python-telegram-bot (v22.0)
   - gspread
   - google-auth / google-auth-oauthlib
   - flask
   - sqlalchemy
   - cryptography
   - pyyaml
   - loguru
   - python-dotenv
   - pathlib

2. **Development Dependencies**:
   - pytest and pytest-related packages
   - ruff
   - vulture

## Recent Version Changes

**Version 0.1 (Beta, Current)**:
- First public beta release
- Full English interface
- All commands in English
- Based on previous internal version 3.4

**Version 3.3**:
- Added user-specific custom categories
- Categories stored as JSON in the database
- YAML import/export functionality
- Integration with transaction flow

**Version 3.2**:
- SQLite database implementation with SQLAlchemy
- Token encryption using Fernet
- Improved token management and refresh
- Better error handling and recovery

## Known Limitations

1. **Feature Limitations**:
   - No transaction query or visualization commands
   - No transaction editing or deletion
   - Limited data validation

2. **Technical Limitations**:
   - OAuth requires port access or public domain
   - Category editing via YAML is not user-friendly
   - Encryption key requires secure storage
   - No automatic database schema migrations

## Future Development Priorities

1. **Testing Improvements**:
   - Database interaction tests
   - Encryption functionality tests
   - Category management tests

2. **Security Enhancements**:
   - Encryption key rotation
   - More secure key storage

3. **User Experience**:
   - Interactive category editor
   - Transaction query commands
   - Visualization features

4. **Technical Debt**:
   - Static type checking with mypy
   - Database migration system
   - Better async handling

## Environment Setup Requirements

Required environment variables:
- `TELEGRAM_TOKEN`: Bot token from BotFather
- `OAUTH_CREDENTIALS_PATH`: Path to OAuth credentials JSON
- `OAUTH_SERVER_HOST`: Local server host (default: localhost)
- `OAUTH_SERVER_PORT`: Local server port (default: 8000)
- `OAUTH_REDIRECT_URI`: OAuth callback URI
- `OAUTH_ENCRYPTION_KEY`: Fernet encryption key
- `DATABASE_URL`: SQLite connection string
- `LOG_LEVEL`: Logging level (default: INFO)

## Running the Application

1. Create virtual environment with Python 3.13+
2. Install dependencies with uv or pip
3. Configure environment variables
4. Run with `python main.py`

## License Information

This project is licensed under the GNU General Public License v3.0.
