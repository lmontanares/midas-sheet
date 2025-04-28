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


def get_category_keyboard(expense_type: str = "expense", user_id: str = None) -> InlineKeyboardMarkup:
    """
    Creates a button keyboard with categories based on transaction type and user preferences.

    Args:
        expense_type: Transaction type (expense or income)
        user_id: User's ID for personalized categories

    Returns:
        Telegram button keyboard
    """
    buttons = []

    if expense_type == "expense":
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
    back_button = [InlineKeyboardButton("⬅️ Change type", callback_data="back_to_selector")]
    buttons.append(back_button)

    return InlineKeyboardMarkup(buttons)


def get_subcategory_keyboard(main_category: str, expense_type: str, user_id: str = None) -> InlineKeyboardMarkup:
    """
    Creates a button keyboard with subcategories for more detailed categorization.

    Args:
        main_category: Selected main category name
        expense_type: Transaction type (expense or income)
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

    back_button = [InlineKeyboardButton("⬅️ Back to Categories", callback_data=f"back|{expense_type}")]
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
        f"Hello {user.first_name}! I'm the financial management bot.\n\n"
        f"To get started, you need to authorize access to your Google Sheets.\n"
        f"Use the /auth command to start the authorization process."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /help command to provide guidance.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    help_text = """
    *Available Commands:*
    /start - Start the bot
    /help - Show this help message
    /auth - Authorize access to your Google Sheets

    /sheet <ID> - Select a specific spreadsheet
    /add - Show available categories to record a transaction
    /logout - Log out and revoke access

    *Category Management (customized per user):*
    /categories - Show your current categories
    /editcat - Edit your custom categories. Steps:
        1. Use the 'Export to YAML' option to get your current file.
        2. Edit the downloaded `.yaml` file (add/modify/delete categories/subcategories).
        3. Use the 'Import from YAML' option and send the modified file.
    /resetcat - Reset your categories to system default values
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")


