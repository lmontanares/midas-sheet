# src/bot/auth_handlers.py (Revised)

import asyncio  # For scheduling message sending
from functools import partial  # Needed if passing context to callback handler externally
from typing import Optional  # Added Optional for type hint

from google.auth.exceptions import GoogleAuthError  # Import specific exceptions
from gspread.exceptions import APIError, SpreadsheetNotFound  # Import specific exceptions
from loguru import logger
from telegram import Update
from telegram.constants import ParseMode  # Explicit import
from telegram.ext import ContextTypes, JobQueue  # Added JobQueue potentially

# Assuming these types are available via imports in the actual context
# from ..auth.oauth import OAuthManager
# from ..sheets.operations import SheetsOperations
# from ..sheets.client import GoogleSheetsClient

# --- Command Handlers ---


async def auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /auth command to initiate the OAuth 2.0 flow.
    Generates an authorization link and sends it to the user.
    """
    if not update.effective_user or not update.message:
        logger.warning("Cannot process /auth: effective_user or message is None.")
        return

    user_id = str(update.effective_user.id)
    oauth_manager = context.bot_data.get("oauth_manager")

    if not oauth_manager:
        logger.error("OAuthManager not found in bot_data.")
        await update.message.reply_text(
            "Error interno: El servicio de autenticación no está configurado correctamente. Por favor, contacta al administrador."
        )
        return

    # Check if already authenticated
    if oauth_manager.is_authenticated(user_id):
        await update.message.reply_text("Ya estás autenticado 👍. Puedes usar /sheet <ID> para seleccionar una hoja o /logout para desconectar.")
        return

    try:
        # Generate URL (state is handled internally by OAuthManager now)
        auth_url, state = oauth_manager.generate_auth_url(user_id)
        # State is logged within generate_auth_url now

        # Send link to user
        await update.message.reply_text(
            f"🔐 *Autorización Requerida*\n\n"
            f"Para conectar tu cuenta de Google Sheets, por favor sigue estos pasos:\n\n"
            f"1. Haz clic en el enlace de abajo.\n"
            f"2. Autoriza el acceso en la página de Google.\n"
            f"3. Serás redirigido a una página de confirmación.\n\n"
            f"[Autorizar Acceso a Google Sheets]({auth_url})\n\n"
            f"_Este enlace es único y válido por un corto tiempo._",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,  # Good practice for auth links
        )
        logger.info(f"Authorization link sent to user {user_id}")

    except Exception as e:
        logger.exception(f"Error generating authorization URL for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Ocurrió un error al iniciar el proceso de autorización. Por favor, intenta nuevamente más tarde con /auth."
        )


# Removed code_handler - manual code pasting is deprecated
# Removed list_command function
async def sheet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /sheet command to select an active spreadsheet."""
    if not update.effective_user or not update.message:
        return
    user_id = str(update.effective_user.id)
    sheets_operations = context.bot_data.get("sheets_operations")
    oauth_manager = context.bot_data.get("oauth_manager")

    if not sheets_operations or not oauth_manager:
        logger.error("SheetsOperations or OAuthManager not found in bot_data for /sheet.")
        await update.message.reply_text("Error interno: Servicio no disponible.")
        return

    if not oauth_manager.is_authenticated(user_id):
        await update.message.reply_text("⚠️ Debes autenticarte primero usando /auth.")
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text("⚠️ Uso incorrecto. Proporciona el ID de la hoja.\nEjemplo: `/sheet TU_SHEET_ID_AQUI`")
        return

    spreadsheet_id = context.args[0].strip()
    wait_message = None
    try:
        wait_message = await update.message.reply_text(f"Verificando y configurando hoja '{spreadsheet_id}'...")

        # sheets_operations.setup_for_user should use the updated client internally
        # It should raise exceptions on failure (e.g., SpreadsheetNotFound, APIError)
        spreadsheet_title = sheets_operations.setup_for_user(user_id, spreadsheet_id)

        if spreadsheet_title:
            # Store the active sheet ID in user_data (consider if this is still needed)
            context.user_data["active_spreadsheet_id"] = spreadsheet_id
            context.user_data["active_spreadsheet_title"] = spreadsheet_title  # Store title from setup

            await wait_message.edit_text(
                f"✅ Hoja de cálculo *{spreadsheet_title}* seleccionada.\n\nAhora puedes usar comandos como /agregar en esta hoja.",
                parse_mode=ParseMode.MARKDOWN,
            )
            logger.info(f"User {user_id} selected spreadsheet {spreadsheet_id} ('{spreadsheet_title}')")
        else:
            # This case implies setup_for_user returned None/False without error, adjust based on its impl.
            await wait_message.edit_text(
                f"❌ No se pudo configurar la hoja con ID: {spreadsheet_id}. Verifica el ID y que tengas acceso a ella en Google Sheets."
            )

    except SpreadsheetNotFound:
        logger.warning(f"SpreadsheetNotFound error for user {user_id}, sheet_id {spreadsheet_id}")
        error_msg = f"❌ Hoja no encontrada o inaccesible (ID: {spreadsheet_id}). Verifica el ID y tus permisos."
        if wait_message:
            await wait_message.edit_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
    except (APIError, GoogleAuthError) as e:
        logger.error(f"API/Auth error setting sheet {spreadsheet_id} for user {user_id}: {e}")
        error_msg = f"❌ Error al acceder a la hoja '{spreadsheet_id}'."
        if "PERMISSION_DENIED" in str(e):
            error_msg += " Permiso denegado."
        elif "invalid_grant" in str(e) or isinstance(e, GoogleAuthError):
            error_msg = "❌ Error de autenticación. Intenta /auth de nuevo."
        else:
            error_msg += " Intenta de nuevo más tarde."
        if wait_message:
            await wait_message.edit_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
    except Exception as e:
        logger.exception(f"Unexpected error setting spreadsheet {spreadsheet_id} for user {user_id}: {e}")
        error_msg = f"❌ Error inesperado al configurar la hoja '{spreadsheet_id}'."
        if wait_message:
            await wait_message.edit_text(error_msg)
        else:
            await update.message.reply_text(error_msg)


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /logout command to revoke access and clear local data."""
    if not update.effective_user or not update.message:
        return
    user_id = str(update.effective_user.id)
    oauth_manager = context.bot_data.get("oauth_manager")
    sheets_client = context.bot_data.get("sheets_client")  # Get client if stored directly

    if not oauth_manager:
        logger.error("OAuthManager not found in bot_data for /logout.")
        await update.message.reply_text("Error interno: Servicio no disponible.")
        return

    # Check if authenticated *before* attempting logout
    is_auth = oauth_manager.is_authenticated(user_id)
    if not is_auth:
        # Check if a token file exists anyway (maybe expired/invalid)
        token_path = oauth_manager._get_token_path(user_id)  # Access internal method carefully
        if token_path.exists():
            logger.info(f"User {user_id} is not authenticated but token file exists. Proceeding with cleanup.")
        else:
            await update.message.reply_text("No has iniciado sesión. No hay nada que cerrar.")
            return

    try:
        logger.info(f"Attempting logout for user {user_id}")
        # Revoke token with Google and delete local file
        revoked = oauth_manager.revoke_token(user_id)

        if revoked:
            logger.info(f"Token revocation/cleanup successful for user {user_id}")
        else:
            logger.warning(f"Token revocation/cleanup might have failed for user {user_id}, but proceeding with local data clear.")

        # --- Clear local user data ---
        # Clear selected sheet from user_data
        cleared_keys = []
        if "active_spreadsheet_id" in context.user_data:
            del context.user_data["active_spreadsheet_id"]
            cleared_keys.append("active_spreadsheet_id")
        if "active_spreadsheet_title" in context.user_data:
            del context.user_data["active_spreadsheet_title"]
            cleared_keys.append("active_spreadsheet_title")
        # Removed context.user_data["oauth"] cleanup
        if cleared_keys:
            logger.debug(f"Cleared keys from user_data for {user_id}: {cleared_keys}")

        # Clear client cache in SheetsClient instance
        if sheets_client and hasattr(sheets_client, "clear_user_cache"):
            sheets_client.clear_user_cache(user_id)
            logger.debug(f"Cleared sheets_client cache for user {user_id}")
        else:
            logger.debug("SheetsClient or clear_user_cache method not found, skipping cache clear.")

        # Clear any user-specific state in SheetsOperations if applicable
        sheets_operations = context.bot_data.get("sheets_operations")
        if sheets_operations and hasattr(sheets_operations, "clear_user_data"):
            sheets_operations.clear_user_data(user_id)
            logger.debug(f"Called clear_user_data on sheets_operations for user {user_id}")

        await update.message.reply_text(
            "✅ Has cerrado sesión correctamente.\n\n"
            "El acceso a tu cuenta de Google ha sido revocado para este bot, "
            "y tus datos locales han sido eliminados.\n\n"
            "Usa /auth si deseas volver a conectar."
        )
        logger.info(f"Logout completed for user {user_id}")

    except Exception as e:
        logger.exception(f"Error during logout for user {user_id}: {e}")
        await update.message.reply_text("❌ Ocurrió un error al cerrar sesión. Por favor, intenta nuevamente.")


# --- OAuth Callback Handling Logic ---


async def _send_auth_success_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job to send the success message after OAuth callback."""
    job_data = context.job.data if context.job else {}
    user_id = job_data.get("user_id")
    if not user_id:
        logger.error("Job data missing user_id for sending success message.")
        return

    logger.info(f"Sending delayed auth success message to user {user_id}")
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ *Autorización Exitosa*\n\n"
            "Has conectado tu cuenta de Google Sheets correctamente.\n\n"
            "Ahora puedes:\n"
            # Removed reference to /list
            "• Usar /sheet <ID> para seleccionar una hoja.\n"
            "• Usar /agregar para registrar transacciones.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        # Catch specific Telegram errors if needed (e.g., BadRequest if user blocked bot)
        logger.error(f"Failed to send auth success message to user {user_id}: {e}")


