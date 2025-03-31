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
        BotCommand("add", "Agrega una transacción financiera"),
        # Aquí se añadirán más comandos en el futuro
    ]
