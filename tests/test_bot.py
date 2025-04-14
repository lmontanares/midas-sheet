"""
Tests para el módulo del bot de Telegram.
"""

import pytest
from telegram import BotCommand, Update, User
from telegram.ext import Application, ApplicationBuilder, CommandHandler

from src.bot.bot import TelegramBot
from src.bot.commands import get_commands
from src.bot.handlers import error_handler, help_command, start_command


def test_get_commands():
    """Verifica que la lista de comandos no está vacía y contiene los comandos básicos."""
    commands = get_commands()
    assert len(commands) > 0
    assert any(cmd.command == "start" for cmd in commands)
    assert any(cmd.command == "help" for cmd in commands)

    # Verify that each command has a non-empty description
    for cmd in commands:
        assert isinstance(cmd, BotCommand)
        assert cmd.command, "El comando no debe estar vacío"
        assert cmd.description, "La descripción del comando no debe estar vacía"


@pytest.mark.asyncio
async def test_bot_initialization():
    """Test bot initialization."""
    # Arrange
    token = "test_token_123"

    # Act
    bot = TelegramBot(token)

    # Assert
    assert bot.token == token
    assert bot.application is None


@pytest.mark.asyncio
async def test_bot_setup(mocker):
    """Test bot configuration."""
    # Arrange
    token = "test_token_123"

    # Create mock objects
    mock_app = mocker.Mock()
    mock_app.add_handler = mocker.Mock()
    mock_app.add_error_handler = mocker.Mock()
    mock_app.bot = mocker.Mock()
    mock_app.bot.set_my_commands = mocker.AsyncMock()

    # Create a mock for ApplicationBuilder
    mock_builder = mocker.Mock()
    mock_builder.token.return_value = mock_builder
    mock_builder.build.return_value = mock_app

    # Use mocker to replace ApplicationBuilder
    mocker.patch("telegram.ext.ApplicationBuilder", return_value=mock_builder)

    # Act
    bot = TelegramBot(token)
    await bot.setup()

    # Assert
    assert bot.application is not None
    assert mock_builder.token.call_args[0][0] == token

    # Verify that command handlers were added
    assert mock_app.add_handler.call_count >= 2

    # Verify that commands were configured in the bot menu
    mock_app.bot.set_my_commands.assert_awaited_once()


@pytest.mark.asyncio
async def test_bot_run_without_setup():
    """Test that the bot cannot run without prior configuration."""
    # Arrange
    token = "test_token_123"
    bot = TelegramBot(token)

    # Act & Assert
    with pytest.raises(RuntimeError) as excinfo:
        await bot.run()

    assert "El bot debe ser configurado antes de ejecutarse" in str(excinfo.value)


@pytest.mark.asyncio
async def test_bot_run(mocker):
    """Test bot execution."""
    # Arrange
    token = "test_token_123"

    # Create mock objects
    mock_app = mocker.Mock()
    mock_app.add_handler = mocker.Mock()
    mock_app.add_error_handler = mocker.Mock()
    mock_app.bot = mocker.Mock()
    mock_app.bot.set_my_commands = mocker.AsyncMock()
    mock_app.run_polling = mocker.AsyncMock()

    # Create a mock for ApplicationBuilder
    mock_builder = mocker.Mock()
    mock_builder.token.return_value = mock_builder
    mock_builder.build.return_value = mock_app

    # Use mocker to replace ApplicationBuilder
    mocker.patch("telegram.ext.ApplicationBuilder", return_value=mock_builder)

    # Act
    bot = TelegramBot(token)
    await bot.setup()
    await bot.run()

    # Assert
    mock_app.run_polling.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_command(mocker):
    """Test the /start command handler."""
    # Arrange
    mock_user = mocker.Mock(spec=User)
    mock_user.first_name = "Usuario"

    mock_update = mocker.Mock(spec=Update)
    mock_update.effective_user = mock_user
    mock_update.message = mocker.Mock()
    mock_update.message.reply_text = mocker.AsyncMock()

    mock_context = mocker.Mock()

    # Act
    await start_command(mock_update, mock_context)

    # Assert
    mock_update.message.reply_text.assert_awaited_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "¡Hola Usuario!" in call_args
    assert "gestión financiera" in call_args


@pytest.mark.asyncio
async def test_help_command(mocker):
    """Test the /help command handler."""
    # Arrange
    mock_update = mocker.Mock(spec=Update)
    mock_update.message = mocker.Mock()
    mock_update.message.reply_text = mocker.AsyncMock()

    mock_context = mocker.Mock()

    # Act
    await help_command(mock_update, mock_context)

    # Assert
    mock_update.message.reply_text.assert_awaited_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "/start" in call_args
    assert "/help" in call_args

    # Verify that Markdown parse mode was specified
    assert mock_update.message.reply_text.call_args[1].get("parse_mode") == "Markdown"


@pytest.mark.asyncio
async def test_error_handler_with_update(mocker):
    """Test the error handler when there is an Update."""
    # Arrange
    mock_update = mocker.Mock(spec=Update)
    mock_update.effective_message = mocker.Mock()
    mock_update.effective_message.reply_text = mocker.AsyncMock()

    mock_context = mocker.Mock()
    mock_context.error = Exception("Error de prueba")

    # Act
    await error_handler(mock_update, mock_context)

    # Assert
    mock_update.effective_message.reply_text.assert_awaited_once()
    call_args = mock_update.effective_message.reply_text.call_args[0][0]
    assert "Ha ocurrido un error" in call_args


@pytest.mark.asyncio
async def test_error_handler_without_update(mocker):
    """Test the error handler when there is no Update."""
    # Arrange
    mock_context = mocker.Mock()
    mock_context.error = Exception("Error de prueba")

    # Act & Assert - should not raise an exception
    await error_handler(None, mock_context)
