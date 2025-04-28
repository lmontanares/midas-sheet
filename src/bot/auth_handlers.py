from google.auth.exceptions import GoogleAuthError
from gspread.exceptions import APIError, SpreadsheetNotFound
from loguru import logger
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..auth.oauth import OAuthManager
from ..db.database import SessionLocal, User, UserSheet
from ..sheets.operations import SheetsOperations

# --- Helper Functions ---


def _upsert_user_details(db: Session, user_id: str, effective_user: Update.effective_user) -> None:
    """Keeps user details updated for persistent contact information."""
    if not effective_user:
        return

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
                logger.debug(f"Updating user details in DB for {user_id}")
                db.flush()
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
            db.flush()

    except Exception as e:
        logger.error(f"Error upserting user details for {user_id}: {e}")
        db.rollback()


def _set_active_sheet(db: Session, user_id: str, spreadsheet_id: str, spreadsheet_title: str | None) -> bool:
    """Sets active spreadsheet in database for persistent user preferences."""
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
            # Check if user has any other sheets and delete them
            stmt_delete = delete(UserSheet).where(UserSheet.user_id == user_id)
            db.execute(stmt_delete)

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
    Initiates OAuth 2.0 flow for secure Google Sheets access.
    Generates authorization link and updates user details in DB.
    """
    if not update.effective_user or not update.message:
        logger.warning("Cannot process /auth: effective_user or message is None.")
        return

    user_id = str(update.effective_user.id)
    oauth_manager: OAuthManager | None = context.bot_data.get("oauth_manager")

    if not oauth_manager:
        logger.error("OAuthManager not found in bot_data.")
        await update.message.reply_text("Internal error: Authentication service is not properly configured. Please contact the administrator.")
        return

    # Upsert user details (username, name) every time /auth is called
    db: Session | None = None
    try:
        db = SessionLocal()
        _upsert_user_details(db, user_id, update.effective_user)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to upsert user details for {user_id} during /auth: {e}")
        if db:
            db.rollback()
    finally:
        if db:
            db.close()

    # Check if already authenticated
    if oauth_manager.is_authenticated(user_id):
        await update.message.reply_text("You're already authenticated 👍. You can use /sheet <ID> to select a sheet or /logout to disconnect.")
        return

    try:
        # Generate URL (state is handled internally by OAuthManager now)
        auth_url, state = oauth_manager.generate_auth_url(user_id)

        # Send link to user
        await update.message.reply_text(
            f"🔐 *Authorization Required*\n\n"
            f"To connect your Google Sheets account, please follow these steps:\n\n"
            f"1. Click on the link below.\n"
            f"2. Authorize access on the Google page.\n"
            f"3. You will be redirected to a confirmation page.\n\n"
            f"[Authorize Access to Google Sheets]({auth_url})\n\n"
            f"_This link is unique and valid for a short time._",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        logger.info(f"Authorization link sent to user {user_id}")

    except Exception as e:
        logger.exception(f"Error generating authorization URL for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ An error occurred while starting the authorization process. Please try again later with /auth."
        )


async def sheet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sets active spreadsheet and verifies access for user transactions."""
    if not update.effective_user or not update.message:
        return
    user_id = str(update.effective_user.id)
    sheets_operations: SheetsOperations | None = context.bot_data.get("sheets_operations")
    oauth_manager: OAuthManager | None = context.bot_data.get("oauth_manager")

    if not sheets_operations or not oauth_manager:
        logger.error("SheetsOperations or OAuthManager not found in bot_data for /sheet.")
        await update.message.reply_text("Internal error: Service not available.")
        return

    if not oauth_manager.is_authenticated(user_id):
        await update.message.reply_text("⚠️ You must authenticate first using /auth.")
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text("⚠️ Incorrect usage. Provide the sheet ID.\nExample: `/sheet YOUR_SHEET_ID_HERE`")
        return

    spreadsheet_id = context.args[0].strip()
    wait_message = None
    db: Session | None = None
    try:
        wait_message = await update.message.reply_text(f"Verifying and configuring sheet '{spreadsheet_id}'...")

        # Verify access and get title
        spreadsheet_title = sheets_operations.setup_for_user(user_id, spreadsheet_id)

        if spreadsheet_title:
            # Store the active sheet ID and title in the database
            db = SessionLocal()
            success = _set_active_sheet(db, user_id, spreadsheet_id, spreadsheet_title)
            if success:
                await wait_message.edit_text(
                    f"✅ Spreadsheet *{spreadsheet_title}* selected.\n\nNow you can use commands like /add with this sheet.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                logger.info(f"User {user_id} selected spreadsheet {spreadsheet_id} ('{spreadsheet_title}') and saved to DB.")
            else:
                await wait_message.edit_text(
                    f"❌ The sheet '{spreadsheet_title}' was verified, but there was an error saving it as active. Try again."
                )

        else:
            await wait_message.edit_text(
                f"❌ Could not verify access to the sheet with ID: {spreadsheet_id}. Make sure you are authenticated (/auth) and have permissions."
            )

    except SpreadsheetNotFound:
        logger.warning(f"SpreadsheetNotFound error for user {user_id}, sheet_id {spreadsheet_id}")
        error_msg = f"❌ Sheet not found or inaccessible (ID: {spreadsheet_id}). Verify the ID and your permissions."
        if wait_message:
            await wait_message.edit_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
    except (APIError, GoogleAuthError) as e:
        logger.error(f"API/Auth error setting sheet {spreadsheet_id} for user {user_id}: {e}")
        error_msg = f"❌ Error accessing sheet '{spreadsheet_id}'."
        if "PERMISSION_DENIED" in str(e):
            error_msg += " Permission denied."
        elif "invalid_grant" in str(e) or isinstance(e, GoogleAuthError):
            error_msg = "❌ Authentication error. Try /auth again."
        else:
            error_msg += " Try again later."
        if wait_message:
            await wait_message.edit_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
    except Exception as e:
        logger.exception(f"Unexpected error setting spreadsheet {spreadsheet_id} for user {user_id}: {e}")
        error_msg = f"❌ Unexpected error configuring sheet '{spreadsheet_id}'."
        if wait_message:
            await wait_message.edit_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
    finally:
        if db:
            db.close()


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Revokes access and clears database data for security and clean state."""
    if not update.effective_user or not update.message:
        return
    user_id = str(update.effective_user.id)
    oauth_manager: OAuthManager | None = context.bot_data.get("oauth_manager")
    sheets_client = context.bot_data.get("sheets_client")

    if not oauth_manager:
        logger.error("OAuthManager not found in bot_data for /logout.")
        await update.message.reply_text("Error interno: Servicio no disponible.")
        return

    # Check if authenticated before attempting logout
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

        await update.message.reply_text(
            "✅ You have successfully logged out.\n\n"
            "Access to your Google account has been revoked for this bot, "
            "and your local data has been deleted.\n\n"
            "Use /auth if you wish to reconnect."
        )
        logger.info(f"Logout completed for user {user_id}")

    except Exception as e:
        logger.exception(f"Error during logout for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred during logout. Please try again.")


# --- OAuth Callback Handling Logic ---


async def _send_auth_success_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends success message after OAuth callback for better user experience."""
    job_data = context.job.data if context.job else {}
    user_id = job_data.get("user_id")
    if not user_id:
        logger.error("Job data missing user_id for sending success message.")
        return

    logger.info(f"Sending delayed auth success message to user {user_id}")
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ *Authorization Successful*\n\n"
            "You have successfully connected your Google Sheets account.\n\n"
            "Now you can:\n"
            "• Use /sheet <ID> to select a sheet.\n"
            "• Use /add to record transactions.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error(f"Failed to send auth success message to user {user_id}: {e}")
