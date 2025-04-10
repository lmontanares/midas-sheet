"""
Configuración principal del bot de Telegram.
"""

from loguru import logger
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from ..auth.oauth import OAuthManager
from ..sheets.client import GoogleSheetsClient  # Added for type hint or access
from ..sheets.operations import SheetsOperations
from .handlers import (
    add_command,
    amount_handler,
    auth_command,
    button_callback,
    comment_handler,
    error_handler,
    help_command,
    logout_command,
    register_bot_commands,
    reload_command,
    sheet_command,
    start_command,
)


class TelegramBot:
    """
    Clase principal para el bot de Telegram.

    Maneja la configuración y ejecución del bot.
    """

    def __init__(self, token: str, sheets: SheetsOperations, oauth_manager: OAuthManager) -> None:
        """
        Inicializa el bot de Telegram.

        Args:
            token: Token de acceso del bot de Telegram.
            sheets: Operaciones para la hoja de cálculo.
            oauth_manager: Gestor de OAuth para autenticación.
        """
        self.token = token
        self.sheets = sheets
        self.oauth_manager = oauth_manager

        self.application: Application | None = None

    def setup(self, existing_application: Application) -> None:
        """
        Configura el bot utilizando una instancia de Application existente.

        Args:
            existing_application: La instancia de Application preconfigurada.
        """
        # Usar la aplicación existente
        self.application = existing_application

        # Asegurar que las referencias necesarias estén en bot_data
        # (Puede ser redundante si main.py ya las añadió, pero es seguro)
        self.application.bot_data["sheets_operations"] = self.sheets
        self.application.bot_data["oauth_manager"] = self.oauth_manager

        # Añadir sheets_client si es necesario para otros handlers
        if isinstance(self.sheets.client, GoogleSheetsClient):
            self.application.bot_data["sheets_client"] = self.sheets.client

        # Registrar manejadores de comandos básicos
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("agregar", add_command))
        self.application.add_handler(CommandHandler("recargar", reload_command))

        # Registrar manejadores para OAuth
        self.application.add_handler(CommandHandler("auth", auth_command))
        self.application.add_handler(CommandHandler("login", auth_command))  # Alias
        # Removed list_command handler
        self.application.add_handler(CommandHandler("sheet", sheet_command))
        self.application.add_handler(CommandHandler("logout", logout_command))

        # Manejador para callbacks de botones
        self.application.add_handler(CallbackQueryHandler(button_callback))

        # Implementamos un sistema de estados mediante user_data para manejar la conversación

        # Luego registramos el manejador para los comentarios
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE, comment_handler, block=True),
            group=1,  # Grupo 1 tiene prioridad sobre grupo 2
        )

        # Finalmente registramos el manejador para los montos (prioridad más baja)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE, amount_handler, block=True), group=2
        )

        # Registrar manejador de errores
        self.application.add_error_handler(error_handler)

        # Añadir un post_init callback para registrar los comandos del bot de forma asíncrona
        self.application.post_init = register_bot_commands

        logger.info("Bot configurado utilizando la aplicación existente")

    def run(self) -> None:
        """
        Inicia el bot de Telegram.

        Raises:
            RuntimeError: Si el bot no ha sido configurado
        """
        if not self.application:
            # Este error no debería ocurrir si setup() se llama correctamente desde main
            raise RuntimeError("La aplicación del bot no está inicializada. Llama a setup() primero.")

        logger.info("Iniciando bot...")
        self.application.run_polling()

    def stop(self):
        """Stop the bot properly"""
        if self.application:
            self.application.stop()
