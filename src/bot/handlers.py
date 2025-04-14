"""
Message and command handlers for the Telegram bot.
"""

import datetime

import yaml
from gspread.exceptions import APIError, WorksheetNotFound  # Import other relevant exceptions
from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.config.categories import category_manager
from src.sheets.operations import MissingHeadersError, SheetsOperations

from ..db.database import SessionLocal


def get_category_keyboard(expense_type: str = "gasto", user_id: str = None) -> InlineKeyboardMarkup:
    """
    Creates a button keyboard with categories based on transaction type and user preferences.

    Args:
        expense_type: Transaction type (gasto or ingreso)
        user_id: User's ID for personalized categories

    Returns:
        Telegram button keyboard
    """
    buttons = []

    if expense_type == "gasto":
        for category in category_manager.get_expense_category_names(user_id):
            # Callback data format: "category|expense_type|category_name"
            callback_data = f"category|{expense_type}|{category}"
            buttons.append([InlineKeyboardButton(category, callback_data=callback_data)])
    else:
        for category in category_manager.get_income_categories(user_id):
            # Callback data format: "category|expense_type|category_name"
            callback_data = f"category|{expense_type}|{category}"
            buttons.append([InlineKeyboardButton(category, callback_data=callback_data)])

    # Add button to return to type selector
    back_button = [InlineKeyboardButton("⬅️ Cambiar tipo", callback_data="back_to_selector")]
    buttons.append(back_button)

    return InlineKeyboardMarkup(buttons)


