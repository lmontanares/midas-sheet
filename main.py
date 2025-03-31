"""
Punto de entrada principal de la aplicación de finanzas.

Este script inicia tanto el bot de Telegram como la conexión con Google Sheets.
"""

from pathlib import Path

from loguru import logger

from src.bot.bot import TelegramBot
from src.sheets.client import GoogleSheetsClient
from src.sheets.operations import SheetsOperations
from src.utils.config import Config
from src.utils.logger import setup_logging


def main() -> None:
    """
    Función principal que inicia la aplicación.
    """
    # Configurar logging
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    setup_logging(log_dir / "app.log")

    try:
        # Cargar configuración
        config = Config()

        # Inicializar el cliente de Google Sheets
        sheets_client = GoogleSheetsClient(config.google_credentials_path)
        sheets_client.authenticate()

        # Inicializar operaciones de hojas de cálculo
        sheets = SheetsOperations(sheets_client, config.spreadsheet_id)
        sheets.setup()

        # Inicializar y ejecutar el bot de Telegram
        bot = TelegramBot(config.telegram_token, sheets)
        bot.setup()
        bot.run()

    except Exception as e:
        logger.error(f"Error al iniciar la aplicación: {e}")
        raise


if __name__ == "__main__":
    main()
