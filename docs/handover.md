# Handover Document: Financial Management System v3.3

## 1. Project Overview

### Core Purpose and Main Objectives
The Financial Management System is an application designed to facilitate tracking and control of personal finances through a Telegram bot integrated with Google Sheets. The main objective is to provide an accessible tool that allows users to record and query their income and expenses easily from any device with Telegram, using their own spreadsheets and personalized categories.

### Description of Core Functionality
The system consists of several components working together:
1.  A Telegram bot that serves as a user interface for recording financial transactions, querying information, and managing settings.
2.  A Google Sheets integration module that stores and manages financial data in the user's cloud spreadsheets.
3.  An OAuth 2.0 authentication module for secure access to Google Sheets.
4.  An SQLite database for persistent storage of user data, encrypted tokens, selected sheets, and custom categories.
5.  A category management system allowing users to define their own income and expense categories.

The user interacts with the bot following a specific flow:
1.  The user authenticates with their Google account using OAuth 2.0 (`/auth`).
2.  They select one of their spreadsheets directly with the (`/sheet`) command.
3.  They can manage their custom categories using `/categorias`, `/editarcat`, and `/resetcat`.
4.  They initiate transaction recording with the `/agregar` (add) command.
5.  They choose the transaction type (income or expense).
6.  They select a category **from their personalized list (or defaults if none are set)**.
7.  If they selected an expense, they select a subcategory **from their personalized list**.
8.  They enter the transaction amount.
9.  They decide whether to add an optional comment (with Yes/No buttons).
10. If they chose to add a comment, they write it; if not, it's recorded without a comment.
11. The system records the transaction in the corresponding spreadsheet using the selected categories.

### Problems It Solves and Value It Provides
- Simplifies recording expenses and income without requiring complex applications
- Allows access and management of financial information from any device with Telegram
- Centralizes financial data in Google Sheets, facilitating later analysis
- Eliminates the need for expensive or complex personal finance tools
- Provides a hierarchical structure to categorize expenses, facilitating detailed analysis
- Allows contextualizing transactions through an optional comment field
- Guided interface using buttons that simplifies the user experience
- Allows each user to work with their own spreadsheets thanks to OAuth 2.0
- Protects data privacy by not requiring sharing sheets with the bot
- **Ensures credential security through token encryption (v3.2)**
- **Allows each user to customize and manage their own transaction categories (v3.3)**

## 2. Technological Ecosystem

### Programming Languages Used
- Python 3.13+ (leveraging modern typing features)

### Type Hints System
The project makes extensive use of Python 3.9+ static typing system, taking advantage of modern features:

- **Direct use of built-in container types** without imports from typing:
  ```python
  # Correct - using modern typing (Python 3.9+)
  users: list[str] = []
  config: dict[str, str] = {}
  ```

- **Union operator `|` for multiple types**:
  ```python
  # Correct - using | operator (Python 3.9+)
  def process_amount(amount: str | float | int) -> float:
      # Implementation
  ```

- **Specific import of `Any` when necessary**:
  ```python
  from typing import Any

  def get_metadata() -> dict[str, Any]:
      # Implementation
  ```

All public methods and functions include complete type annotations, improving documentation, facilitating development, and enabling static type checking.

### Frameworks, Libraries, and Main Dependencies
- **Telegram Bot:**
  - python-telegram-bot (v22.0): Framework for creating the bot
- **Google Sheets:**
  - gspread: Library for interacting with Google Sheets
  - google-auth: Base authentication (includes transport via requests)
  - google-auth-oauthlib: OAuth 2.0 authentication with Google
- **OAuth Server:**
  - Flask: Lightweight web server for handling OAuth redirections
- **Security:**
  - **cryptography**: For token encryption and decryption
  - **hashlib**: For hashing user identifiers
  - **secrets**: For secure token state generation
- **Database:**
  - **SQLAlchemy**: ORM for database management
  - **SQLite**: Lightweight, serverless database engine
- **Configuration and Data:**
  - pyyaml: For handling YAML configuration files (including category import/export)
- **Utilities:**
  - loguru: Advanced logging system
  - python-dotenv: Environment variable management
  - pathlib: Modern file path handling
  - requests: HTTP library (used by google-auth)
- **Testing:**
  - pytest: Main testing framework
  - pytest-asyncio: Support for asynchronous tests
  - pytest-cov: Code coverage measurement
  - pytest-mock: Creation of mocks with native integration in pytest
- **Development:**
  - ruff: Linter and formatter
  - vulture: Dead code detection

