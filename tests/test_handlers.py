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
    """Prueba que el comando /start salude al usuario por su nombre."""
    # Act
    await start_command(mock_telegram_update, mock_context)

    # Assert
    mock_telegram_update.message.reply_text.assert_awaited_once()
    greeting = mock_telegram_update.message.reply_text.call_args[0][0]
    assert f"¡Hola {mock_telegram_update.effective_user.first_name}!" in greeting


@pytest.mark.asyncio
async def test_help_command_content(mock_telegram_update, mock_context):
    """Prueba que el comando /help muestre información sobre todos los comandos disponibles."""
    # Act
    await help_command(mock_telegram_update, mock_context)

    # Assert
    mock_telegram_update.message.reply_text.assert_awaited_once()
    help_text = mock_telegram_update.message.reply_text.call_args[0][0]

    # Verificar que menciona todos los comandos disponibles actualmente
    assert "/start" in help_text
    assert "/help" in help_text

    # Verificar que se está usando Markdown
    assert mock_telegram_update.message.reply_text.call_args[1].get("parse_mode") == "Markdown"


@pytest.mark.asyncio
async def test_error_handler_logging(mock_telegram_update, mock_context, mocker):
    """Prueba que el manejador de errores registre correctamente los errores."""
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
    """Prueba que el manejador de errores envíe un mensaje amigable al usuario."""
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
    """Prueba que el manejador de errores no falle cuando no hay mensaje efectivo."""
    # Arrange
    mock_update = mocker.Mock(spec=Update)
    mock_update.effective_message = None
    mock_context.error = Exception("Error sin mensaje")

    # Act & Assert (no debería lanzar excepción)
    await error_handler(mock_update, mock_context)


@pytest.mark.asyncio
async def test_error_handler_with_none_update(mock_context):
    """Prueba que el manejador de errores maneje correctamente casos sin update."""
    # Arrange
    mock_context.error = Exception("Error sin update")

    # Act & Assert (no debería lanzar excepción)
    await error_handler(None, mock_context)


@pytest.mark.asyncio
async def test_agregar_command(mock_telegram_update, mock_context, mocker):
    """Prueba que el comando /agregar muestre botones con categorías."""
    # Arrange
    mock_sheets = mocker.Mock()
    mock_sheets.get_column_values.return_value = ["Categorías", "COMIDA", "TRANSPORTE", "SALARIO", "comision"]
    mock_context.bot_data = {"sheets_operations": mock_sheets}

    # Act
    await agregar_command(mock_telegram_update, mock_context)

    # Assert
    mock_telegram_update.message.reply_text.assert_awaited_once()
    # Verificar que se llamó a reply_text con un reply_markup (teclado)
    assert "reply_markup" in mock_telegram_update.message.reply_text.call_args[1]
    # Verificar que se solicitaron las categorías desde la hoja de cálculo
    mock_sheets.get_column_values.assert_called_once_with("General", "G")[1:-1]


def test_get_categoria_keyboard():
    """Prueba que el teclado de categorías solo incluya las categorías en mayúsculas."""
    # Arrange
    categorias = ["COMIDA", "transporte", "SALARIO", "ocio"]

    # Act
    keyboard = get_cat_keyboard(categorias, "gasto")

    # Assert
    # Verificar que solo hay botones para las categorías en mayúsculas (más la fila de botones de tipo)
    assert len(keyboard.inline_keyboard) == 3  # 1 fila de botones de tipo + 2 categorías en mayúsculas

    # Verificar que los botones de categorías son correctos
    assert keyboard.inline_keyboard[1][0].text == "COMIDA"
    assert keyboard.inline_keyboard[1][0].callback_data == "gasto|COMIDA"
    assert keyboard.inline_keyboard[2][0].text == "SALARIO"
    assert keyboard.inline_keyboard[2][0].callback_data == "gasto|SALARIO"

    # Verificar que los botones de tipo están presentes
    assert keyboard.inline_keyboard[0][0].text == "GASTOS"
    assert keyboard.inline_keyboard[0][1].text == "INGRESOS"


@pytest.mark.asyncio
async def test_button_callback_selector(mocker):
    """Prueba que el callback de botones actualice el mensaje al seleccionar tipo."""
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
    # Verificar que el mensaje menciona "ingreso"
    assert "ingreso" in mock_query.edit_message_text.call_args[0][0]
    # Verificar que se incluyó un reply_markup
    assert "reply_markup" in mock_query.edit_message_text.call_args[1]


@pytest.mark.asyncio
async def test_button_callback_categoria(mocker):
    """Prueba que el callback de botones solicite el monto al seleccionar categoría."""
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
    # Verificar que el mensaje menciona "COMIDA"
    assert "COMIDA" in mock_query.edit_message_text.call_args[0][0]
    # Verificar que se solicitó el monto
    assert "monto" in mock_query.edit_message_text.call_args[0][0].lower()
    # Verificar que se guardaron los datos en user_data
    assert "transaccion_pendiente" in mock_context.user_data
    assert mock_context.user_data["transaccion_pendiente"]["tipo"] == "gasto"
    assert mock_context.user_data["transaccion_pendiente"]["categoria"] == "COMIDA"