def get_subcategory_keyboard(main_category: str, expense_type: str, user_id: str = None) -> InlineKeyboardMarkup:
    """
    Creates a button keyboard with subcategories for more detailed categorization.

    Args:
        main_category: Selected main category name
        expense_type: Transaction type (gasto or ingreso)
        user_id: User's ID for personalized categories

    Returns:
        Telegram button keyboard
    """
    subcategories = category_manager.get_subcategories(main_category, user_id)

    buttons = []
    for subcat in subcategories:
        if subcat.strip():
            callback_data = f"subcategory|{expense_type}|{main_category}|{subcat}"
            buttons.append([InlineKeyboardButton(subcat, callback_data=callback_data)])

    back_button = [InlineKeyboardButton("⬅️ Volver a Categorías", callback_data=f"back|{expense_type}")]
    buttons.append(back_button)

    return InlineKeyboardMarkup(buttons)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /start command to onboard new users.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    user = update.effective_user
    await update.message.reply_text(
        f"¡Hola {user.first_name}! Soy el bot de gestión financiera.\n\n"
        f"Para comenzar, necesitas autorizar el acceso a tus hojas de cálculo de Google.\n"
        f"Usa el comando /auth para iniciar el proceso de autorización."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /help command to provide guidance.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    help_text = """
    *Comandos disponibles:*
    /start - Inicia el bot
    /help - Muestra este mensaje de ayuda
    /auth - Autoriza acceso a tus hojas de Google

    /sheet <ID> - Selecciona una hoja de cálculo específica
    /agregar - Muestra las categorías disponibles para registrar una transacción
    /logout - Cierra sesión y revoca acceso

    *Gestión de categorías (personalizadas por usuario):*
    /categorias - Muestra tus categorías actuales
    /editarcat - Edita tus categorías personalizadas. Pasos:
        1. Usa la opción 'Exportar a YAML' para obtener tu archivo actual.
        2. Edita el archivo `.yaml` descargado (añade/modifica/elimina categorías/subcategorías).
        3. Usa la opción 'Importar desde YAML' y envía el archivo modificado.
    /resetcat - Reinicia tus categorías a los valores predeterminados del sistema
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")


def get_type_selector_keyboard() -> InlineKeyboardMarkup:
    """
    Creates a simple keyboard to select transaction type for initial selection.

    Returns:
        Telegram button keyboard
    """
    buttons = [[InlineKeyboardButton("GASTOS", callback_data="selector|gasto"), InlineKeyboardButton("INGRESOS", callback_data="selector|ingreso")]]
    return InlineKeyboardMarkup(buttons)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /agregar command to start transaction recording process.
    Shows buttons to choose between expense or income.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    user = update.effective_user
    user_id = str(user.id)

    oauth_manager = context.bot_data.get("oauth_manager")

    if not oauth_manager or not oauth_manager.is_authenticated(user_id):
        await update.message.reply_text(
            "⚠️ Debes autenticarte primero antes de registrar transacciones.\n\nUsa /auth para iniciar el proceso de autorización."
        )
        return

    try:
        keyboard = get_type_selector_keyboard()
        await update.message.reply_text("¿Qué tipo de transacción deseas registrar?", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error al mostrar el selector de tipo: {e}")
        await update.message.reply_text("❌ Error al iniciar el proceso de registro")


async def register_transaction(
    update: Update, context: ContextTypes.DEFAULT_TYPE, expense_type: str, amount: float, category: str, subcategory: str, date: str, comment: str
) -> None:
    """
    Records a transaction in the spreadsheet to maintain financial tracking.

    Args:
        update: Telegram Update object
        context: Handler context
        expense_type: Transaction type (gasto or ingreso)
        amount: Transaction amount
        category: Main category of the transaction
        subcategory: Subcategory of the transaction
        date: Transaction date in YYYY-MM-DD format
        comment: Optional transaction comment
    """
    user = update.effective_user
    user_id = str(user.id)
    sheets_ops: SheetsOperations = context.bot_data.get("sheets_operations")
    if expense_type == "gasto":
        sheet_name = "gastos"
        row_data = [
            date,
            user.username or user.first_name,
            category,
            subcategory,
            amount,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            comment,
        ]
    elif expense_type == "ingreso":
        sheet_name = "ingresos"
        row_data = [
            date,
            user.username or user.first_name,
            category,
            amount,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            comment,
        ]

    try:
        sheets_ops.append_row(user_id, sheet_name, row_data)
        sign = "-" if expense_type == "gasto" else "+"

        # For income, where category and subcategory are the same, only show once
        category_display = f"{category}" if category == subcategory else f"{category} - {subcategory}"

        confirm_message = (
            f"✅ {expense_type.capitalize()} registrado correctamente:\nFecha: {date}\nCategoría: {category_display}\nMonto: {sign}{amount:.2f}"
        )

        if comment:
            confirm_message += f"\nComment: {comment}"

        await update.effective_message.reply_text(confirm_message)

    except MissingHeadersError as e:
        logger.error(f"Header mismatch error for user {user_id}: {e}")
        await update.effective_message.reply_text(
            f"❌ Error: Las cabeceras de la hoja '{e.sheet_name}' no son correctas.\n"
            f"Esperadas: `{e.expected}`\n"
            f"Encontradas: `{e.actual}`\n\n"
            "Por favor, corrige las cabeceras en tu Google Sheet o asegúrate de que la hoja exista y tenga datos.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except WorksheetNotFound:
        logger.error(f"Worksheet '{sheet_name}' not found for user {user_id} during append.")
        await update.effective_message.reply_text(
            f"❌ Error: No se encontró la hoja '{sheet_name}' en tu Google Sheet activo. "
            "Asegúrate de que exista o selecciona la hoja correcta con /sheet."
        )
    except APIError as e:
        logger.error(f"Google Sheets API error during append for user {user_id}: {e}")
        await update.effective_message.reply_text(
            "❌ Error de API al intentar registrar la transacción en Google Sheets. Verifica tu conexión o los permisos de la hoja."
        )
    except RuntimeError as e:
        logger.error(f"Runtime/Auth error during append for user {user_id}: {e}")
        await update.effective_message.reply_text("❌ Error de autenticación al registrar. Intenta usar /auth de nuevo.")
    except ValueError as e:
        logger.error(f"Configuration error adding transaction for user {user_id}: {e}")
        await update.effective_message.reply_text(f"❌ Error de configuración: {str(e)}")
    except Exception as e:
        await update.effective_message.reply_text("❌ Error inesperado al registrar la transacción en la hoja.")
        logger.exception(f"Unhandled error adding transaction for user {user_id}: {e}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles button interactions for guided transaction entry.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)

    # Verify authentication before processing callbacks
    oauth_manager = context.bot_data.get("oauth_manager")
    if not oauth_manager or not oauth_manager.is_authenticated(user_id):
        # Don't interrupt flow for buttons that don't require authentication
        # but validate when it's a transaction flow
        pass

    # Get callback data
    data = query.data.split("|")
    action = data[0]

    # If it's a type selector (expense/income)
    if action == "selector":
        # Verify authentication and active sheet for transaction flows
        if not oauth_manager or not oauth_manager.is_authenticated(user_id):
            await query.edit_message_text("⚠️ Debes autenticarte primero.\n\nUsa /auth para iniciar el proceso de autorización.")
            return

        expense_type = data[1]

        try:
            # Cargar las categorías personalizadas del usuario
            db = SessionLocal()
            try:
                category_manager.load_user_categories(user_id, db)
            except Exception as db_error:
                logger.error(f"Error loading user categories: {db_error}")
            finally:
                db.close()

            # Update message with new category keyboard based on selected type and user preferences
            keyboard = get_category_keyboard(expense_type, user_id)
            await query.edit_message_text(f"Selecciona una categoría para registrar un {expense_type}:", reply_markup=keyboard)
        except Exception as e:
            error_str = str(e)
            if "message is not modified" in error_str.lower():
                # This error occurs when we try to edit a message with identical content
                # Just log it without showing an error to the user
                logger.warning(f"Attempt to edit message with identical content: {error_str}")
            else:
                logger.error(f"Error getting categories for buttons: {e}")
                await query.edit_message_text("❌ Error al cargar las categorías")

        return

    # If it's a main category selection, show subcategories or request amount
    elif action == "category":
        expense_type = data[1]
        category = data[2]

        # Different behavior for expenses and income
        if expense_type == "gasto":
            try:
                # Cargar las categorías personalizadas del usuario
                db = SessionLocal()
                try:
                    category_manager.load_user_categories(user_id, db)
                except Exception as db_error:
                    logger.error(f"Error loading user categories for subcategories: {db_error}")
                finally:
                    db.close()

                # Create keyboard with subcategories based on user preferences
                keyboard = get_subcategory_keyboard(category, expense_type, user_id)
                await query.edit_message_text(
                    f"Has seleccionado *{category}* como {expense_type}.\nAhora selecciona una subcategoría:",
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(f"Error getting subcategories: {e}")
                await query.edit_message_text("❌ Error al cargar las subcategorías")
        else:
            # For income, no subcategories, proceed directly to request amount
            # Save data in user_data for next step
            context.user_data["pending_transaction"] = {
                "expense_type": expense_type,
                "category": category,
                "subcategory": category,  # For income, category and subcategory are the same
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "amount": None,  # Will be filled in next step
                "comment": "",  # Will be filled in final step
            }
            # Set state as "waiting_amount"
            context.user_data["state"] = "waiting_amount"

            await query.edit_message_text(
                f"Has seleccionado *{category}* como {expense_type}.\nPor favor envía el monto (solo números, ej: 123.45):", parse_mode="Markdown"
            )

        return

    # If it's back to categories
    elif action == "back":
        expense_type = data[1]

        try:
            # Cargar las categorías personalizadas del usuario
            db = SessionLocal()
            try:
                category_manager.load_user_categories(user_id, db)
            except Exception as db_error:
                logger.error(f"Error loading user categories for back action: {db_error}")
            finally:
                db.close()

            # Show main categories again with user preferences
            keyboard = get_category_keyboard(expense_type, user_id)
            await query.edit_message_text(f"Selecciona una categoría para registrar un {expense_type}:", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error going back to categories: {e}")
            await query.edit_message_text("❌ Error al cargar las categorías")

        return

    # If it's a subcategory selection, request the amount
    elif action == "subcategory":
        expense_type = data[1]
        category = data[2]
        subcategory = data[3]

        # Save data in user_data for next step
        context.user_data["pending_transaction"] = {
            "expense_type": expense_type,
            "category": category,
            "subcategory": subcategory,
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "amount": None,  # Will be filled in next step
            "comment": "",  # Will be filled in final step
        }
        # Set state as "waiting_amount"
        context.user_data["state"] = "waiting_amount"

        # For income, where category and subcategory are the same, adjust message
        category_display = f"{category}" if category == subcategory else f"{category} - {subcategory}"

        await query.edit_message_text(
            f"Has seleccionado *{category_display}* como {expense_type}.\nPor favor envía el monto (solo números, ej: 123.45):",
            parse_mode="Markdown",
        )

        return

    # If it's back to type selector
    elif action == "back_to_selector":
        try:
            # Show type selector again
            keyboard = get_type_selector_keyboard()
            await query.edit_message_text("¿Qué tipo de transacción deseas registrar?", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error going back to type selector: {e}")
            await query.edit_message_text("❌ Error al cargar el selector de tipo")

        return

    # If it's a response to add comment question
    elif action == "comment":
        option = data[1]  # "yes" or "no"

        # Verify there's a pending transaction
        if "pending_transaction" not in context.user_data:
            logger.warning(f"Attempted to add comment but no pending transaction. User: {update.effective_user.id}")
            await query.edit_message_text("❌ Error: La transacción ha expirado. Por favor usa /agregar para iniciar una nueva transacción.")
            return

        logger.info(f"Handling comment button. Option: {option}. User: {update.effective_user.id}")
        if option == "yes":
            # User wants to add a comment
            context.user_data["state"] = "waiting_comment"
            # Extract transaction data for message
            transaction = context.user_data["pending_transaction"]
            expense_type = transaction["expense_type"]
            category = transaction["category"]
            amount = transaction["amount"]

            # Show category (with subcategory if expense)
            if expense_type == "ingreso":
                category_display = category
            else:
                subcategory = transaction["subcategory"]
                category_display = f"{category} - {subcategory}"

            await query.edit_message_text(
                f"*{category_display}* - *{amount:.2f}*\n\nPor favor escribe un comentario para esta transacción:", parse_mode="Markdown"
            )
        else:  # option == "no"
            # User doesn't want to add comment, record transaction without comment
            transaction = context.user_data["pending_transaction"]
            expense_type = transaction["expense_type"]
            category = transaction["category"]
            subcategory = transaction["subcategory"]
            date = transaction["date"]
            amount = transaction["amount"]

            # Record transaction without comment (empty string)
            await register_transaction(update, context, expense_type, amount, category, subcategory, date, "")

            # Clear temporary data
            del context.user_data["pending_transaction"]
            if "state" in context.user_data:
                del context.user_data["state"]

        return

    # Handle reset categories confirmation
    elif action == "reset_categories":
        option = data[1]  # "confirm" or "cancel"

        if option == "confirm":
            # Reset user categories to defaults
            db = SessionLocal()
            try:
                success = category_manager.reset_user_categories(user_id, db)
                if success:
                    await query.edit_message_text("✅ Tus categorías han sido restablecidas a los valores predeterminados.")
                else:
                    await query.edit_message_text("❌ Error al restablecer tus categorías.")
            except Exception as e:
                logger.error(f"Error resetting categories for user {user_id}: {e}")
                await query.edit_message_text("❌ Error al restablecer las categorías.")
            finally:
                db.close()
        else:  # option == "cancel"
            await query.edit_message_text("⚠️ Operación cancelada. Tus categorías no han sido modificadas.")
        return

    # Handle edit categories options
    elif action == "edit_categories":
        option = data[1]  # "expense", "income", "import" or "export"

        if option == "import":
            # Prompt user to upload YAML file
            await query.edit_message_text(
                "📝 Por favor, envía un archivo YAML con tus categorías personalizadas.\n\n"
                "El archivo debe tener el siguiente formato:\n```\n"
                "expense_categories:\n"
                "  CATEGORIA1:\n"
                "    - Subcategoria1\n"
                "    - Subcategoria2\n"
                "  CATEGORIA2:\n"
                "    - Subcategoria3\n"
                "income_categories:\n"
                "  - Ingreso1\n"
                "  - Ingreso2\n```"
            )
            # Set state to waiting for file upload
            context.user_data["state"] = "waiting_category_file"
            return

        elif option == "export":
            # Export categories to YAML
            await query.edit_message_text("📦 Exportando tus categorías...")
            await export_categories_to_yaml(update, context)
            return

        elif option == "expense" or option == "income":
            # Show message about editing not yet implemented
            await query.edit_message_text(
                f"La edición manual de categorías de {option} está en desarrollo.\n\n"
                "Por ahora, puedes usar las opciones de importar/exportar para modificar tus categorías mediante un archivo YAML."
            )
            return

    # If it gets here, it's an unknown command
    await query.edit_message_text("❌ Acción no reconocida. Usa /agregar para comenzar de nuevo.")


async def amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles amount input after category selection for proper transaction recording.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    # Verify if there's a pending transaction and we're waiting for an amount
    if "pending_transaction" not in context.user_data or context.user_data.get("state") != "waiting_amount":
        # If we're not waiting for an amount, ignore this message (will be handled by another handler)
        return

    logger.info(f"Processing amount for transaction. User: {update.effective_user.id}")

    try:
        amount_text = update.message.text.strip()

        # Validate it's a number
        try:
            amount = float(amount_text)
            if amount <= 0:
                await update.message.reply_text("⚠️ El monto debe ser un número positivo. Intenta de nuevo:")
                return
        except ValueError:
            await update.message.reply_text("⚠️ Por favor ingresa solo números (ej: 123.45). Intenta de nuevo:")
            return

        # Save amount in pending transaction
        context.user_data["pending_transaction"]["amount"] = amount

        # Change state to "confirm_comment"
        context.user_data["state"] = "confirm_comment"

        # Prepare transaction information to display
        transaction = context.user_data["pending_transaction"]
        expense_type = transaction["expense_type"]
        category = transaction["category"]

        # For income, where category and subcategory are the same, adjust message
        if expense_type == "ingreso":
            category_display = category
        else:
            subcategory = transaction["subcategory"]
            category_display = f"{category} - {subcategory}"

        # Create buttons to confirm if user wants to add a comment
        keyboard = [[InlineKeyboardButton("✅ Sí", callback_data="comment|yes"), InlineKeyboardButton("❌ No", callback_data="comment|no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Has seleccionado *{category_display}* como {expense_type} con monto *{amount:.2f}*.\n\n¿Deseas agregar un comentario a esta transacción?",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    except Exception as e:
        # If any error occurs, inform user and log it
        logger.error(f"Error processing amount: {e}")
        await update.message.reply_text("❌ Error al procesar la transacción. Por favor intenta de nuevo con /agregar.")


async def comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles comment input and finalizes transaction recording for complete data.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    # Verify if there's a pending transaction and we're waiting for a comment
    if "pending_transaction" not in context.user_data or context.user_data.get("state") != "waiting_comment":
        # If we're not waiting for a comment, ignore this message (will be handled by another handler)
        return

    logger.info(f"Processing comment for transaction. User: {update.effective_user.id}")

    try:
        # Get entered comment
        comment_text = update.message.text.strip()

        # If user writes "no comment", save as empty string
        if comment_text.lower() == "no comment":
            comment_text = ""

        # Get complete data from pending transaction
        transaction = context.user_data["pending_transaction"]
        expense_type = transaction["expense_type"]
        category = transaction["category"]
        subcategory = transaction["subcategory"]
        date = transaction["date"]
        amount = transaction["amount"]

        # Record transaction with comment
        await register_transaction(update, context, expense_type, amount, category, subcategory, date, comment_text)

        # Clear temporary data
        del context.user_data["pending_transaction"]
        if "state" in context.user_data:
            del context.user_data["state"]

    except Exception as e:
        # If any error occurs, inform user and log it
        logger.error(f"Error processing comment: {e}")
        await update.message.reply_text("❌ Error al procesar la transacción. Por favor intenta de nuevo con /agregar.")


async def register_bot_commands(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Registers bot commands in Telegram for user discoverability.
    This handler runs at bot startup.

    Args:
        context: Handler context
    """
    from .commands import get_commands

    try:
        # Set commands in bot menu
        await context.bot.set_my_commands(get_commands())
        logger.info("Bot commands registered successfully")
    except Exception as e:
        logger.error(f"Error registering bot commands: {e}")


async def show_categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra las categorías del usuario.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    user = update.effective_user
    user_id = str(user.id)

    # Verificar autenticación
    oauth_manager = context.bot_data.get("oauth_manager")
    if not oauth_manager or not oauth_manager.is_authenticated(user_id):
        await update.message.reply_text("⚠️ Debes autenticarte primero.\n\nUsa /auth para iniciar el proceso de autorización.")
        return

    # Obtener categorías del usuario
    db = SessionLocal()
    try:
        category_manager.load_user_categories(user_id, db)

        expense_categories = category_manager.get_expense_categories(user_id)
        income_categories = category_manager.get_income_categories(user_id)

        # Construir mensaje
        message = "*Tus categorías personalizadas:*\n\n"

        # Categorías de gastos
        message += "*CATEGORÍAS DE GASTOS:*\n"
        for category, subcategories in expense_categories.items():
            message += f"• {category}\n"
            for subcategory in subcategories:
                message += f"  - {subcategory}\n"

        # Categorías de ingresos
        message += "\n*CATEGORÍAS DE INGRESOS:*\n"
        for category in income_categories:
            message += f"• {category}\n"

        # Añadir instrucciones
        message += "\nPuedes personalizar tus categorías con el comando /editarcat"

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error showing categories for user {user_id}: {e}")
        await update.message.reply_text("❌ Error al obtener tus categorías.")
    finally:
        db.close()


async def reset_categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Resetea las categorías del usuario a los valores predeterminados.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    user = update.effective_user
    user_id = str(user.id)

    # Verificar autenticación
    oauth_manager = context.bot_data.get("oauth_manager")
    if not oauth_manager or not oauth_manager.is_authenticated(user_id):
        await update.message.reply_text("⚠️ Debes autenticarte primero.\n\nUsa /auth para iniciar el proceso de autorización.")
        return

    # Crear botones de confirmación
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Sí, resetear", callback_data="reset_categories|confirm"),
                InlineKeyboardButton("❌ No, cancelar", callback_data="reset_categories|cancel"),
            ]
        ]
    )

    await update.message.reply_text(
        "⚠️ ¿Estás seguro que deseas resetear tus categorías personalizadas a los valores predeterminados?", reply_markup=keyboard
    )


