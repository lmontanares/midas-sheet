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
        BotCommand("agregar", "Agrega una transacción financiera"),
        BotCommand("recargar", "Recarga las categorías desde el archivo de configuración"),
        # Aquí se añadirán más comandos en el futuro
    ]
