"""
Main Telegram bot configuration.
"""

from loguru import logger
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from ..auth.oauth import OAuthManager
from ..sheets.client import GoogleSheetsClient
from ..sheets.operations import SheetsOperations
from .auth_handlers import auth_command, logout_command, sheet_command
from .handlers import (
    add_command,
    amount_handler,
    button_callback,
    comment_handler,
    edit_categories_command,
    error_handler,
    help_command,
    process_yaml_import,
    register_bot_commands,
    reload_command,
    reset_categories_command,
    show_categories_command,
    start_command,
)


class TelegramBot:
    """
    Main Telegram bot class.

    Handles bot configuration and execution.
    """

    def __init__(self, token: str, sheets: SheetsOperations, oauth_manager: OAuthManager) -> None:
        """
        Initializes the Telegram bot with required components for proper operation.

        Args:
            token: Telegram bot access token.
            sheets: Sheet operations handler.
            oauth_manager: OAuth manager for authentication.
        """
        self.token = token
        self.sheets = sheets
        self.oauth_manager = oauth_manager

        self.application: Application | None = None

    def setup(self, existing_application: Application) -> None:
        """
        Configures the bot with an existing Application instance for flexibility.

        Args:
            existing_application: Preconfigured Application instance.
        """
        self.application = existing_application

        # Ensure required references are in bot_data
        self.application.bot_data["sheets_operations"] = self.sheets
        self.application.bot_data["oauth_manager"] = self.oauth_manager

        # Add sheets_client if needed for handlers
        if isinstance(self.sheets.client, GoogleSheetsClient):
            self.application.bot_data["sheets_client"] = self.sheets.client

        # Register basic command handlers
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("agregar", add_command))

        # Register OAuth handlers
        self.application.add_handler(CommandHandler("auth", auth_command))
        self.application.add_handler(CommandHandler("login", auth_command))  # Alias
        self.application.add_handler(CommandHandler("sheet", sheet_command))
        self.application.add_handler(CommandHandler("logout", logout_command))

        # Register category management handlers
        self.application.add_handler(CommandHandler("categorias", show_categories_command))
        self.application.add_handler(CommandHandler("editarcat", edit_categories_command))
        self.application.add_handler(CommandHandler("resetcat", reset_categories_command))

        # Button callback handler
        self.application.add_handler(CallbackQueryHandler(button_callback))

        # Implement state system using user_data for conversation management

        # Register comment handler with higher priority
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE, comment_handler, block=True),
            group=1,
        )

        # Register amount handler with lower priority
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE, amount_handler, block=True), group=2
        )

        # Register file handler for category import
        self.application.add_handler(MessageHandler(filters.Document.ALL & filters.UpdateType.MESSAGE, process_yaml_import, block=True), group=3)

        # Register error handler
        self.application.add_error_handler(error_handler)

        # Add post_init callback for asynchronous command registration
        self.application.post_init = register_bot_commands

        logger.info("Bot configured using existing application")

    def run(self) -> None:
        """
        Starts the Telegram bot to begin processing messages.

        Raises:
            RuntimeError: If the bot has not been configured
        """
        if not self.application:
            raise RuntimeError("Bot application not initialized. Call setup() first.")

        logger.info("Starting bot...")
        self.application.run_polling()

    def stop(self):
        """Stop the bot properly to prevent resource leaks"""
        if self.application:
            self.application.stop()