### Development Tools and Work Environment
- Package manager: uv (modern alternative to pip)
- Version control: Git
- Virtual environment: Recommended for dependency isolation
- Tests: pytest with the plugins mentioned above

## 3. Architecture and Structure

### Conceptual Architecture Diagram
The architecture follows a modular pattern with clear separation of responsibilities, OAuth authentication, encryption for security, database persistence, and user-specific configurations:

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

The information flow begins when the user sends commands to the bot through Telegram. The user first authenticates using OAuth 2.0, allowing the bot to access their own Google spreadsheets. **The tokens generated in this process are encrypted using Fernet before being stored in the SQLite database (v3.2)**. Users can manage their custom categories, which are also stored in the database (v3.3). The bot processes commands, interacts with the database to retrieve tokens (decrypting them) and categories, and uses the Google Sheets module to read/write data in the user's sheets. Finally, the bot sends responses to the user.

### Component/Module Structure
```
/finanzas/
│
├── src/                  # Source code
│   ├── __init__.py       # Main module initialization
│   ├── auth/             # OAuth 2.0 Authentication
│   │   ├── __init__.py   # Module initialization
│   │   └── oauth.py      # OAuth authentication manager with encryption
│   │
│   ├── bot/              # Telegram bot logic
│   │   ├── __init__.py   # Module initialization
│   │   ├── bot.py        # Main bot configuration
│   │   ├── handlers.py   # Message and command handlers (incl. category editing)
│   │   ├── commands.py   # Command definitions (incl. category commands)
│   │   └── auth_handlers.py # Specific handlers for authentication
│   │
│   ├── config/           # External configurations & Category Management
│   │   ├── __init__.py   # Module initialization
│   │   ├── categories.py # Categories manager (handles defaults & user specifics)
│   │   └── categories.yaml # Default categories configuration file
│   │
│   ├── db/               # Database models and functions
│   │   ├── __init__.py   # Module initialization
│   │   └── database.py   # SQLAlchemy configuration and models (User, AuthToken, UserSheet, UserCategories)
│   │
│   ├── server/           # Server for OAuth
│   │   ├── __init__.py   # Module initialization
│   │   └── oauth_server.py # Server for OAuth redirections
│   │
│   ├── sheets/           # Google Sheets integration
│   │   ├── __init__.py   # Module initialization
│   │   ├── client.py     # Client to connect with Google Sheets
│   │   └── operations.py # Operations with spreadsheets
│   │
│   └── utils/            # Common utilities
│       ├── __init__.py   # Module initialization
│       ├── config.py     # Configuration and environment variables
│       └── logger.py     # Logging configuration
│
├── tests/                # Automated tests
│   ├── __init__.py       # Test module initialization
│   ├── test_bot.py       # Tests for the Telegram bot
│   ├── test_commands.py  # Tests for bot commands
│   ├── test_handlers.py  # Tests for bot handlers
│   ├── test_sheets.py    # Tests for Google Sheets integration
│   # (test_auth.py - Currently Missing)
│   # (test_categories.py - Currently Missing)
│   # (test_database.py - Currently Missing)
│   ├── conftest.py       # Shared fixtures for tests
│   └── README.md         # Test documentation
│
├── docs/                 # Project documentation
│   └── handover.md       # Handover document
│
├── logs/                 # Directory for log files
│
├── main.py               # Application entry point
├── finanzas.db           # SQLite database (Runtime, not in repo)
├── pyproject.toml        # Python project configuration
├── pytest.ini            # pytest configuration
├── .env                  # Environment variables (Local, not in repo)
├── .env.example          # Example environment variables
├── oauth_credentials.json # Google API OAuth credentials (Local, not in repo)
└── README.md             # Main documentation
```
# Note: Files like finanzas.db, .env, and oauth_credentials.json are generated/configured at runtime and are typically excluded from version control.

