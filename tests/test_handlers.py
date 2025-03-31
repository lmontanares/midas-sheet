"""
Tests específicos para los manejadores de comandos del bot de Telegram.
"""

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from src.bot.handlers import error_handler, help_command, start_command


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
