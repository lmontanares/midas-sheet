"""
Tests específicos para los manejadores de comandos del bot de Telegram.
"""

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from src.bot.handlers import agregar_command, button_callback, error_handler, get_cat_keyboard, help_command, start_command


@pytest.fixture
def mock_telegram_update(mocker):
    """Fixture para crear un mock de Update de Telegram."""
    mock_user = mocker.Mock(spec=User)
    mock_user.first_name = "TestUser"
    mock_user.id = 12345

    mock_chat = mocker.Mock(spec=Chat)
    mock_chat.id = 67890

    mock_message = mocker.Mock(spec=Message)
    mock_message.chat = mock_chat
    mock_message.reply_text = mocker.AsyncMock()

    mock_update = mocker.Mock(spec=Update)
    mock_update.effective_user = mock_user
    mock_update.message = mock_message
    mock_update.effective_message = mock_message

    return mock_update


@pytest.fixture
def mock_context(mocker):
    """Fixture para crear un mock de Context."""
    return mocker.Mock(spec=ContextTypes.DEFAULT_TYPE)


@pytest.mark.asyncio
async def test_start_command_greeting(mock_telegram_update, mock_context):
    """Test that the /start command greets the user by name."""
    # Act
    await start_command(mock_telegram_update, mock_context)

    # Assert
    mock_telegram_update.message.reply_text.assert_awaited_once()
    greeting = mock_telegram_update.message.reply_text.call_args[0][0]
    assert f"¡Hola {mock_telegram_update.effective_user.first_name}!" in greeting


@pytest.mark.asyncio
async def test_help_command_content(mock_telegram_update, mock_context):
    """Test that the /help command shows information about all available commands."""
    # Act
    await help_command(mock_telegram_update, mock_context)

    # Assert
    mock_telegram_update.message.reply_text.assert_awaited_once()
    help_text = mock_telegram_update.message.reply_text.call_args[0][0]

    # Verify that it mentions all currently available commands
    assert "/start" in help_text
    assert "/help" in help_text

    # Verify that Markdown is being used
    assert mock_telegram_update.message.reply_text.call_args[1].get("parse_mode") == "Markdown"


@pytest.mark.asyncio
async def test_error_handler_logging(mock_telegram_update, mock_context, mocker):
    """Test that the error handler correctly logs errors."""
    # Arrange
    mock_context.error = ValueError("Error de prueba")
    mock_logger = mocker.patch("src.bot.handlers.logger.exception")

    # Act
    await error_handler(mock_telegram_update, mock_context)

    # Assert
    mock_logger.assert_called_once()
    assert "Error: Error de prueba" in mock_logger.call_args[0][0]


@pytest.mark.asyncio
async def test_error_handler_user_message(mock_telegram_update, mock_context):
    """Test that the error handler sends a friendly message to the user."""
    # Arrange
    mock_context.error = Exception("Error interno")

    # Act
    await error_handler(mock_telegram_update, mock_context)

    # Assert
    mock_telegram_update.effective_message.reply_text.assert_awaited_once()
    error_message = mock_telegram_update.effective_message.reply_text.call_args[0][0]
    assert "Ha ocurrido un error" in error_message
    assert "intenta nuevamente" in error_message


@pytest.mark.asyncio
async def test_error_handler_no_message(mock_context, mocker):
    """Test that the error handler does not fail when there is no effective message."""
    # Arrange
    mock_update = mocker.Mock(spec=Update)
    mock_update.effective_message = None
    mock_context.error = Exception("Error sin mensaje")

    # Act & Assert (should not raise exception)
    await error_handler(mock_update, mock_context)


@pytest.mark.asyncio
async def test_error_handler_with_none_update(mock_context):
    """Test that the error handler correctly handles cases without an update."""
    # Arrange
    mock_context.error = Exception("Error sin update")

    # Act & Assert (should not raise exception)
    await error_handler(None, mock_context)


