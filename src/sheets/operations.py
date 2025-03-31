"""
Operaciones para manipular datos en Google Sheets usando gspread.
"""

from typing import Any

from gspread import Spreadsheet
from loguru import logger

from .client import GoogleSheetsClient


class SheetsOperations:
    """
    Proporciona operaciones de alto nivel para manipular datos en Google Sheets.
    """

    def __init__(self, client: GoogleSheetsClient, spreadsheet_id: str) -> None:
        """
        Inicializa las operaciones con un cliente Google Sheets.

        Args:
            client: Cliente Google Sheets autenticado
            spreadsheet_id: ID de la hoja de cálculo a utilizar
        """
        self.client = client
        self.spreadsheet_id = spreadsheet_id
        self.spreadsheet: Spreadsheet

    def setup(self) -> None:
        """
        Configura el acceso a la hoja de cálculo.

        Raises:
            Exception: Si falla la operación
        """
        try:
            self.spreadsheet = self.client.open_spreadsheet(self.spreadsheet_id)
            logger.info(f"Hoja de cálculo configurada: {self.spreadsheet.title}")
        except Exception as e:
            logger.error(f"Error al configurar la hoja de cálculo: {e}")
            raise

    def get_worksheet(self, sheet_name: str) -> Any:
        """
        Obtiene una hoja de trabajo específica.

        Args:
            sheet_name: Nombre de la hoja

        Returns:
            Objeto Worksheet de gspread

        Raises:
            ValueError: Si no se encuentra la hoja
            RuntimeError: Si no se ha configurado la hoja de cálculo
        """
        if not self.spreadsheet:
            raise RuntimeError("Debes configurar la hoja de cálculo antes de realizar operaciones")

        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            return worksheet
        except Exception as e:
            logger.error(f"Error al obtener la hoja '{sheet_name}': {e}")
            raise ValueError(f"La hoja '{sheet_name}' no existe")