def get_type_selector_keyboard() -> InlineKeyboardMarkup:
    """
    Creates a simple keyboard to select transaction type for initial selection.

    Returns:
        Telegram button keyboard
    """
    buttons = [[InlineKeyboardButton("EXPENSES", callback_data="selector|expense"), InlineKeyboardButton("INCOME", callback_data="selector|income")]]
    return InlineKeyboardMarkup(buttons)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /add command to start transaction recording process.
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
            "⚠️ You need to authenticate first before recording transactions.\n\nUse /auth to start the authorization process."
        )
        return

    try:
        keyboard = get_type_selector_keyboard()
        await update.message.reply_text("What type of transaction would you like to record?", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error displaying type selector: {e}")
        await update.message.reply_text("❌ Error starting the registration process")


async def register_transaction(
    update: Update, context: ContextTypes.DEFAULT_TYPE, expense_type: str, amount: float, category: str, subcategory: str, date: str, comment: str
) -> None:
    """
    Records a transaction in the spreadsheet to maintain financial tracking.

    Args:
        update: Telegram Update object
        context: Handler context
        expense_type: Transaction type (expense or income)
        amount: Transaction amount
        category: Main category of the transaction
        subcategory: Subcategory of the transaction
        date: Transaction date in YYYY-MM-DD format
        comment: Optional transaction comment
    """
    user = update.effective_user
    user_id = str(user.id)
    sheets_ops: SheetsOperations = context.bot_data.get("sheets_operations")
    if expense_type == "expense":
        sheet_name = "expenses"
        row_data = [
            date,
            user.username or user.first_name,
            category,
            subcategory,
            amount,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            comment,
        ]
    elif expense_type == "income":
        sheet_name = "income"
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
        sign = "-" if expense_type == "expense" else "+"

        # For income, where category and subcategory are the same, only show once
        category_display = f"{category}" if category == subcategory else f"{category} - {subcategory}"

        confirm_message = (
            f"✅ {expense_type.capitalize()} recorded successfully:\nDate: {date}\nCategory: {category_display}\nAmount: {sign}{amount:.2f}"
        )

        if comment:
            confirm_message += f"\nComment: {comment}"

        await update.effective_message.reply_text(confirm_message)

    except MissingHeadersError as e:
        logger.error(f"Header mismatch error for user {user_id}: {e}")
        await update.effective_message.reply_text(
            f"❌ Error: The headers in the sheet '{e.sheet_name}' are not correct.\n"
            f"Expected: `{e.expected}`\n"
            f"Found: `{e.actual}`\n\n"
            "Please correct the headers in your Google Sheet or make sure the sheet exists and has data.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except WorksheetNotFound:
        logger.error(f"Worksheet '{sheet_name}' not found for user {user_id} during append.")
        await update.effective_message.reply_text(
            f"❌ Error: The worksheet '{sheet_name}' was not found in your active Google Sheet. "
            "Make sure it exists or select the correct sheet with /sheet."
        )
    except APIError as e:
        logger.error(f"Google Sheets API error during append for user {user_id}: {e}")
        await update.effective_message.reply_text(
            "❌ API error when trying to record the transaction in Google Sheets. Check your connection or sheet permissions."
        )
    except RuntimeError as e:
        logger.error(f"Runtime/Auth error during append for user {user_id}: {e}")
        await update.effective_message.reply_text("❌ Authentication error when recording. Try using /auth again.")
    except ValueError as e:
        logger.error(f"Configuration error adding transaction for user {user_id}: {e}")
        await update.effective_message.reply_text(f"❌ Configuration error: {str(e)}")
    except Exception as e:
        await update.effective_message.reply_text("❌ Unexpected error while recording the transaction in the sheet.")
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
            await query.edit_message_text("⚠️ You need to authenticate first.\n\nUse /auth to start the authorization process.")
            return

        expense_type = data[1]

        try:
            # Load user's custom categories
            db = SessionLocal()
            try:
                category_manager.load_user_categories(user_id, db)
            except Exception as db_error:
                logger.error(f"Error loading user categories: {db_error}")
            finally:
                db.close()

            # Update message with new category keyboard based on selected type and user preferences
            keyboard = get_category_keyboard(expense_type, user_id)
            await query.edit_message_text(f"Select a category to record an {expense_type}:", reply_markup=keyboard)
        except Exception as e:
            error_str = str(e)
            if "message is not modified" in error_str.lower():
                # This error occurs when we try to edit a message with identical content
                # Just log it without showing an error to the user
                logger.warning(f"Attempt to edit message with identical content: {error_str}")
            else:
                logger.error(f"Error getting categories for buttons: {e}")
                await query.edit_message_text("❌ Error loading categories")

        return

    # If it's a main category selection, show subcategories or request amount
    elif action == "category":
        expense_type = data[1]
        category = data[2]

        # Different behavior for expenses and income
        if expense_type == "expense":
            try:
                # Load user's custom categories
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
                    f"You selected *{category}* as {expense_type}.\nNow select a subcategory:",
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(f"Error getting subcategories: {e}")
                await query.edit_message_text("❌ Error loading subcategories")
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
                f"You selected *{category}* as {expense_type}.\nPlease enter the amount (numbers only, e.g.: 123.45):", parse_mode="Markdown"
            )

        return

    # If it's back to categories
    elif action == "back":
        expense_type = data[1]

        try:
            # Load user's custom categories
            db = SessionLocal()
            try:
                category_manager.load_user_categories(user_id, db)
            except Exception as db_error:
                logger.error(f"Error loading user categories for back action: {db_error}")
            finally:
                db.close()

            # Show main categories again with user preferences
            keyboard = get_category_keyboard(expense_type, user_id)
            await query.edit_message_text(f"Select a category to record an {expense_type}:", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error going back to categories: {e}")
            await query.edit_message_text("❌ Error loading categories")

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
            f"You selected *{category_display}* as {expense_type}.\nPlease enter the amount (numbers only, e.g.: 123.45):",
            parse_mode="Markdown",
        )

        return

    # If it's back to type selector
    elif action == "back_to_selector":
        try:
            # Show type selector again
            keyboard = get_type_selector_keyboard()
            await query.edit_message_text("What type of transaction would you like to record?", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error going back to type selector: {e}")
            await query.edit_message_text("❌ Error loading type selector")

        return

    # If it's a response to add comment question
    elif action == "comment":
        option = data[1]  # "yes" or "no"

        # Verify there's a pending transaction
        if "pending_transaction" not in context.user_data:
            logger.warning(f"Attempted to add comment but no pending transaction. User: {update.effective_user.id}")
            await query.edit_message_text("❌ Error: The transaction has expired. Please use /add to start a new transaction.")
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
            if expense_type == "income":
                category_display = category
            else:
                subcategory = transaction["subcategory"]
                category_display = f"{category} - {subcategory}"

            await query.edit_message_text(
                f"*{category_display}* - *{amount:.2f}*\n\nPlease write a comment for this transaction:", parse_mode="Markdown"
            )
        else:
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
                    await query.edit_message_text("✅ Your categories have been reset to default values.")
                else:
                    await query.edit_message_text("❌ Error resetting your categories.")
            except Exception as e:
                logger.error(f"Error resetting categories for user {user_id}: {e}")
                await query.edit_message_text("❌ Error resetting categories.")
            finally:
                db.close()
        else:  # option == "cancel"
            await query.edit_message_text("⚠️ Operation cancelled. Your categories have not been modified.")
        return

    # Handle edit categories options
    elif action == "edit_categories":
        option = data[1]  # "expense", "income", "import" or "export"

        if option == "import":
            # Prompt user to upload YAML file
            await query.edit_message_text(
                "📝 Please send a YAML file with your custom categories.\n\n"
                "The file must have the following format:\n```\n"
                "expense_categories:\n"
                "  CATEGORY1:\n"
                "    - Subcategory1\n"
                "    - Subcategory2\n"
                "  CATEGORY2:\n"
                "    - Subcategory3\n"
                "income_categories:\n"
                "  - Income1\n"
                "  - Income2\n```"
            )
            # Set state to waiting for file upload
            context.user_data["state"] = "waiting_category_file"
            return

        elif option == "export":
            # Export categories to YAML
            await query.edit_message_text("📦 Exporting your categories...")
            await export_categories_to_yaml(update, context)
            return

        elif option == "expense" or option == "income":
            # Show message about editing not yet implemented
            await query.edit_message_text(
                f"Manual editing of {option} categories is in development.\n\n"
                "For now, you can use the import/export options to modify your categories using a YAML file."
            )
            return

    # If it gets here, it's an unknown command
    await query.edit_message_text("❌ Unrecognized action. Use /add to start again.")


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
                await update.message.reply_text("⚠️ The amount must be a positive number. Try again:")
                return
        except ValueError:
            await update.message.reply_text("⚠️ Please enter only numbers (e.g.: 123.45). Try again:")
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
        if expense_type == "income":
            category_display = category
        else:
            subcategory = transaction["subcategory"]
            category_display = f"{category} - {subcategory}"

        # Create buttons to confirm if user wants to add a comment
        keyboard = [[InlineKeyboardButton("✅ Yes", callback_data="comment|yes"), InlineKeyboardButton("❌ No", callback_data="comment|no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"You selected *{category_display}* as {expense_type} with amount *{amount:.2f}*.\n\nWould you like to add a comment to this transaction?",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    except Exception as e:
        # If any error occurs, inform user and log it
        logger.error(f"Error processing amount: {e}")
        await update.message.reply_text("❌ Error processing the transaction. Please try again with /add.")


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
        await update.message.reply_text("❌ Error processing the transaction. Please try again with /add.")


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
    Shows user's categories.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    user = update.effective_user
    user_id = str(user.id)

    # Verify authentication
    oauth_manager = context.bot_data.get("oauth_manager")
    if not oauth_manager or not oauth_manager.is_authenticated(user_id):
        await update.message.reply_text("⚠️ You need to authenticate first.\n\nUse /auth to start the authorization process.")
        return

    # Get user categories
    db = SessionLocal()
    try:
        category_manager.load_user_categories(user_id, db)

        expense_categories = category_manager.get_expense_categories(user_id)
        income_categories = category_manager.get_income_categories(user_id)

        message = "*Your custom categories:*\n\n"
        message += "*EXPENSE CATEGORIES:*\n"
        for category, subcategories in expense_categories.items():
            message += f"• {category}\n"
            for subcategory in subcategories:
                message += f"  - {subcategory}\n"

        message += "\n*INCOME CATEGORIES:*\n"
        for category in income_categories:
            message += f"• {category}\n"

        message += "\nYou can customize your categories with the /editcat command"
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error showing categories for user {user_id}: {e}")
        await update.message.reply_text("❌ Error retrieving your categories.")
    finally:
        db.close()


async def reset_categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Resets user's categories to default values.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    user = update.effective_user
    user_id = str(user.id)

    # Verify authentication
    oauth_manager = context.bot_data.get("oauth_manager")
    if not oauth_manager or not oauth_manager.is_authenticated(user_id):
        await update.message.reply_text("⚠️ You need to authenticate first.\n\nUse /auth to start the authorization process.")
        return

    # Create confirmation buttons
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Yes, reset", callback_data="reset_categories|confirm"),
                InlineKeyboardButton("❌ No, cancel", callback_data="reset_categories|cancel"),
            ]
        ]
    )

    await update.message.reply_text(
        "⚠️ Are you sure you want to reset your custom categories to default values?", reply_markup=keyboard
    )


async def edit_categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Starts the category editing flow.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    user = update.effective_user
    user_id = str(user.id)

    # Verify authentication
    oauth_manager = context.bot_data.get("oauth_manager")
    if not oauth_manager or not oauth_manager.is_authenticated(user_id):
        await update.message.reply_text("⚠️ You need to authenticate first.\n\nUse /auth to start the authorization process.")
        return

    # Show editing options
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✏️ Edit expense categories", callback_data="edit_categories|expense")],
            [InlineKeyboardButton("✏️ Edit income categories", callback_data="edit_categories|income")],
            [InlineKeyboardButton("📝 Import from YAML", callback_data="edit_categories|import")],
            [InlineKeyboardButton("📦 Export to YAML", callback_data="edit_categories|export")],
        ]
    )

    await update.message.reply_text("What would you like to do with your categories?", reply_markup=keyboard)


