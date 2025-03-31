"""
Cliente para interactuar con Google Sheets usando gspread.
"""

from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from loguru import logger


class GoogleSheetsClient:
    """
    Cliente para interactuar con Google Sheets usando gspread.

    Maneja la autenticación y proporciona métodos para interactuar con hojas de cálculo.
    """

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    def __init__(self, credentials_file: str) -> None:
        """
        Inicializa el cliente de Google Sheets.

        Args:
            credentials_file: Ruta al archivo de credenciales JSON
        """
        self.credentials_file = credentials_file
        self.client = None

    def authenticate(self) -> None:
        """
        Autentica con Google Sheets usando gspread.

        Raises:
            FileNotFoundError: Si no se encuentra el archivo de credenciales
            Exception: Si falla la autenticación
        """
        try:
            credentials = Credentials.from_service_account_file(self.credentials_file, scopes=self.SCOPES)
            self.client = gspread.authorize(credentials)
            logger.info("Autenticación exitosa con Google Sheets")
        except FileNotFoundError:
            logger.error(f"No se encontró el archivo de credenciales: {self.credentials_file}")
            raise
        except Exception as e:
            logger.error(f"Error al autenticar con Google Sheets: {e}")
            raise

    def open_spreadsheet(self, spreadsheet_id: str) -> Any:
        """
        Abre una hoja de cálculo por su ID.

        Args:
            spreadsheet_id: ID de la hoja de cálculo

        Returns:
            Objeto Spreadsheet de gspread

        Raises:
            RuntimeError: Si no se ha autenticado previamente
        """
        if not self.client:
            raise RuntimeError("Debes autenticar antes de realizar operaciones")

        try:
            return self.client.open_by_key(spreadsheet_id)
        except Exception as e:
            logger.error(f"Error al abrir la hoja de cálculo: {e}")
            raise
