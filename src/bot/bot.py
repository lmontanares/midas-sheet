"""
Configuración principal del bot de Telegram.
"""

from loguru import logger
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from ..sheets.operations import SheetsOperations
from .handlers import (
    add_command,
    amount_handler,
    button_callback,
    comment_handler,
    error_handler,
    help_command,
    register_bot_commands,
    reload_command,
    start_command,
)


class TelegramBot:
    """
    Clase principal para el bot de Telegram.

    Maneja la configuración y ejecución del bot.
    """

    def __init__(self, token: str, sheets: SheetsOperations) -> None:
        """
        Inicializa el bot de Telegram.

        Args:
            token: Token de acceso del bot de Telegram
            sheets: Operaciones para la hoja de cálculo
        """
        self.token = token
        self.sheets = sheets
        self.application: Application | None = None

    def setup(self) -> None:
        """
        Configura el bot con los manejadores necesarios.
        """
        # Crear la aplicación
        self.application = ApplicationBuilder().token(self.token).build()

        # Guardar referencia a SheetsOperations para usar en los manejadores
        self.application.bot_data["sheets_operations"] = self.sheets

        # Registrar manejadores de comandos
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("agregar", add_command))
        self.application.add_handler(CommandHandler("recargar", reload_command))

        # Manejador para callbacks de botones
        self.application.add_handler(CallbackQueryHandler(button_callback))

        # Implementamos un sistema de estados mediante user_data para manejar la conversación
        # Primero registramos el manejador para los comentarios (prioridad más alta)
        # porque si estamos esperando un comentario, necesitamos capturarlo
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE,
                comment_handler,
                block=True
            ),
            group=1  # Grupo 1 tiene prioridad sobre grupo 2
        )
        
        # Luego registramos el manejador para los montos (prioridad más baja)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE,
                amount_handler,
                block=True
            ),
            group=2
        )

        # Registrar manejador de errores
        self.application.add_error_handler(error_handler)
        
        # Añadir un post_init callback para registrar los comandos del bot de forma asíncrona
        self.application.post_init = register_bot_commands

        logger.info("Bot configurado correctamente")

    def run(self) -> None:
        """
        Inicia el bot de Telegram.

        Raises:
            RuntimeError: Si el bot no ha sido configurado
        """
        if not self.application:
            self.setup()

        logger.info("Iniciando bot...")
        self.application.run_polling()

    def stop(self):
        """Stop the bot properly"""
        if self.application:
            self.application.stop()