@pytest.mark.asyncio
async def test_agregar_command(mock_telegram_update, mock_context, mocker):
    """Test that the /agregar command shows buttons with categories."""
    # Arrange
    mock_sheets = mocker.Mock()
    mock_sheets.get_column_values.return_value = ["Categorías", "COMIDA", "TRANSPORTE", "SALARIO", "comision"]
    mock_context.bot_data = {"sheets_operations": mock_sheets}

    # Act
    await agregar_command(mock_telegram_update, mock_context)

    # Assert
    mock_telegram_update.message.reply_text.assert_awaited_once()
    # Verify that reply_text was called with a reply_markup (keyboard)
    assert "reply_markup" in mock_telegram_update.message.reply_text.call_args[1]
    # Verify that categories were requested from the spreadsheet
    mock_sheets.get_column_values.assert_called_once_with("General", "G")[1:-1]  # TODO: This assertion seems incorrect, review sheet structure/mock


def test_get_categoria_keyboard():
    """Test that the category keyboard only includes uppercase categories."""
    # Arrange
    categorias = ["COMIDA", "transporte", "SALARIO", "ocio"]

    # Act
    keyboard = get_cat_keyboard(categorias, "gasto")

    # Assert
    # Verify that there are only buttons for uppercase categories (plus the type button row)
    assert len(keyboard.inline_keyboard) == 3  # 1 row of type buttons + 2 uppercase categories

    # Verify that the category buttons are correct
    assert keyboard.inline_keyboard[1][0].text == "COMIDA"
    assert keyboard.inline_keyboard[1][0].callback_data == "gasto|COMIDA"
    assert keyboard.inline_keyboard[2][0].text == "SALARIO"
    assert keyboard.inline_keyboard[2][0].callback_data == "gasto|SALARIO"

    # Verify that the type buttons are present
    assert keyboard.inline_keyboard[0][0].text == "GASTOS"
    assert keyboard.inline_keyboard[0][1].text == "INGRESOS"


@pytest.mark.asyncio
async def test_button_callback_selector(mocker):
    """Test that the button callback updates the message when selecting a type."""
    # Arrange
    mock_query = mocker.Mock()
    mock_query.answer = mocker.AsyncMock()
    mock_query.edit_message_text = mocker.AsyncMock()
    mock_query.data = "selector|ingreso"

    mock_update = mocker.Mock()
    mock_update.callback_query = mock_query

    mock_context = mocker.Mock()
    mock_sheets = mocker.Mock()
    mock_sheets.get_column_values.return_value = ["Categorías", "COMIDA", "TRANSPORTE"]
    mock_context.bot_data = {"sheets_operations": mock_sheets}

    # Act
    await button_callback(mock_update, mock_context)

    # Assert
    mock_query.answer.assert_awaited_once()
    mock_query.edit_message_text.assert_awaited_once()
    # Verify that the message mentions "ingreso" (income)
    assert "ingreso" in mock_query.edit_message_text.call_args[0][0]
    # Verify that a reply_markup was included
    assert "reply_markup" in mock_query.edit_message_text.call_args[1]


@pytest.mark.asyncio
async def test_button_callback_categoria(mocker):
    """Test that the button callback requests the amount when selecting a category."""
    # Arrange
    mock_query = mocker.Mock()
    mock_query.answer = mocker.AsyncMock()
    mock_query.edit_message_text = mocker.AsyncMock()
    mock_query.data = "gasto|COMIDA"

    mock_update = mocker.Mock()
    mock_update.callback_query = mock_query

    mock_context = mocker.Mock()
    mock_context.user_data = {}

    # Act
    await button_callback(mock_update, mock_context)

    # Assert
    mock_query.answer.assert_awaited_once()
    mock_query.edit_message_text.assert_awaited_once()
    # Verify that the message mentions "COMIDA" (FOOD)
    assert "COMIDA" in mock_query.edit_message_text.call_args[0][0]
    # Verify that the amount was requested
    assert "monto" in mock_query.edit_message_text.call_args[0][0].lower()
    # Verify that the data was saved in user_data
    assert "transaccion_pendiente" in mock_context.user_data
    assert mock_context.user_data["transaccion_pendiente"]["tipo"] == "gasto"
    assert mock_context.user_data["transaccion_pendiente"]["categoria"] == "COMIDA"