async def edit_categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Inicia el flujo de edición de categorías.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    user = update.effective_user
    user_id = str(user.id)

    # Verificar autenticación
    oauth_manager = context.bot_data.get("oauth_manager")
    if not oauth_manager or not oauth_manager.is_authenticated(user_id):
        await update.message.reply_text("⚠️ Debes autenticarte primero.\n\nUsa /auth para iniciar el proceso de autorización.")
        return

    # Mostrar opciones para editar
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✏️ Editar categorías de gastos", callback_data="edit_categories|expense")],
            [InlineKeyboardButton("✏️ Editar categorías de ingresos", callback_data="edit_categories|income")],
            [InlineKeyboardButton("📝 Importar desde YAML", callback_data="edit_categories|import")],
            [InlineKeyboardButton("📦 Exportar a YAML", callback_data="edit_categories|export")],
        ]
    )

    await update.message.reply_text("¿Qué deseas hacer con tus categorías?", reply_markup=keyboard)


async def process_yaml_import(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Procesa un archivo YAML para importar categorías.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    user = update.effective_user
    user_id = str(user.id)

    # Verificar si hay un documento adjunto
    if not update.message.document:
        await update.message.reply_text("❌ Por favor, adjunta un archivo YAML con tus categorías.")
        return

    # Verificar que sea un archivo YAML
    file = update.message.document
    if not file.file_name.endswith((".yaml", ".yml")):
        await update.message.reply_text("❌ El archivo debe tener extensión .yaml o .yml")
        return

    try:
        # Descargar archivo
        file_obj = await context.bot.get_file(file.file_id)
        yaml_content = await file_obj.download_as_bytearray()
        yaml_text = yaml_content.decode("utf-8")

        # Parsear YAML
        categories_data = yaml.safe_load(yaml_text)

        # Validar estructura
        if not isinstance(categories_data, dict):
            await update.message.reply_text("❌ Formato incorrecto. El archivo debe contener un diccionario YAML.")
            return

        # Verificar campos requeridos
        if "expense_categories" not in categories_data or "income_categories" not in categories_data:
            await update.message.reply_text("❌ Formato incorrecto. El archivo debe contener 'expense_categories' y 'income_categories'.")
            return

        # Validar tipos
        expense_categories = categories_data["expense_categories"]
        income_categories = categories_data["income_categories"]

        if not isinstance(expense_categories, dict) or not isinstance(income_categories, list):
            await update.message.reply_text("❌ Formato incorrecto. 'expense_categories' debe ser un diccionario y 'income_categories' una lista.")
            return

        # Verificar subcategorías
        for category, subcategories in expense_categories.items():
            if not isinstance(subcategories, list):
                await update.message.reply_text(f"❌ Formato incorrecto. Las subcategorías de '{category}' deben ser una lista.")
                return

        # Guardar categorías
        db = SessionLocal()
        try:
            success = category_manager.save_user_categories(user_id, expense_categories, income_categories, db)

            if success:
                await update.message.reply_text("✅ Categorías importadas correctamente.")
            else:
                await update.message.reply_text("❌ Error al guardar las categorías.")

        finally:
            db.close()

    except yaml.YAMLError as e:
        await update.message.reply_text(f"❌ Error al parsear el archivo YAML: {str(e)}")
        context.user_data.pop("state", None)  # Clear state on error
    except Exception as e:
        logger.error(f"Error importing YAML categories for user {user_id}: {e}")
        await update.message.reply_text("❌ Error al procesar el archivo de categorías.")
        context.user_data.pop("state", None)  # Clear state on error


async def export_categories_to_yaml(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Exporta las categorías del usuario a un archivo YAML.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    user = update.effective_user
    user_id = str(user.id)

    # Obtener categorías del usuario
    db = SessionLocal()
    try:
        category_manager.load_user_categories(user_id, db)

        expense_categories = category_manager.get_expense_categories(user_id)
        income_categories = category_manager.get_income_categories(user_id)

        # Crear diccionario de categorías
        categories_data = {"expense_categories": expense_categories, "income_categories": income_categories}

        # Convertir a YAML
        yaml_content = yaml.safe_dump(categories_data, allow_unicode=True, sort_keys=False)

        # Crear archivo temporal
        import tempfile

        temp_file = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False)
        temp_file.write(yaml_content.encode("utf-8"))
        temp_file.close()

        # Enviar archivo
        with open(temp_file.name, "rb") as file:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file,
                filename=f"categorias_{user.username or user_id}.yaml",
                caption="📦 Tus categorías personalizadas",
            )

        # Eliminar archivo temporal
        import os

        os.unlink(temp_file.name)

    except Exception as e:
        logger.error(f"Error exporting YAML categories for user {user_id}: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Error al exportar tus categorías.")
        elif update.effective_message:
            await update.effective_message.reply_text("❌ Error al exportar tus categorías.")
    finally:
        db.close()


async def error_handler(update: Update | None, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Global error handler for graceful error management.

    Args:
        update: Telegram Update object or None
        context: Context with error information
    """
    logger.exception(f"Error: {context.error} - Update: {update}")

    if update and update.effective_message:
        await update.effective_message.reply_text("Ha ocurrido un error. Por favor intenta de nuevo más tarde.")
