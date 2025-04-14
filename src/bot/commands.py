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
        BotCommand("start", "Inicia el bot"),
        BotCommand("help", "Muestra ayuda sobre los comandos disponibles"),
        BotCommand("auth", "Autoriza acceso a tus hojas de Google"),
        BotCommand("sheet", "Selecciona una hoja de cálculo específica"),
        BotCommand("agregar", "Agrega una transacción financiera"),
        BotCommand("logout", "Cierra sesión y revoca acceso"),
        BotCommand("categorias", "Muestra tus categorías actuales"),
        BotCommand("editarcat", "Edita tus categorías personalizadas"),
        BotCommand("resetcat", "Reinicia tus categorías a los valores predeterminados"),
    ]
