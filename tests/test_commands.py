"""
Tests para el módulo de comandos del bot de Telegram.
"""

import pytest
from telegram import BotCommand

from src.bot.commands import get_commands


def test_get_commands_structure():
    """Verifica la estructura de la lista de comandos."""
    commands = get_commands()

    # Verify that a list is returned
    assert isinstance(commands, list)

    # Verify that all elements are instances of BotCommand
    for cmd in commands:
        assert isinstance(cmd, BotCommand)


def test_get_commands_content():
    """Verifica el contenido de la lista de comandos."""
    commands = get_commands()

    # Create a dictionary to verify commands and their descriptions
    cmd_dict = {cmd.command: cmd.description for cmd in commands}

    # Verify the basic commands that should be present
    assert "start" in cmd_dict
    assert "help" in cmd_dict

    # Verify that descriptions are not empty
    for description in cmd_dict.values():
        assert description.strip(), "La descripción no debe estar vacía"


def test_get_commands_extensibility():
    """
    Verifica que la función get_commands devuelva al menos los comandos básicos
    y esté preparada para añadir más comandos en el futuro.
    """
    commands = get_commands()

    # Verify the minimum required commands
    assert len(commands) >= 2

    # Verify that there are no duplicate commands
    command_names = [cmd.command for cmd in commands]
    assert len(command_names) == len(set(command_names)), "No debe haber comandos duplicados"

    # Comment in the original code indicates that more commands will be added
    # The structure should allow for this extensibility