def oauth_callback_handler(state: str, code: str, context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
    """
    Handles the callback from the OAuth server. Exchanges code for token.
    This function is passed to OAuthServer during initialization.

    Args:
        state: The state parameter from the callback URL.
        code: The authorization code from the callback URL.
        context: The bot's application context (passed via functools.partial or similar).

    Returns:
        user_id if successful, None otherwise (signals failure to the server).

    Raises:
        ValueError: If state is invalid (propagated from OAuthManager).
        Exception: For other unexpected errors during exchange or client auth.
                   These will be caught by the server's route handler.
    """
    oauth_manager = context.bot_data.get("oauth_manager")
    sheets_client = context.bot_data.get("sheets_client")  # Get client if stored directly
    job_queue = context.application.job_queue

    if not oauth_manager:
        logger.critical("CRITICAL: OAuthManager not available in oauth_callback_handler. Cannot process callback.")
        # Returning None signals failure, server shows generic error.
        # Cannot raise here easily without context of what server expects.
        return None

    logger.info(f"OAuth callback received. Processing state: {state[:10]}...")
    # Exceptions are handled by the server route that calls this handler

    # Exchange code, get user_id if successful. Raises ValueError on invalid state.
    user_id = oauth_manager.exchange_code(state, code)  # Can raise exceptions

    if user_id:
        logger.info(f"Code exchanged successfully via callback for user {user_id}")

        # Immediately try to authenticate the gspread client to cache it
        if sheets_client:
            try:
                # _get_client handles fetching credentials and authorizing gspread
                client_instance = sheets_client._get_client(user_id)  # Can raise exceptions
                if client_instance:
                    logger.info(f"gspread client authenticated and cached via callback for user {user_id}")
                else:
                    # This implies get_credentials failed after successful exchange_code
                    logger.error(f"Failed to get gspread client for user {user_id} immediately after token exchange (get_credentials likely failed).")
                    # Still schedule success message, but log error. User might need /auth again later.
            except Exception as e:
                # Log error but don't block the success message scheduling
                logger.exception(f"Error authenticating sheets_client for user {user_id} immediately after callback: {e}")

        # Schedule sending the success message back to the user via JobQueue
        if job_queue:
            job_queue.run_once(
                _send_auth_success_message,
                when=1,  # Run 1 second later
                data={"user_id": user_id},
                name=f"auth_success_{user_id}",  # Unique job name
            )
            logger.debug(f"Scheduled auth success message job for user {user_id}")
        else:
            logger.error("JobQueue not available in context. Cannot schedule success message for user {user_id}.")
            # Consider alternative notification? Difficult without job queue.

        return user_id  # Signal success to the OAuthServer

    else:
        # Should not happen if exchange_code raises exceptions on failure
        logger.error(f"oauth_manager.exchange_code returned None unexpectedly for state {state}.")
        return None  # Signal failure

    # ValueError (invalid state) and other exceptions from exchange_code or _get_client
    # will propagate up to the server's route handler, which will log them
    # and return an error page. No need to catch them explicitly here unless
    # we want to perform specific cleanup *before* the server handles it.
    # except ValueError as ve:
    #     logger.error(f"OAuth state validation failed during callback: {ve}. State: {state}")
    #     raise # Re-raise for the server
    # except Exception as e:
    #     logger.exception(f"Unhandled error processing OAuth callback (state: {state}): {e}")
    #     raise # Re-raise for the server
