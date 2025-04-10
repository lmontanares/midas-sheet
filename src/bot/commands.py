"""
Definición de comandos para el bot de Telegram.
"""

from telegram import BotCommand


def get_commands() -> list[BotCommand]:
    """
    Retorna la lista de comandos disponibles para el bot.

    Returns:
        Lista de comandos del bot
    """
    return [
        BotCommand("start", "Inicia el bot"),
        BotCommand("help", "Muestra ayuda sobre los comandos disponibles"),
        BotCommand("auth", "Autoriza acceso a tus hojas de Google"),
        BotCommand("sheet", "Selecciona una hoja de cálculo específica"),
        BotCommand("agregar", "Agrega una transacción financiera"),
        BotCommand("recargar", "Recarga las categorías desde el archivo de configuración"),
        BotCommand("logout", "Cierra sesión y revoca acceso"),
    ]
