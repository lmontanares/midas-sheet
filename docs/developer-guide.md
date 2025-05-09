# MidasSheet: Developer Guide

*Version: 0.1 Beta*

## 1. Project Architecture

### Core Components

The Financial Management System consists of several interconnected components:

1. **Telegram Bot Interface**: Provides the user interface via Telegram
2. **OAuth 2.0 Authentication**: Secures access to Google Sheets
3. **Google Sheets Integration**: Stores financial data in user spreadsheets
4. **SQLite Database**: Stores encrypted tokens, selected sheets, and categories
5. **Category Management**: Handles default and user-specific categories

### Architectural Diagram

```
                  ┌─────────────┐
                  │Google OAuth │
                  │   Server    │
                  └──────┬──────┘
                         │
                         │ (Authentication)
                         ▼
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
                   (Responses, visualizations, category management)

                                        (Stores Encrypted Tokens,
                                         User Sheets, User Categories)
```

### Information Flow

1. User sends a command to the bot via Telegram
2. The bot processes the command through appropriate handlers
3. For authenticated operations:
   - OAuth tokens are retrieved from database and decrypted
   - Google Sheets are accessed with the authenticated client
4. For category management:
   - Categories are loaded from user-specific DB records or defaults
5. For transaction logging:
   - Data is written to the appropriate spreadsheet
   - Confirmation is sent back to the user

## 2. Technical Stack

### Core Technologies

- **Python 3.13+**: Modern Python with type hints
- **python-telegram-bot (v22.0)**: Telegram bot framework
- **gspread + google-auth**: Google Sheets integration
- **SQLAlchemy + SQLite**: Database ORM and storage
- **cryptography (Fernet)**: Secure token encryption
- **Flask**: OAuth callback server
- **YAML**: Category configuration format

### Modern Type Hints

The project uses Python 3.9+ typing features:

```python
# Direct container types (Python 3.9+)
users: list[str] = []
config: dict[str, str] = {}

# Union operator (Python 3.9+)
def process_amount(amount: str | float | int) -> float:
    # Implementation
    pass

# Specific import of Any when necessary
from typing import Any
def get_metadata() -> dict[str, Any]:
    # Implementation
    pass
```

## 3. Database Structure

Four main tables are implemented:

```mermaid
erDiagram
    users ||--o{ auth_tokens : "stores"
    users ||--o{ user_sheets : "selects"
    users ||--o{ user_categories : "customizes"

    users {
        TEXT user_id PK "Telegram User ID"
        TEXT telegram_username NULL
        TEXT first_name NULL
        TEXT last_name NULL
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
        TIMESTAMP updated_at "DEFAULT CURRENT_TIMESTAMP"
    }

    auth_tokens {
        TEXT user_id PK FK "References users.user_id"
        BLOB encrypted_token "Fernet encrypted token data"
        TIMESTAMP token_expiry NULL "Optional: Extracted expiry for cleanup"
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
        TIMESTAMP updated_at "DEFAULT CURRENT_TIMESTAMP"
    }

    user_sheets {
        TEXT user_id PK FK "References users.user_id"
        TEXT spreadsheet_id "Google Sheet ID"
        TEXT spreadsheet_title NULL "Optional: Sheet title"
        BOOLEAN is_active "DEFAULT TRUE"
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
        TIMESTAMP updated_at "DEFAULT CURRENT_TIMESTAMP"
    }

    user_categories {
        INTEGER id PK "Auto-incrementing primary key"
        TEXT user_id FK "References users.user_id"
        TEXT categories_json "Stores categories as JSON"
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
        TIMESTAMP updated_at "DEFAULT CURRENT_TIMESTAMP"
    }
```

## 4. Authentication System

### OAuth Flow

1. User initiates authentication with `/auth` command
2. Bot generates a secure state token and authorization URL
3. User completes authentication in browser
4. OAuth server receives callback with authorization code
5. Code is exchanged for access and refresh tokens
6. Tokens are encrypted and stored in the database
7. Subsequent API calls use stored tokens (refreshed when needed)
8. User can revoke access with `/logout` command

### Token Encryption

Tokens are secured through Fernet symmetric encryption:
1. Tokens are serialized to JSON and encoded in UTF-8
2. The encoded data is encrypted using Fernet with an environment key
3. Encrypted tokens are stored as BLOBs in the database
4. When needed, tokens are retrieved and decrypted
5. If decryption fails, the token record is deleted

## 5. Custom Categories System

### Structure

Categories are stored in JSON format:

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

### Management

The `CategoryManager` class handles:
- Loading default categories from YAML file
- Loading user-specific categories from the database
- Saving updated categories back to the database
- Providing categories for transaction logging

### YAML Format

Categories can be exported/imported as YAML:

```yaml
# Example categories.yaml
expense_categories:
  HOME: # Category Name
    - Supermarket # Subcategory 1
    - Mortgage / Rent # Subcategory 2
    - Electricity
  TRANSPORTATION:
    - Uber
    - Fuel
    - Public Transport

income_categories:
  - Salary / Wages # Income Category 1
  - Interest Income
  - Dividends
```

## 6. Design Patterns

The project implements several design patterns:

- **Client Pattern**: Encapsulation of Google Sheets access (`GoogleSheetsClient`)
- **Factory Pattern**: Creation of bot handlers
- **Repository Pattern**: Data access through SQLAlchemy
- **State Pattern**: Conversation flow management
- **Proxy Pattern**: OAuth management delegation
- **Dependency Injection**: Passing dependencies in constructors
- **Observer Pattern**: OAuth server-bot communication
- **ORM Pattern**: Database mapping with SQLAlchemy
- **Configuration Pattern**: Loading settings from environment and files

## 7. Known Limitations

- No transaction query or visualization commands yet
- Limited data validation for user inputs
- No transaction editing or deletion capabilities
- OAuth server requires port access or public domain
- The encryption key requires secure storage
- Editing categories via YAML can be cumbersome

## 8. Development Setup

1. Clone the repository
2. Configure environment variables (copy `.env.example` to `.env`)
3. Generate a Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
4. Set up OAuth in Google Cloud Platform
5. Run the application: `uv run python main.py`

> Note: `uv run` automatically handles virtual environment creation, dependency installation, and activation.

## 9. Future Improvements

### Short Term

- Comprehensive tests for database and encryption
- Improved token/key management
- Transaction query commands
- Better data validation
- Transaction editing capabilities

### Long Term

- Interactive category editor in Telegram
- Advanced financial reporting and visualization
- Budget and alert features
- Multiple currency support
- Database migration to PostgreSQL for production
- Backup and restoration mechanisms

## 10. Code Conventions

- Follow PEP 8 style guidelines
- Use modern Python 3.9+ typing features
- Document all public interfaces with docstrings
- Include type annotations for all public methods
- Write tests for new functionality
- Maintain modular architecture and separation of concerns