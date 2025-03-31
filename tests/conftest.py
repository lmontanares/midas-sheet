"""
Fixtures comunes para las pruebas del bot de Telegram.
"""

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import Application, ContextTypes


@pytest.fixture
def mock_user(mocker):
    """Fixture para crear un mock de Usuario de Telegram."""
    mock = mocker.Mock(spec=User)
    mock.id = 12345
    mock.first_name = "TestUser"
    mock.last_name = "Apellido"
    mock.username = "testuser"
    mock.is_bot = False
    return mock


@pytest.fixture
def mock_chat(mocker):
    """Fixture para crear un mock de Chat de Telegram."""
    mock = mocker.Mock(spec=Chat)
    mock.id = 67890
    mock.type = "private"
    return mock


@pytest.fixture
def mock_message(mocker, mock_chat):
    """Fixture para crear un mock de Mensaje de Telegram."""
    mock = mocker.Mock(spec=Message)
    mock.message_id = 54321
    mock.chat = mock_chat
    mock.text = "/comando test"
    mock.reply_text = mocker.AsyncMock()
    return mock


@pytest.fixture
def mock_update(mock_user, mock_message):
    """Fixture para crear un mock de Update de Telegram."""
    mock = mocker.Mock(spec=Update)
    mock.update_id = 98765
    mock.message = mock_message
    mock.effective_message = mock_message
    mock.effective_user = mock_user
    mock.effective_chat = mock_message.chat
    return mock


@pytest.fixture
def mock_context(mocker):
    """Fixture para crear un mock de Context de Telegram."""
    mock = mocker.Mock(spec=ContextTypes.DEFAULT_TYPE)
    mock.bot = mocker.Mock()
    mock.bot.send_message = mocker.AsyncMock()
    return mock


@pytest.fixture
def mock_application(mocker):
    """Fixture para crear un mock de Application de Telegram."""
    mock = mocker.Mock(spec=Application)
    mock.bot = mocker.Mock()
    mock.bot.set_my_commands = mocker.AsyncMock()
    mock.add_handler = mocker.Mock()
    mock.add_error_handler = mocker.Mock()
    mock.run_polling = mocker.AsyncMock()
    return mock
