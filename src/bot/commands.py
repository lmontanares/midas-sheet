"""
Telegram bot command definitions.
"""

from telegram import BotCommand


def get_commands() -> list[BotCommand]:
    """
    Returns the list of available bot commands for UI discoverability.

    Returns:
        List of bot commands
    """
    return [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help for available commands"),
        BotCommand("auth", "Authorize access to your Google Sheets"),
        BotCommand("sheet", "Select a specific spreadsheet"),
        BotCommand("add", "Add a financial transaction"),
        BotCommand("logout", "Log out and revoke access"),
        BotCommand("categories", "Show your current categories"),
        BotCommand("editcat", "Edit your custom categories"),
        BotCommand("resetcat", "Reset your categories to default values"),
    ]