### Design Patterns Implemented
- **Client Pattern**: Encapsulation of Google Sheets access in a client class (`GoogleSheetsClient`)
- **Factory Pattern**: Creation of handlers for the Telegram bot (in `commands.py`)
- **Repository Pattern**: Implemented for data access through SQLAlchemy
- **State Pattern**: Implemented for conversation flow using the `user_data` dictionary with defined states to handle the transition between flow steps
- **Proxy/Delegation Pattern**: Implemented in `OAuthManager` to handle Google authentication
- **Applied Cryptography**: Implemented in `OAuthManager` to encrypt and decrypt stored tokens
- **Properties (@property)**: For controlled access to configuration (in `config.py`)
- **Dependency Injection**: Classes receive their dependencies in the constructor (e.g., `TelegramBot` receives `SheetsOperations`, `OAuthManager`, `CategoryManager`)
- **Asynchronous Callbacks**: Use of `post_init` for asynchronous bot command registration
- **Multi-threaded Server**: Implementation of the OAuth server in a separate thread to avoid blocking the bot
- **Observer Pattern**: Implemented for communication between the OAuth server and the bot through callbacks
- **ORM (Object-Relational Mapping)**: Use of SQLAlchemy to map Python objects to database tables
- **Configuration Pattern**: Loading default categories from YAML and user-specific categories from the database (`CategoryManager`)

## 4. Current Development Status

### Implemented Features and Complete Functionalities
- Complete basic project structure with modular organization
- Initial Telegram bot configuration implemented
- **Complete OAuth 2.0 authentication system (v3.2):**
  - Authorization flow with Google redirection
  - Token management by user
  - Automatic refresh of expired tokens
  - Access revocation
  - **Complete token encryption**
  - **Secure cryptographic key management**
- **SQL database implementation with SQLAlchemy and SQLite (v3.2):**
  - Persistent storage of users, encrypted authentication tokens, and selected spreadsheets.
  - Creation of `User`, `AuthToken`, and `UserSheet` tables.
  - Refactoring of token storage and sheet selection to use the database.
- **Custom Categories per User (v3.3):**
  - Storage of user-specific categories (JSON) in the `user_categories` database table.
  - `CategoryManager` handles loading defaults and user specifics.
  - Commands to view (`/categorias`), edit (`/editarcat` via YAML import/export), and reset (`/resetcat`) categories.
  - Integration into the `/agregar` transaction flow to use custom categories/subcategories.
- **Implemented commands:**
  - `/auth`: Initiates the OAuth authentication process
  - `/sheet`: Selects a specific spreadsheet (includes functionality to list available sheets)
  - `/logout`: Logs out and revokes access
  - `/start`: Initiates interaction with the bot
  - `/help`: Shows help about available commands
  - `/agregar`: Adds a new expense or income (using custom categories)
  - `/recargar`: Reloads data from the server (e.g., categories - though now less needed)
  - `/categorias`: Shows user's current custom categories
  - `/editarcat`: Provides options (YAML import/export) to edit custom categories
  - `/resetcat`: Resets user's categories to default values
