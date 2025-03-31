"""
Tests para el módulo del bot de Telegram.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.bot.bot import TelegramBot
from src.bot.commands import get_commands


def test_get_commands():
    """Verifica que la lista de comandos no está vacía."""
    commands = get_commands()
    assert len(commands) > 0
    assert any(cmd.command == "start" for cmd in commands)
    assert any(cmd.command == "help" for cmd in commands)


@pytest.mark.asyncio
async def test_bot_initialization():
    """Prueba la inicialización del bot."""
    # Arrange
    token = "test_token_123"

    # Act
    bot = TelegramBot(token)

    # Assert
    assert bot.token == token
    assert bot.application is None


@pytest.mark.asyncio
@patch("telegram.ext.ApplicationBuilder")
async def test_bot_setup(mock_builder):
    """Prueba la configuración del bot."""
    # Arrange
    token = "test_token_123"
    mock_app = AsyncMock()
    mock_builder.return_value.token.return_value.build.return_value = mock_app

    # Act
    bot = TelegramBot(token)
    await bot.setup()

    # Assert
    assert bot.application is not None
    mock_builder.return_value.token.assert_called_once_with(token)
