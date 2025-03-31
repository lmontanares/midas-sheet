"""
Manejadores de mensajes y comandos para el bot de Telegram.
"""

from typing import Any

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manejador para el comando /start.

    Args:
        update: Objeto Update de Telegram
        context: Contexto del manejador
    """
    user = update.effective_user
    await update.message.reply_text(f"¡Hola {user.first_name}! Soy el bot de gestión financiera.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manejador para el comando /help.

    Args:
        update: Objeto Update de Telegram
        context: Contexto del manejador
    """
    help_text = """
    *Comandos disponibles:*
    /start - Inicia el bot
    /help - Muestra este mensaje de ayuda

    Pronto se agregarán más funciones...
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def error_handler(update: Update | None, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manejador global de errores.

    Args:
        update: Objeto Update de Telegram o None
        context: Contexto con información del error
    """
    logger.exception(f"Error: {context.error} - Update: {update}")

    if update and update.effective_message:
        await update.effective_message.reply_text("Ha ocurrido un error. Por favor, intenta nuevamente más tarde.")
