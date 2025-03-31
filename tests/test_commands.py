"""
Tests para el módulo de comandos del bot de Telegram.
"""

import pytest
from telegram import BotCommand

from src.bot.commands import get_commands


def test_get_commands_structure():
    """Verifica la estructura de la lista de comandos."""
    commands = get_commands()
    
    # Verificar que se devuelve una lista
    assert isinstance(commands, list)
    
    # Verificar que todos los elementos son instancias de BotCommand
    for cmd in commands:
        assert isinstance(cmd, BotCommand)


def test_get_commands_content():
    """Verifica el contenido de la lista de comandos."""
    commands = get_commands()
    
    # Crear un diccionario para verificar los comandos y sus descripciones
    cmd_dict = {cmd.command: cmd.description for cmd in commands}
    
    # Verificar los comandos básicos que deberían estar presentes
    assert "start" in cmd_dict
    assert "help" in cmd_dict
    
    # Verificar que las descripciones no estén vacías
    for description in cmd_dict.values():
        assert description.strip(), "La descripción no debe estar vacía"


def test_get_commands_extensibility():
    """
    Verifica que la función get_commands devuelva al menos los comandos básicos
    y esté preparada para añadir más comandos en el futuro.
    """
    commands = get_commands()
    
    # Verificar los comandos mínimos requeridos
    assert len(commands) >= 2
    
    # Verificar que no hay comandos duplicados
    command_names = [cmd.command for cmd in commands]
    assert len(command_names) == len(set(command_names)), "No debe haber comandos duplicados"
    
    # Comentario en el código original indica que se añadirán más comandos
    # La estructura debe permitir esta extensibilidad
