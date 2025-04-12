"""
Message and command handlers for the Telegram bot.
"""

import datetime

from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.config.categories import category_manager
from src.sheets.operations import SheetsOperations


def get_category_keyboard(expense_type: str = "gasto") -> InlineKeyboardMarkup:
    """
    Creates a button keyboard with categories based on transaction type for user selection.

    Args:
        expense_type: Transaction type (gasto or ingreso)

    Returns:
        Telegram button keyboard
    """
    buttons = []

    if expense_type == "gasto":
        for category in category_manager.get_expense_category_names():
            # Callback data format: "category|expense_type|category_name"
            callback_data = f"category|{expense_type}|{category}"
            buttons.append([InlineKeyboardButton(category, callback_data=callback_data)])
    else:
        for category in category_manager.income_categories:
            # Callback data format: "category|expense_type|category_name"
            callback_data = f"category|{expense_type}|{category}"
            buttons.append([InlineKeyboardButton(category, callback_data=callback_data)])

    # Add button to return to type selector
    back_button = [InlineKeyboardButton("⬅️ Cambiar tipo", callback_data="back_to_selector")]
    buttons.append(back_button)

    return InlineKeyboardMarkup(buttons)


def get_subcategory_keyboard(main_category: str, expense_type: str) -> InlineKeyboardMarkup:
    """
    Creates a button keyboard with subcategories for more detailed categorization.

    Args:
        main_category: Selected main category name
        expense_type: Transaction type (gasto or ingreso)

    Returns:
        Telegram button keyboard
    """
    subcategories = category_manager.get_subcategories(main_category)

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
    /recargar - Recarga las categorías desde el archivo de configuración
    /logout - Cierra sesión y revoca acceso
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


async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /recargar command to refresh categories for dynamic configuration.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    user = update.effective_user

    try:
        category_manager.reload_categories()

        num_expense_cats = len(category_manager.get_expense_category_names())
        num_income_cats = len(category_manager.income_categories)
        num_total_subcats = sum(len(subcats) for subcats in category_manager.expense_categories.values())

        message = f"✅ Categorías recargadas correctamente:\n"
        message += f"- Categorías de gastos: *{num_expense_cats}*\n"
        message += f"- Subcategorías totales: *{num_total_subcats}*\n"
        message += f"- Categorías de ingresos: *{num_income_cats}*"

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Categories reloaded by {user.username or user.first_name}")

    except Exception as e:
        logger.error(f"Error reloading categories: {e}")
        await update.message.reply_text(f"❌ Error al recargar las categorías: {str(e)}")


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
    try:
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

    except ValueError as e:
        await update.effective_message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error adding transaction: {e}")
    except Exception as e:
        await update.effective_message.reply_text("❌ Error al registrar la transacción")
        logger.exception(f"Error no controlado al agregar transacción: {e}")


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
            # Update message with new category keyboard based on selected type
            keyboard = get_category_keyboard(expense_type)
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
                # Create keyboard with subcategories
                keyboard = get_subcategory_keyboard(category, expense_type)
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
            # Show main categories again
            keyboard = get_category_keyboard(expense_type)
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
