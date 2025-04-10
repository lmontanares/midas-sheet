"""
Punto de entrada principal de la aplicación de finanzas.

Este script inicia tanto el bot de Telegram como la conexión con Google Sheets.
"""

import functools
from pathlib import Path
from typing import Optional

from loguru import logger
from telegram.ext import ApplicationBuilder, ContextTypes

from src.auth.oauth import OAuthManager
from src.bot.auth_handlers import _send_auth_success_message
from src.bot.bot import TelegramBot
from src.server.oauth_server import OAuthServer
from src.sheets.client import GoogleSheetsClient
from src.sheets.operations import SheetsOperations
from src.utils.config import Config
from src.utils.logger import setup_logging


def main_oauth_callback_handler(
    state: str, code: str, oauth_manager: OAuthManager, sheets_client: GoogleSheetsClient, job_queue: ContextTypes.DEFAULT_TYPE.job_queue
) -> Optional[str]:
    """
    Handles the callback from the OAuth server within the main script's context.
    Exchanges code for token and schedules success message.

    Args:
        state: The state parameter from the callback URL.
        code: The authorization code from the callback URL.
        oauth_manager: Instance of OAuthManager.
        sheets_client: Instance of GoogleSheetsClient.
        job_queue: The application's job queue.

    Returns:
        user_id if successful, None otherwise.

    Raises:
        ValueError: If state is invalid.
        Exception: For other unexpected errors.
    """
    logger.info(f"Main OAuth callback received. Processing state: {state[:10]}...")
    try:
        # Exchange code, get user_id if successful. Raises ValueError on invalid state.
        user_id = oauth_manager.exchange_code(state, code)

        if user_id:
            logger.info(f"Code exchanged successfully via main callback for user {user_id}")

            # Immediately try to authenticate the gspread client to cache it
            try:
                client_instance = sheets_client._get_client(user_id)
                if client_instance:
                    logger.info(f"gspread client authenticated and cached via main callback for user {user_id}")
                else:
                    logger.error(f"Failed to get gspread client for user {user_id} immediately after token exchange.")
            except Exception as e:
                logger.exception(f"Error authenticating sheets_client for user {user_id} immediately after main callback: {e}")

            # Schedule sending the success message back to the user via JobQueue
            if job_queue:
                job_queue.run_once(
                    _send_auth_success_message,
                    when=1,
                    data={"user_id": user_id},
                    name=f"auth_success_{user_id}",
                )
                logger.debug(f"Scheduled auth success message job for user {user_id}")
            else:
                logger.error(f"JobQueue not available. Cannot schedule success message for user {user_id}.")

            return user_id
        else:
            logger.error(f"oauth_manager.exchange_code returned None unexpectedly for state {state}.")
            return None

    except ValueError as ve:
        logger.error(f"OAuth state validation failed during main callback: {ve}. State: {state}")
        raise  # Re-raise for the server to handle
    except Exception as e:
        logger.exception(f"Unhandled error processing main OAuth callback (state: {state}): {e}")
        raise  # Re-raise for the server to handle


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

        # Crear directorio de tokens si no existe
        tokens_dir = Path(config.oauth_tokens_dir)
        tokens_dir.mkdir(exist_ok=True, parents=True)

        # 1. Initialize OAuth Manager
        oauth_manager = OAuthManager(
            client_secrets_file=config.oauth_credentials_path,
            token_dir=config.oauth_tokens_dir,
            redirect_uri=config.oauth_redirect_uri,
            encryption_key=config.oauth_encryption_key,
        )
        logger.info("Gestor OAuth inicializado")

        # 2. Initialize Sheets Client
        sheets_client = GoogleSheetsClient(oauth_manager)
        logger.info("Cliente Google Sheets inicializado")

        # 3. Initialize Telegram Application
        application = ApplicationBuilder().token(config.telegram_token).build()
        logger.info("Telegram Application creada")

        # Add necessary components to bot_data
        application.bot_data["oauth_manager"] = oauth_manager
        application.bot_data["sheets_client"] = sheets_client

        # 4. Create the partial callback function
        callback_with_context = functools.partial(
            main_oauth_callback_handler,
            oauth_manager=oauth_manager,
            sheets_client=sheets_client,
            job_queue=application.job_queue,
        )

        # 5. Initialize the OAuth server with the partial callback
        oauth_server = OAuthServer(
            host=config.oauth_server_host,
            port=config.oauth_server_port,
            callback_handler=callback_with_context,
            redirect_uri=config.oauth_redirect_uri,
        )

        # Iniciar el servidor OAuth en un hilo separado
        oauth_server.start()
        logger.info(f"Servidor OAuth iniciado en {config.oauth_server_host}:{config.oauth_server_port}")

        # 6. Initialize Sheets Operations
        sheets_operations = SheetsOperations(sheets_client)
        logger.info("Operaciones de hojas de cálculo inicializadas")

        # 7. Initialize Telegram Bot
        bot = TelegramBot(config.telegram_token, sheets_operations, oauth_manager)

        # Add sheets_operations to bot_data
        application.bot_data["sheets_operations"] = sheets_operations

        # 8. Setup and run the bot using the existing application
        bot.setup(existing_application=application)
        logger.info("Bot de Telegram configurado, iniciando...")
        bot.run()  # This blocks until termination

    except Exception as e:
        logger.error(f"Error al iniciar la aplicación: {e}")
        raise
    finally:
        # Asegurar que el servidor OAuth se detenga correctamente
        try:
            if "oauth_server" in locals():
                oauth_server.stop()
                logger.info("Servidor OAuth detenido")
        except Exception as e:
            logger.error(f"Error al detener el servidor OAuth: {e}")


if __name__ == "__main__":
    main()