- Web server for handling OAuth redirections implemented
- Complete implementation of the `/agregar` command with interactive flow using buttons:
  - Clear selection of transaction type (income/expense) as the first step
  - Category selection using buttons **(from user's custom list)**
  - Subcategory selection for expenses **(from user's custom list)**
  - Amount entry
  - Option to add optional comments using buttons (Yes/No)
  - Registration in spreadsheets with all fields
- System of default configurable categories from external YAML file
- Multi-user OAuth 2.0 authentication:
  - Each user accesses their own spreadsheets
  - Data is stored in user-specific sheets
  - Handling of multiple simultaneous user sessions
- Integration with Google Sheets to store transactions in user-specific sheets
- Use of `pathlib.Path` for modern file path handling
- State system to manage conversation flows with robustness
- Advanced error handling and recovery system
- **Complete static typing system:**
  - Type annotations on all public interfaces
  - Use of modern Python 3.9+ typing features
  - Detailed type documentation
- **Complete testing system:**
  - Unit tests for bot components
  - Tests for Google Sheets integration
  - Tests for OAuth authentication
  - Tests for the redirection server
  - Mocks for external APIs (Telegram, Google)
  - # (Tests for database interactions - Currently Missing)
  - # (Tests for category management - Currently Missing)

### Progress and Achievements to Date
- Complete implementation of the OAuth 2.0 authentication system
- Migration from service account authentication to OAuth 2.0
- **Implementation of token encryption using Fernet (v3.2)**
- **Refactoring to use SQLAlchemy with SQLite instead of files (v3.2):**
  - Secure storage of encrypted tokens in the database
  - Association of users with selected spreadsheets
  - Data persistence between bot restarts
- **Token revocation implemented with cleanup of database records (v3.2)**
- **Implementation of Custom Categories per User (v3.3):**
  - Database storage for user categories
  - Commands for category management
  - Integration into transaction flow
  - YAML import/export functionality
- Support for multiple users with access to their own sheets
- Integration of a web server to handle OAuth redirections
- Implementation of complete authorization flow and sheet selection
- Secure token management by user
- Automatic refresh of expired tokens
- Intuitive navigation between different spreadsheets
- Improved security by not requiring sharing sheets with a service account
- Improvements in the start message to guide the user in the authentication process
- Implementation of authentication checks in all relevant operations
- Significant improvements in authentication-related error handling
- The "gastos" (expenses) and "ingresos" (income) sheets include columns for category, subcategory, and comment
- `/help` command updated with new available commands
- Complete implementation of the modern static typing system
- Successful implementation of SQL database integration (SQLAlchemy + SQLite)

### Existing Technical Documentation
- Detailed docstrings in main classes and methods
- README.md updated with instructions for OAuth 2.0 and setup
- Test documentation in tests/README.md
- Well-organized and documented project structure
- YAML file with clear documentation about default categories
- Detailed handover document updated with OAuth, encryption, database (v3.2), and custom categories (v3.3) (this document)

## 5. Challenges and Technical Considerations

### Known Issues or Limitations
- No commands to query or visualize recorded transactions
- No advanced validation for user-entered values (amounts, etc.)
- No mechanisms for editing or deleting erroneous transactions
- Asynchronous handling between Python and python-telegram-bot can be complex:
  - A solution has been implemented using post_init callbacks for command registration
  - Warnings related to unexpected coroutines may arise, which do not affect functionality
- Potential errors in comment handling when conversation state is lost
- The OAuth server requires port access on the server for redirections
- In production environments, a public domain with HTTPS is required for OAuth redirections
- **The encryption key is stored in the `OAUTH_ENCRYPTION_KEY` environment variable, which requires additional protection of the `.env` file**
- **Editing categories via YAML file upload/download can be cumbersome for some users.**

### Accumulated Technical Debt
- No comprehensive data validation for financial entries
- Asynchronous loads for multiple components are not implemented optimally
- No complete end-user documentation (especially for category editing)
- **Missing tests for OAuth functionalities:**
  - Integration tests for the OAuth flow
  - Tests for expired token handling and revocation
  - Tests for communication between OAuth server and bot
- **Missing tests for database integration:**
  - Basic CRUD operations
  - Data persistence between restarts
  - Referential integrity
- **Missing tests for encryption functionality:**
  - Token encryption and decryption tests
  - Recovery tests for decryption errors
  - Key management tests
- **Missing tests for custom category functionality:**
  - Basic CRUD operations via commands
  - YAML import/export validation and edge cases
  - Integration tests with the `/agregar` flow using custom categories
  - Tests for `/resetcat` functionality
- OAuth server closure handling could be improved to ensure clean termination
- No static type checking configured in the CI/CD flow
- No automatic database schema migration for future changes

### Pending Optimizations
- **Implement periodic rotation of encryption keys**
- Implement session expiration for inactive users
- Improve specific OAuth error handling
- Implement caching to reduce calls to the Google API
- Improve error handling for specific situations (e.g., invalid YAML format)
- Implement advanced data validation for financial entries
- Integrate automatic code analysis tools (linters, formatters)
- Add static type checking with mypy
- Improve asynchronous operation handling to avoid warnings
- Improve communication between the OAuth server and the bot:
  - Implement more robust mechanism to communicate authorization codes
  - Handle timeouts in the authorization process
- **Optimize database queries:**
  - Implement additional indexes if necessary (e.g., on `user_categories.user_id`)
  - Consider using a cache system for frequent queries (e.g., user categories)
- **Implement a migration system for the database:**
  - Use Alembic to manage database schema changes
  - Allow updates without data loss
- **Improve category editing experience (e.g., interactive editor within Telegram).**

## 6. Roadmap

### Immediate Next Steps
1.  **Implement comprehensive tests for database functionalities (v3.2 features)**
2.  **Implement comprehensive tests for encryption functionalities (v3.2 features)**
3.  **Implement comprehensive tests for custom category functionalities (v3.3 features)**
4.  **Implement advanced rotation and management of cryptographic keys**
5.  **Implement token re-encryption in case of key change**
6.  **Improve specific error handling for token encryption/decryption**
7.  Implement command to query recent transactions including comments
8.  Implement command to visualize summaries (e.g., expenses by category) by user
9.  Improve input data validation in all fields
10. Add functionality to edit or delete transactions
11. Configure static type checking with mypy
12. Improve end-user documentation for the authentication and category management processes
13. **Implement migration system with Alembic**

### Planned Features for Medium/Long Term
1.  **More secure storage system for cryptographic keys (HSM or secret management systems)**
2.  **Interactive category editor within Telegram**
3.  Implement more advanced financial reports and analysis by user
4.  Add budget and alert functionalities
5.  Integrate charts and visualizations through Telegram
6.  Allow data export in different formats
7.  Implement intelligent spending pattern analysis
8.  Allow sharing sheets between multiple users (collaboration)
9.  Text searches in comments and transaction filtering
10. Implement scheduled notifications and reminders
11. Add support for multiple currencies and automatic conversion
12. **Migrate to a more robust database for production environments (PostgreSQL)**
13. **Implement database backup and restoration mechanisms**


### Tentative Schedule
Information not available: No formal development schedule has been established.

## 7. Key Decisions

### Important Architectural Choices and Their Justifications
1.  **Migration from service_account to OAuth 2.0 (v3.2)**: Allows each user to use their own sheets, improving privacy and avoiding the need to share sheets with a service account.
2.  **Flask server for OAuth redirections (v3.2)**: Provides a simple and efficient way to handle OAuth redirection callback, running in a separate thread to avoid blocking the bot.
3.  **Centralized OAuth manager (v3.2)**: Encapsulates all authentication logic in a dedicated class, facilitating token and credential management.
4.  **Token encryption (v3.2)**: Uses Fernet (cryptography) to encrypt tokens in the database, significantly improving the security of user credentials.
5.  **Use of SQLAlchemy with SQLite (v3.2)**: Provides data persistence and a relational data model while maintaining implementation simplicity without requiring a separate database server.
6.  **ORM for data access (v3.2)**: Provides an abstraction layer that facilitates working with the database and allows changing the database engine in the future if necessary.
7.  **Custom Categories stored in Database (v3.3)**: Stores user-specific categories persistently in the database (JSON format) for flexibility and personalization.
8.  **YAML for Category Import/Export (v3.3)**: Provides a human-readable format for users to manage complex category structures externally, although with usability trade-offs.
9.  **Enhanced Category Manager (v3.3)**: Centralizes logic for handling default and user-specific categories, loading them as needed.
10. **Use of python-telegram-bot**: Provides a modern and asynchronous API to interact with the Telegram API.
11. **Use of gspread with OAuth**: Offers a simple interface to access user-specific sheets.
12. **Modular structure**: Facilitates code extension and maintenance, with clear separation of responsibilities.
13. **Modern typing system (Python 3.9+)**: Improves readability, documentation, and code verification with less visual overhead.
14. **Loguru for logging**: Provides a more friendly and powerful interface than the standard logging module.
15. **Pytest and pytest-mock for tests**: Modern framework with better support for fixtures and mocking than unittest.
16. **State system for conversation**: Allows a robust and recoverable flow, facilitating conversation management by stages.
17. **Preventive data verification**: Validation of data existence before processing to avoid errors due to lost state.

### Technical Trade-offs Made
1.  **Complexity vs. Flexibility**: The implementation of OAuth 2.0, encryption, database, and custom categories increases system complexity, but offers greater flexibility, security, persistence, and personalization for users.
2.  **Performance vs. Security**: Encryption/decryption adds a small processing overhead, but significantly improves security.
3.  **Local server vs. External service**: A local server was chosen for OAuth, which simplifies development but requires additional considerations for production.
4.  **SQLite vs. Server database**: SQLite was chosen for its simplicity and ease of configuration, although it has limitations in concurrency and scalability compared to systems like PostgreSQL.
5.  **Encryption key in environment variables vs. Secret management system**: Environment variables were chosen for simplicity, although a dedicated secret management system would be more secure.
6.  **Category Storage (JSON vs. Normalized Tables)**: Storing categories as JSON in a single column is simpler to implement initially but less flexible for complex queries compared to normalized tables.
7.  **Category Editing (YAML vs. Interactive UI)**: YAML import/export is easier to implement initially but less user-friendly than a fully interactive editor within Telegram.
8.  **Telegram as main interface**: Telegram was chosen for its accessibility and simplicity, although it limits some advanced UI options.
9.  **Google Sheets as transaction database**: Chosen for its ease of use and visualization, although it doesn't have the capabilities of a complete database system.
10. **Tests with pytest-mock vs unittest.mock**: pytest-mock was chosen for its better integration with pytest and cleaner syntax, although it requires an additional dependency.
11. **Guided flow vs. Free input**: A guided flow was implemented using buttons, which improves the user experience but requires more complexity in the code.
12. **Specific handlers vs. General handlers**: Specific handlers were implemented for OAuth and potentially categories, which improves code organization but increases structure complexity.
13. **Robustness vs. Performance**: Multiple checks and logging were implemented to ensure robustness, accepting a slight impact on performance.
14. **Modern typing vs. Compatibility with older versions**: Modern typing (Python 3.9+) was chosen for its clarity and conciseness, sacrificing compatibility with older Python versions.

### Lessons Learned During Development
- OAuth 2.0 authentication requires careful planning of the user flow.
- Communication between a web server and a Telegram bot requires synchronization mechanisms.
- Token handling requires important security considerations, including encryption.
- **Cryptographic key management is a critical aspect that requires specific attention.**
- **Using SQLAlchemy significantly facilitates working with relational databases from Python.**
- **Migration from file-based storage to database can significantly improve system robustness.**
- **Managing user-specific configurations (like categories) requires careful database design and application logic.**
- **Choosing the right format/method for user configuration (e.g., YAML vs. UI) involves balancing implementation effort and user experience.**
- User state management is crucial to maintain application coherence.
- Correct structure and modularization from the beginning facilitates project extension.
- Implementation of interactive flows with buttons significantly improves the user experience.
- Detailed event logging is indispensable to identify production problems.
- Authentication verification must be performed at each point where protected resources are accessed.
- **Correct handling of authentication, decryption, and configuration errors significantly improves the user experience.**
- Each user may have different needs and spreadsheet/category structures.
- Modern type annotations significantly improve code documentation and reduce errors.
- Consistency in typing style is important for code maintainability.
- **The cryptography library provides powerful and easy-to-use tools for secure encryption.**
- **Using an ORM like SQLAlchemy allows a smooth transition from file-based storage to a relational database.**
- **Proper management of database sessions is crucial to avoid resource leaks.**

## 8. Additional Resources

### Links to Repositories, Documentation, or Diagrams
Information not available: No links to external repositories or additional documentation have been provided.

### Key Contacts for Queries
Information not available: No contacts have been specified for this project.

### Information About Test/Production Environments
The project is configured to run in a local development environment. For a production environment, it is recommended:
- Configure a public domain with HTTPS for OAuth redirections
- Register the public domain in Google Cloud Platform
- **Implement a secure cryptographic key management system**
- **Consider using secret management services (HashiCorp Vault, AWS KMS, etc.)**
- **Migrate to a more robust database like PostgreSQL for better scalability and concurrency**
- Configure a monitoring system for the OAuth server and the bot
- **Implement regular database backups**

Tests are run using pytest and can be initiated with:
- `pytest`: Runs the tests directly
- `pytest --cov=src`: Runs the tests with coverage report

It is recommended to implement static type checking (e.g., with mypy), potentially configured via a script in `pyproject.toml`.

## 9. Instructions to Continue Development

1.  Clone the repository (or access the `/home/somebody/dev/finanzas` folder)
2.  Create a virtual environment: `uv venv .venv`
3.  Activate the environment: `source .venv/bin/activate` (Linux/Mac) or `.venv\Scripts\activate` (Windows)
4.  Install dependencies: `uv pip install -r requirements.txt`
5.  For development, install additional dependencies: `uv pip install -e ".[dev]"`
6.  Configure environment variables by copying `.env.example` to `.env` and completing the values (including `BOT_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`).
7.  Configure OAuth in Google Cloud Platform:
    - Create a project if it doesn't exist
    - Enable Google Sheets and Google Drive APIs
    - Create OAuth 2.0 credentials for **Web application**
    - Add redirection URI: `http://localhost:8000/oauth2callback` (or your configured host/port)
    - Download the credentials JSON and save it as `oauth_credentials.json`
8.  **Generate a Fernet encryption key:**
    ```bash
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ```
9.  **Add the generated key to `.env` as `OAUTH_ENCRYPTION_KEY`**
10. Initialize the database (if it doesn't exist): The application should do this on first run via `init_db()`.
11. Run tests: `pytest` or `pytest --cov=src`
12. Run the application: `python main.py`

## 10. Recent Important Changes

The most significant modifications in the latest versions include:

**Version 3.2:**

1.  **SQL database implementation:**
    - Migration from file-based storage to SQLite with SQLAlchemy
    - Creation of ORM models for users, tokens, and spreadsheets
    - Implementation of the repository pattern for data access
    - Refactoring of token storage to use the database
    - Improvement in data persistence and relationships between entities

2.  **Security and encryption improvements:**
    - Storage of encrypted tokens in the database
    - Improved handling of decryption errors
    - Better recovery from encryption/decryption failures
    - Automatic cleanup of invalid tokens in the database

**Version 3.3:**

3.  **Custom Categories per User:**
    - Added `user_categories` table to the database to store categories as JSON.
    - Implemented `CategoryManager` to handle default and user-specific categories.
    - Added commands (`/categorias`, `/editarcat`, `/resetcat`) for users to manage their categories.
    - Integrated custom categories into the `/agregar` transaction flow.
    - Implemented YAML import/export functionality for category editing.

4.  **Project structure and error handling improvements:**
    - Reorganization of modules for better coherence (e.g., category logic).
    - Improved separation of responsibilities.
    - Refactoring to follow SOLID principles.
    - Better database session management.
    - More robust exception handling during authentication and category operations.
    - Better error messages for the end user related to categories.

These modifications significantly increase the system's robustness, security, and flexibility by improving data persistence (v3.2), maintaining token encryption in the database (v3.2), providing a more structured relational data model (v3.2), and allowing users to personalize their financial tracking experience with custom categories (v3.3).

## 11. SQL Database Implementation (v3.2)

SQL database integration has been implemented using SQLAlchemy with a SQLite backend. This implementation replaces file-based storage for authentication tokens and manages user information and selected spreadsheets. *Section 12 details the addition of user category storage.*

### 11.1. Database Schema Design

Four main tables have been implemented: `users`, `auth_tokens`, `user_sheets`, and `user_categories` (added in v3.3).

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

**Implemented Table Definitions:**

*   **`users`**: Stores basic information about Telegram users.
    *   `user_id` (TEXT, Primary Key): Unique Telegram user ID.
    *   `telegram_username` (TEXT, Nullable): Telegram username.
    *   `first_name` (TEXT, Nullable): User's first name.
    *   `last_name` (TEXT, Nullable): User's last name.
    *   `created_at` (TIMESTAMP): User creation date.
    *   `updated_at` (TIMESTAMP): Last update date.
*   **`auth_tokens`**: Stores encrypted Google OAuth tokens.
    *   `user_id` (TEXT, Primary Key, Foreign Key -> `users.user_id`): Link to the user.
    *   `encrypted_token` (BLOB): Stores the output of `Fernet.encrypt()`.
    *   `token_expiry` (TIMESTAMP, Nullable): Optionally stores the token expiration date unencrypted for easier querying/cleanup.
    *   `created_at` (TIMESTAMP): Token creation date.
    *   `updated_at` (TIMESTAMP): Token last update date (e.g., after refreshing).
*   **`user_sheets`**: Associates users with their selected Google spreadsheet.
    *   `user_id` (TEXT, Primary Key, Foreign Key -> `users.user_id`): Link to the user.
    *   `spreadsheet_id` (TEXT): ID of the Google sheet selected by the user.
    *   `spreadsheet_title` (TEXT, Nullable): Sheet title for user feedback.
    *   `is_active` (BOOLEAN): Currently assumes one sheet per user, but allows future expansion.
    *   `created_at` (TIMESTAMP): Sheet association date.
    *   `updated_at` (TIMESTAMP): Last update date.
*   **`user_categories` (v3.3)**: Stores customized categories for each user.
    *   `id` (INTEGER, Primary Key): Auto-incrementing unique identifier.
    *   `user_id` (TEXT, Foreign Key -> `users.user_id`): Link to the user.
    *   `categories_json` (TEXT): JSON string containing the user's customized categories.
    *   `created_at` (TIMESTAMP): Categories creation date.
    *   `updated_at` (TIMESTAMP): Last update date.

### 11.2. Advantages of Database Implementation
1.  **Improved data persistence**: Data survives system restarts and doesn't depend on disk files that could become corrupted.
2.  **Referential integrity**: Ensures correct relationships between users, tokens, sheets, and categories.
3.  **Structured queries**: Allows performing complex queries when necessary.
4.  **Scalability**: Facilitates migration to more robust database systems in the future (PostgreSQL, MySQL).
5.  **Transactions**: Guarantees atomic operations to maintain data consistency.
6.  **Better organization**: The data model is more explicit and understandable.
7.  **Security**: Better access control to sensitive data (especially with encryption).

### 11.3. Technical Implementation
The implementation uses SQLAlchemy as an ORM with the following features:

1.  **Declarative models**: Models are defined using the `DeclarativeBase` base class.
2.  **Annotated types**: Use of `Mapped[type]` to define fields with static typing.
3.  **Defined relationships**: Use of foreign keys to maintain referential integrity.
4.  **Automatic timestamps**: `created_at` and `updated_at` fields managed automatically.
5.  **Session management**: Implementation of the session pattern to interact with the database.
6.  **Automatic initialization**: The `init_db()` function ensures that tables exist before starting the application.

### 11.4. Encryption Handling with Database
OAuth tokens are securely stored through the following process:

1.  The token is serialized to JSON and encoded in UTF-8
2.  The encoded token is encrypted using Fernet with a secret key
3.  The encrypted token is stored as a BLOB in the `auth_tokens` table
4.  When retrieving the token, it is decrypted using the same key
5.  If decryption fails, the corrupted record is deleted

## 12. Custom Categories per User (v3.3)

A complete system for custom categories per user has been implemented, allowing each client to personalize their expense and income categories according to their needs.

### 12.1. Custom Categories Overview
The system allows users to:
- View their current custom categories (`/categorias`)
- Edit categories via YAML file import/export (`/editarcat`)
- Reset categories to default values (`/resetcat`)

Categories are stored as a JSON string in the `user_categories` table in the database, with the following structure:

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

### 12.2. Key Components Implemented
1.  **`UserCategories` Database Model**:
    - Stores user-specific categories in JSON format in the `user_categories` table.
    - Links categories to specific users via `user_id`.
    - Tracks creation and update timestamps.

2.  **Enhanced `CategoryManager` Class (`src/config/categories.py`)**:
    - Loads and caches default categories from `categories.yaml`.
    - Loads user-specific categories from the database when needed for a user.
    - Saves/updates custom categories to the database.
    - Provides methods to reset categories to defaults for a user (deletes DB record).
    - Handles merging/prioritizing user categories over defaults.

3.  **New Bot Commands (`src/bot/commands.py`, `src/bot/handlers.py`)**:
    - `/categorias`: Shows the user's currently active categories (custom or default).
    - `/editarcat`: Presents options (Import YAML, Export YAML) to modify categories.
    - `/resetcat`: Confirms and then resets the user's categories to the application defaults.

4.  **YAML Import/Export**:
    - `/editarcat` -> Export: Generates a YAML file with the user's current categories and sends it.
    - `/editarcat` -> Import: Handles user uploading a YAML file, validates its structure, and updates the database.

5.  **Button-Based Options**:
    - Confirmation dialogs for critical actions like `/resetcat`.
    - Clear options for choosing edit methods in `/editarcat`.
    - Guided file import/export process.

6.  **Document Handling**:
    - Processes uploaded YAML files (`application/x-yaml` or `.yaml` extension).
    - Creates downloadable category export files (`categories.yaml`).

### 12.3. Transaction Flow Integration
The transaction recording flow (`/agregar` command) has been updated to use each user's custom categories:

1.  When a user starts `/agregar`, the `CategoryManager` attempts to load their custom categories from the database.
2.  If custom categories exist, they are used to generate the category/subcategory selection buttons.
3.  If a user has no custom categories stored, the default categories from `categories.yaml` are used.
4.  The selected category/subcategory (whether custom or default) is recorded in the Google Sheet.

### 12.4. YAML Format for Categories
The system uses a simple YAML format for importing/exporting categories:

```yaml
# Example categories.yaml
expense_categories:
  HOGAR: # Category Name
    - Supermercado # Subcategory 1
    - Hipoteca / Alquiler # Subcategory 2
    - Electricidad
  TRANSPORTE:
    - Uber
    - Combustible
    - Transporte Público
# Add more expense categories as needed

income_categories:
  - Salario / Sueldos # Income Category 1
  - Ingresos por Intereses
  - Dividendos
# Add more income categories as needed
```

### 12.5. Future Improvements
1.  **Interactive Category Editor**: A direct category editor in Telegram (e.g., using inline keyboards) instead of YAML files.
2.  **Category Statistics**: Showing usage information per category.
3.  **Category Sharing**: Allowing users to share category sets with others.
4.  **Category Templates**: Predefined category sets for different user types.
5.  **Hierarchical Categories**: Support for multi-level category hierarchies beyond the current two levels.
6.  **Improved YAML Validation**: More specific error messages if the imported YAML is malformed.

This implementation makes the financial management system more flexible and adaptable to different users' needs, while maintaining a consistent and intuitive user experience.