async def process_yaml_import(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processes a YAML file to import categories.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    user = update.effective_user
    user_id = str(user.id)

    # Check if there is an attached document
    if not update.message.document:
        await update.message.reply_text("❌ Please attach a YAML file with your categories.")
        return

    # Verify it is a YAML file
    file = update.message.document
    if not file.file_name.endswith((".yaml", ".yml")):
        await update.message.reply_text("❌ The file must have a .yaml or .yml extension")
        return

    try:
        # Download file
        file_obj = await context.bot.get_file(file.file_id)
        yaml_content = await file_obj.download_as_bytearray()
        yaml_text = yaml_content.decode("utf-8")

        categories_data = yaml.safe_load(yaml_text)

        if not isinstance(categories_data, dict):
            await update.message.reply_text("❌ Incorrect format. The file must contain a YAML dictionary.")
            return

        if "expense_categories" not in categories_data or "income_categories" not in categories_data:
            await update.message.reply_text("❌ Incorrect format. The file must contain 'expense_categories' and 'income_categories'.")
            return

        expense_categories = categories_data["expense_categories"]
        income_categories = categories_data["income_categories"]

        if not isinstance(expense_categories, dict) or not isinstance(income_categories, list):
            await update.message.reply_text("❌ Incorrect format. 'expense_categories' must be a dictionary and 'income_categories' a list.")
            return

        for category, subcategories in expense_categories.items():
            if not isinstance(subcategories, list):
                await update.message.reply_text(f"❌ Incorrect format. Subcategories for '{category}' must be a list.")
                return

        db = SessionLocal()
        try:
            success = category_manager.save_user_categories(user_id, expense_categories, income_categories, db)

            if success:
                await update.message.reply_text("✅ Categories imported successfully.")
            else:
                await update.message.reply_text("❌ Error saving categories.")

        finally:
            db.close()

    except yaml.YAMLError as e:
        await update.message.reply_text(f"❌ Error parsing YAML file: {str(e)}")
        context.user_data.pop("state", None)  # Clear state on error
    except Exception as e:
        logger.error(f"Error importing YAML categories for user {user_id}: {e}")
        await update.message.reply_text("❌ Error processing the categories file.")
        context.user_data.pop("state", None)  # Clear state on error


async def export_categories_to_yaml(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Exports user's categories to a YAML file.

    Args:
        update: Telegram Update object
        context: Handler context
    """
    user = update.effective_user
    user_id = str(user.id)

    db = SessionLocal()
    try:
        category_manager.load_user_categories(user_id, db)

        expense_categories = category_manager.get_expense_categories(user_id)
        income_categories = category_manager.get_income_categories(user_id)

        categories_data = {"expense_categories": expense_categories, "income_categories": income_categories}

        yaml_content = yaml.safe_dump(categories_data, allow_unicode=True, sort_keys=False)

        import tempfile

        temp_file = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False)
        temp_file.write(yaml_content.encode("utf-8"))
        temp_file.close()

        with open(temp_file.name, "rb") as file:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file,
                filename=f"categories_{user.username or user_id}.yaml",
                caption="📦 Your custom categories",
            )

        import os

        os.unlink(temp_file.name)

    except Exception as e:
        logger.error(f"Error exporting YAML categories for user {user_id}: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Error exporting your categories.")
        elif update.effective_message:
            await update.effective_message.reply_text("❌ Error exporting your categories.")
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
        await update.effective_message.reply_text("An error has occurred. Please try again later.")
