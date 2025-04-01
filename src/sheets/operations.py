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
        Configura el acceso a la hoja de cálculo y asegura la existencia de hojas necesarias.

        Raises:
            Exception: Si falla la operación
        """
        try:
            self.spreadsheet = self.client.open_spreadsheet(self.spreadsheet_id)
            logger.info(f"Hoja de cálculo configurada: {self.spreadsheet.title}")

            # Inicializar las hojas necesarias
            self.ensure_sheets_exist()
        except Exception as e:
            logger.error(f"Error al configurar la hoja de cálculo: {e}")
            raise

    def ensure_sheets_exist(self) -> None:
        """
        Asegura que existan las hojas necesarias para la aplicación.
        Si no existen, las crea con los encabezados apropiados.
        """
        required_sheets = {
            "gastos": ["Fecha", "Usuario", "Categoría", "Subcategoría", "Monto", "Timestamp", "Comentario"],
            "ingresos": ["Fecha", "Usuario", "Categoría", "Monto", "Timestamp", "Comentario"],
        }

        existing_sheets = [ws.title for ws in self.spreadsheet.worksheets()]

        for sheet_name, headers in required_sheets.items():
            if sheet_name not in existing_sheets:
                # Crear la hoja con los encabezados
                worksheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=1, cols=len(headers))
                worksheet.append_row(headers)
                logger.info(f"Hoja '{sheet_name}' creada con éxito")
            else:
                # Verificar que los encabezados sean correctos
                worksheet = self.spreadsheet.worksheet(sheet_name)
                actual_headers = worksheet.row_values(1)

                if not actual_headers:
                    # La hoja existe pero está vacía
                    worksheet.append_row(headers)
                    logger.info(f"Encabezados añadidos a la hoja '{sheet_name}'")
                elif actual_headers != headers:
                    logger.warning(f"Los encabezados de la hoja '{sheet_name}' no coinciden con los esperados")
                    # No modificamos encabezados existentes para evitar romper datos

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

    def append_row(self, sheet_name: str, values: list[Any]) -> bool:
        """
        Añade una fila de datos al final de una hoja específica.

        Args:
            sheet_name: Nombre de la hoja donde añadir los datos
            values: Lista de valores a añadir como nueva fila

        Returns:
            True si la operación fue exitosa

        Raises:
            ValueError: Si no se encuentra la hoja
            RuntimeError: Si no se ha configurado la hoja de cálculo
        """
        try:
            worksheet = self.get_worksheet(sheet_name)
            worksheet.append_row(values)
            logger.info(f"Datos añadidos a la hoja '{sheet_name}': {values}")
            return True
        except Exception as e:
            logger.error(f"Error al añadir datos a la hoja '{sheet_name}': {e}")
            raise

    def get_column_values(self, sheet_name: str, column: str) -> list[str]:
        """
        Obtiene todos los valores no vacíos de una columna específica.

        Args:
            sheet_name: Nombre de la hoja de donde obtener los datos
            column: Letra de la columna (ej: 'A', 'B', 'G', etc.)

        Returns:
            Lista de valores de la columna, excluyendo celdas vacías

        Raises:
            ValueError: Si no se encuentra la hoja o la columna no es válida
            RuntimeError: Si no se ha configurado la hoja de cálculo
        """
        try:
            # Validar que column sea una letra válida
            if not (isinstance(column, str) and len(column) == 1 and column.isalpha()):
                raise ValueError(f"El valor de columna '{column}' no es válido. Debe ser una letra.")

            worksheet = self.get_worksheet(sheet_name)

            # Obtener el índice numérico de la columna (A=1, B=2, etc.)
            col_idx = ord(column.upper()) - ord("A") + 1

            # Obtener todos los valores de la columna
            all_values = worksheet.col_values(col_idx)

            # Filtrar valores vacíos y devolver el resultado
            return [value for value in all_values if value.strip()]

        except Exception as e:
            logger.error(f"Error al obtener valores de la columna '{column}' en la hoja '{sheet_name}': {e}")
            raise
