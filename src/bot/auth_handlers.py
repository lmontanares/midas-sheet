from typing import Optional  # Added import for Optional

from google.auth.exceptions import GoogleAuthError
from gspread.exceptions import APIError, SpreadsheetNotFound
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..auth.oauth import OAuthManager  # Assuming OAuthManager is correctly imported
from ..db.database import SessionLocal, User, UserSheet
from ..sheets.operations import SheetsOperations

# --- Helper Functions ---


def _upsert_user_details(db: Session, user_id: str, effective_user: Update.effective_user) -> None:
    """Creates or updates user details in the database."""
    if not effective_user:
        return  # Cannot update if no user info available

    try:
        stmt = select(User).where(User.user_id == user_id)
        user = db.scalars(stmt).first()

        if user:
            # Update existing user if details changed
            updated = False
            if user.telegram_username != effective_user.username:
                user.telegram_username = effective_user.username
                updated = True
            if user.first_name != effective_user.first_name:
                user.first_name = effective_user.first_name
                updated = True
            if user.last_name != effective_user.last_name:
                user.last_name = effective_user.last_name
                updated = True
            if updated:
                # updated_at is handled by DB onupdate trigger
                logger.debug(f"Updating user details in DB for {user_id}")
                db.flush()  # Flush changes
        else:
            # Create new user (should ideally be created during initial auth exchange)
            logger.warning(f"User {user_id} not found during detail upsert. Creating.")
            new_user = User(
                user_id=user_id,
                telegram_username=effective_user.username,
                first_name=effective_user.first_name,
                last_name=effective_user.last_name,
            )
            db.add(new_user)
            db.flush()  # Flush to make user available

    except Exception as e:
        logger.error(f"Error upserting user details for {user_id}: {e}")
        db.rollback()  # Rollback on error
        # Decide whether to raise or just log


def _set_active_sheet(db: Session, user_id: str, spreadsheet_id: str, spreadsheet_title: Optional[str]) -> bool:
    """Sets the active spreadsheet for the user in the database."""
    try:
        # Deactivate any existing active sheets for this user first
        stmt_deactivate = (
            update(UserSheet)
            .where(UserSheet.user_id == user_id, UserSheet.is_active == True)  # noqa: E712
            .values(is_active=False)
        )
        db.execute(stmt_deactivate)

        # Check if this specific sheet association already exists
        stmt_select = select(UserSheet).where(UserSheet.user_id == user_id, UserSheet.spreadsheet_id == spreadsheet_id)
        existing_sheet = db.scalars(stmt_select).first()

        if existing_sheet:
            # Reactivate and update title if necessary
            existing_sheet.is_active = True
            existing_sheet.spreadsheet_title = spreadsheet_title
            logger.debug(f"Reactivated sheet {spreadsheet_id} for user {user_id}")
        else:
            # Insert new active sheet
            new_sheet = UserSheet(
                user_id=user_id,
                spreadsheet_id=spreadsheet_id,
                spreadsheet_title=spreadsheet_title,
                is_active=True,
            )
            db.add(new_sheet)
            logger.debug(f"Set new active sheet {spreadsheet_id} for user {user_id}")

        db.commit()
        return True
    except IntegrityError as e:
        logger.error(f"Database integrity error setting active sheet for user {user_id}: {e}")
        db.rollback()
        return False
    except Exception as e:
        logger.error(f"Error setting active sheet {spreadsheet_id} for user {user_id}: {e}")
        db.rollback()
        return False


# --- Command Handlers ---


