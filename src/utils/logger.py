"""
Configuración del sistema de logging usando Loguru.
"""

import sys
from pathlib import Path

from loguru import logger


def setup_logging(log_file: str | Path | None = None, level: str = "INFO") -> None:
    """
    Configura el sistema de logging con Loguru.

    Args:
        log_file: Ruta al archivo de log (opcional)
        level: Nivel de logging (por defecto INFO)
    """
    # Eliminar el handler por defecto
    logger.remove()

    # Formato para los logs
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # Añadir handler para consola
    logger.add(sys.stdout, format=log_format, level=level, colorize=True)

    # Añadir handler para archivo si se especifica
    if log_file:
        # Asegurar que el directorio existe
        if isinstance(log_file, str):
            log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            format=log_format,
            level=level,
            rotation="10 MB",  # Rotación cuando el archivo alcance 10MB
            retention="1 month",  # Mantener logs por 1 mes
            compression="zip",  # Comprimir logs antiguos
        )

        logger.info(f"Logging configurado. Guardando logs en: {log_file}")
    else:
        logger.info("Logging configurado. Solo salida por consola.")


# Exportar logger para uso en todo el proyecto
__all__ = ["logger", "setup_logging"]
