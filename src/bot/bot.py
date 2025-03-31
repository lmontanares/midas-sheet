"""
Configuración principal del bot de Telegram.
"""

from loguru import logger
from telegram.ext import Application, ApplicationBuilder, CommandHandler

from ..sheets.operations import SheetsOperations
from .commands import get_commands
from .handlers import add_command, error_handler, help_command, start_command


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

        # Registrar manejadores de comandos
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("agregar", add_command))

        # Guardar referencia a SheetsOperations para usar en los manejadores
        self.application.bot_data["sheets_operations"] = self.sheets

        # Registrar manejador de errores
        self.application.add_error_handler(error_handler)

        # Establecer los comandos en el menú del bot
        self.application.bot.set_my_commands(get_commands())

        logger.info("Bot configurado correctamente")

    def run(self) -> None:
        """
        Inicia el bot de Telegram.

        Raises:
            RuntimeError: Si el bot no ha sido configurado
        """
        if not self.application:
            raise RuntimeError("El bot debe ser configurado antes de ejecutarse")

        logger.info("Iniciando bot...")
        self.application.run_polling()

    def stop(self):
        """Stop the bot properly"""
        if self.application:
            self.application.stop()