async def auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /auth command to initiate the OAuth 2.0 flow.
    Generates an authorization link and sends it to the user.
    Ensures user details are updated in the DB.
    """
    if not update.effective_user or not update.message:
        logger.warning("Cannot process /auth: effective_user or message is None.")
        return

    user_id = str(update.effective_user.id)
    oauth_manager: Optional[OAuthManager] = context.bot_data.get("oauth_manager")

    if not oauth_manager:
        logger.error("OAuthManager not found in bot_data.")
        await update.message.reply_text(
            "Error interno: El servicio de autenticación no está configurado correctamente. Por favor, contacta al administrador."
        )
        return

    # Upsert user details (username, name) every time /auth is called
    db: Session | None = None
    try:
        db = SessionLocal()
        _upsert_user_details(db, user_id, update.effective_user)
        db.commit()  # Commit user detail changes
    except Exception as e:
        logger.error(f"Failed to upsert user details for {user_id} during /auth: {e}")
        # Continue with auth flow even if user detail update fails
        if db:
            db.rollback()
    finally:
        if db:
            db.close()

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


async def sheet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /sheet command to select an active spreadsheet and store it in the DB."""
    if not update.effective_user or not update.message:
        return
    user_id = str(update.effective_user.id)
    sheets_operations: Optional[SheetsOperations] = context.bot_data.get("sheets_operations")
    oauth_manager: Optional[OAuthManager] = context.bot_data.get("oauth_manager")

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
    db: Session | None = None
    try:
        wait_message = await update.message.reply_text(f"Verificando y configurando hoja '{spreadsheet_id}'...")

        # setup_for_user now only verifies access and returns the title
        spreadsheet_title = sheets_operations.setup_for_user(user_id, spreadsheet_id)

        if spreadsheet_title:
            # Store the active sheet ID and title in the database
            db = SessionLocal()
            success = _set_active_sheet(db, user_id, spreadsheet_id, spreadsheet_title)
            if success:
                # context.user_data["active_spreadsheet_id"] = spreadsheet_id # Removed
                # context.user_data["active_spreadsheet_title"] = spreadsheet_title # Removed

                await wait_message.edit_text(
                    f"✅ Hoja de cálculo *{spreadsheet_title}* seleccionada.\n\nAhora puedes usar comandos como /agregar en esta hoja.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                logger.info(f"User {user_id} selected spreadsheet {spreadsheet_id} ('{spreadsheet_title}') and saved to DB.")
            else:
                await wait_message.edit_text(
                    f"❌ Se verificó la hoja '{spreadsheet_title}', pero hubo un error al guardarla como activa. Intenta de nuevo."
                )

        else:
            # This case implies setup_for_user returned None (likely auth issue handled internally)
            # Error should have been raised by setup_for_user if it was API/NotFound
            await wait_message.edit_text(
                f"❌ No se pudo verificar el acceso a la hoja con ID: {spreadsheet_id}. Asegúrate de estar autenticado (/auth) y tener permisos."
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
    finally:
        if db:
            db.close()


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /logout command to revoke access and clear local/DB data."""
    if not update.effective_user or not update.message:
        return
    user_id = str(update.effective_user.id)
    oauth_manager: OAuthManager | None = context.bot_data.get("oauth_manager")
    sheets_client = context.bot_data.get("sheets_client")  # Keep for cache clearing

    if not oauth_manager:
        logger.error("OAuthManager not found in bot_data for /logout.")
        await update.message.reply_text("Error interno: Servicio no disponible.")
        return

    # Check if authenticated *before* attempting logout
    # No need to check token file existence anymore
    is_auth = oauth_manager.is_authenticated(user_id)
    if not is_auth:
        # Check if a token exists in DB anyway (maybe expired/invalid)
        token_data = oauth_manager.load_token(user_id)
        if token_data:
            logger.info(f"User {user_id} is not authenticated but token exists in DB. Proceeding with cleanup.")
        else:
            await update.message.reply_text("No has iniciado sesión. No hay nada que cerrar.")
            return

    db: Session | None = None
    try:
        logger.info(f"Attempting logout for user {user_id}")
        # Revoke token with Google and delete from DB
        revoked = oauth_manager.revoke_token(user_id)

        if revoked:
            logger.info(f"Token revocation/cleanup successful for user {user_id}")
        else:
            logger.warning(f"Token revocation/cleanup might have failed for user {user_id}, but proceeding with local data clear.")

        # --- Clear local user data ---
        # Clear selected sheet from user_data (REMOVED)
        # cleared_keys = []
        # if "active_spreadsheet_id" in context.user_data:
        #     del context.user_data["active_spreadsheet_id"]
        #     cleared_keys.append("active_spreadsheet_id")
        # if "active_spreadsheet_title" in context.user_data:
        #     del context.user_data["active_spreadsheet_title"]
        #     cleared_keys.append("active_spreadsheet_title")
        # if cleared_keys:
        #     logger.debug(f"Cleared keys from user_data for {user_id}: {cleared_keys}")

        # Deactivate user sheet association in DB
        try:
            db = SessionLocal()
            stmt_deactivate = (
                update(UserSheet)
                .where(UserSheet.user_id == user_id, UserSheet.is_active == True)  # noqa: E712
                .values(is_active=False)
            )
            result = db.execute(stmt_deactivate)
            db.commit()
            if result.rowcount > 0:
                logger.info(f"Deactivated sheet association in DB for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to deactivate sheet association for user {user_id}: {e}")
            if db:
                db.rollback()
        finally:
            if db:
                db.close()

        # Clear client cache in SheetsClient instance
        if sheets_client and hasattr(sheets_client, "clear_user_cache"):
            sheets_client.clear_user_cache(user_id)
            logger.debug(f"Cleared sheets_client cache for user {user_id}")
        else:
            logger.debug("SheetsClient or clear_user_cache method not found, skipping cache clear.")

        # sheets_operations.clear_user_data() was removed

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
            "• Usar /sheet <ID> para seleccionar una hoja.\n"
            "• Usar /agregar para registrar transacciones.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        # Catch specific Telegram errors if needed (e.g., BadRequest if user blocked bot)
        logger.error(f"Failed to send auth success message to user {user_id}: {e}")
