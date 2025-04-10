"""
Operaciones para manipular datos en Google Sheets usando gspread con OAuth 2.0.
"""

from typing import Any, Dict, Optional

from gspread import Spreadsheet
from loguru import logger

from .client import GoogleSheetsClient


class SheetsOperations:
    """
    Proporciona operaciones de alto nivel para manipular datos en Google Sheets.
    """

    def __init__(self, client: GoogleSheetsClient) -> None:
        """
        Inicializa las operaciones con un cliente Google Sheets.

        Args:
            client: Cliente Google Sheets con soporte OAuth
        """
        self.client = client
        self.user_spreadsheets: Dict[str, Dict[str, Any]] = {}

    def setup_for_user(self, user_id: str, spreadsheet_id: str) -> bool:
        """
        Configura el acceso a la hoja de cálculo para un usuario específico.

        Args:
            user_id: ID único del usuario
            spreadsheet_id: ID de la hoja de cálculo a utilizar

        Returns:
            True si la configuración fue exitosa

        Raises:
            Exception: Si falla la operación
        """
        try:
            # Verificar si el usuario está autenticado
            if not self.client.is_authenticated(user_id):
                logger.warning(f"Usuario {user_id} no autenticado, intentando autenticar")
                if not self.client.authenticate(user_id):
                    logger.error(f"No se pudo autenticar al usuario {user_id}")
                    return False
            
            # Abrir la hoja de cálculo
            spreadsheet = self.client.open_spreadsheet(user_id, spreadsheet_id)
            
            # Guardar referencia para este usuario
            if user_id not in self.user_spreadsheets:
                self.user_spreadsheets[user_id] = {}
            
            self.user_spreadsheets[user_id]['spreadsheet'] = spreadsheet
            self.user_spreadsheets[user_id]['spreadsheet_id'] = spreadsheet_id
            
            logger.info(f"Hoja de cálculo configurada para usuario {user_id}: {spreadsheet.title}")

            # Inicializar las hojas necesarias
            self.ensure_sheets_exist(user_id)
            return True
            
        except Exception as e:
            logger.error(f"Error al configurar la hoja de cálculo para usuario {user_id}: {e}")
            raise

    def ensure_sheets_exist(self, user_id: str) -> None:
        """
        Asegura que existan las hojas necesarias para la aplicación.
        Si no existen, las crea con los encabezados apropiados.
        
        Args:
            user_id: ID único del usuario
            
        Raises:
            RuntimeError: Si el usuario no tiene una hoja configurada
        """
        if user_id not in self.user_spreadsheets or 'spreadsheet' not in self.user_spreadsheets[user_id]:
            raise RuntimeError(f"No hay hoja configurada para el usuario {user_id}")
        
        spreadsheet = self.user_spreadsheets[user_id]['spreadsheet']
        
        required_sheets = {
            "gastos": ["Fecha", "Usuario", "Categoría", "Subcategoría", "Monto", "Timestamp", "Comentario"],
            "ingresos": ["Fecha", "Usuario", "Categoría", "Monto", "Timestamp", "Comentario"],
        }

        existing_sheets = [ws.title for ws in spreadsheet.worksheets()]

        for sheet_name, headers in required_sheets.items():
            if sheet_name not in existing_sheets:
                # Crear la hoja con los encabezados
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1, cols=len(headers))
                worksheet.append_row(headers)
                logger.info(f"Hoja '{sheet_name}' creada con éxito para usuario {user_id}")
            else:
                # Verificar que los encabezados sean correctos
                worksheet = spreadsheet.worksheet(sheet_name)
                actual_headers = worksheet.row_values(1)

                if not actual_headers:
                    # La hoja existe pero está vacía
                    worksheet.append_row(headers)
                    logger.info(f"Encabezados añadidos a la hoja '{sheet_name}' para usuario {user_id}")
                elif actual_headers != headers:
                    logger.warning(f"Los encabezados de la hoja '{sheet_name}' no coinciden con los esperados para usuario {user_id}")
                    # No modificamos encabezados existentes para evitar romper datos

    def get_worksheet(self, user_id: str, sheet_name: str) -> Any:
        """
        Obtiene una hoja de trabajo específica para un usuario.

        Args:
            user_id: ID único del usuario
            sheet_name: Nombre de la hoja

        Returns:
            Objeto Worksheet de gspread

        Raises:
            ValueError: Si no se encuentra la hoja
            RuntimeError: Si no se ha configurado la hoja para el usuario
        """
        if user_id not in self.user_spreadsheets or 'spreadsheet' not in self.user_spreadsheets[user_id]:
            raise RuntimeError(f"No hay hoja configurada para el usuario {user_id}")

        spreadsheet = self.user_spreadsheets[user_id]['spreadsheet']
        
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            return worksheet
        except Exception as e:
            logger.error(f"Error al obtener la hoja '{sheet_name}' para usuario {user_id}: {e}")
            raise ValueError(f"La hoja '{sheet_name}' no existe para usuario {user_id}")

    def append_row(self, user_id: str, sheet_name: str, values: list[Any]) -> bool:
        """
        Añade una fila de datos al final de una hoja específica para un usuario.

        Args:
            user_id: ID único del usuario
            sheet_name: Nombre de la hoja donde añadir los datos
            values: Lista de valores a añadir como nueva fila

        Returns:
            True si la operación fue exitosa

        Raises:
            ValueError: Si no se encuentra la hoja
            RuntimeError: Si no se ha configurado la hoja para el usuario
        """
        try:
            worksheet = self.get_worksheet(user_id, sheet_name)
            worksheet.append_row(values)
            logger.info(f"Datos añadidos a la hoja '{sheet_name}' para usuario {user_id}: {values}")
            return True
        except Exception as e:
            logger.error(f"Error al añadir datos a la hoja '{sheet_name}' para usuario {user_id}: {e}")
            raise

    def get_column_values(self, user_id: str, sheet_name: str, column: str) -> list[str]:
        """
        Obtiene todos los valores no vacíos de una columna específica para un usuario.

        Args:
            user_id: ID único del usuario
            sheet_name: Nombre de la hoja de donde obtener los datos
            column: Letra de la columna (ej: 'A', 'B', 'G', etc.)

        Returns:
            Lista de valores de la columna, excluyendo celdas vacías

        Raises:
            ValueError: Si no se encuentra la hoja o la columna no es válida
            RuntimeError: Si no se ha configurado la hoja para el usuario
        """
        try:
            # Validar que column sea una letra válida
            if not (isinstance(column, str) and len(column) == 1 and column.isalpha()):
                raise ValueError(f"El valor de columna '{column}' no es válido. Debe ser una letra.")

            worksheet = self.get_worksheet(user_id, sheet_name)

            # Obtener el índice numérico de la columna (A=1, B=2, etc.)
            col_idx = ord(column.upper()) - ord("A") + 1

            # Obtener todos los valores de la columna
            all_values = worksheet.col_values(col_idx)

            # Filtrar valores vacíos y devolver el resultado
            return [value for value in all_values if value.strip()]

        except Exception as e:
            logger.error(f"Error al obtener valores de la columna '{column}' en la hoja '{sheet_name}' para usuario {user_id}: {e}")
            raise
    
    def list_spreadsheets(self, user_id: str) -> list:
        """
        Lista todas las hojas de cálculo accesibles para un usuario.

        Args:
            user_id: ID único del usuario

        Returns:
            Lista de hojas de cálculo con sus IDs y títulos

        Raises:
            RuntimeError: Si el usuario no está autenticado
        """
        try:
            # Verificar si el usuario está autenticado
            if not self.client.is_authenticated(user_id):
                logger.warning(f"Usuario {user_id} no autenticado, intentando autenticar")
                if not self.client.authenticate(user_id):
                    raise RuntimeError(f"El usuario {user_id} no está autenticado")
            
            # Obtener lista de hojas
            spreadsheets = self.client.list_spreadsheets(user_id)
            
            # Transformar a formato más amigable
            result = []
            for sheet in spreadsheets:
                result.append({
                    'id': sheet.id,
                    'name': sheet.name,
                    'url': sheet.url
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error al listar hojas de cálculo para usuario {user_id}: {e}")
            raise
    
    def set_active_spreadsheet(self, user_id: str, spreadsheet_id: str) -> bool:
        """
        Establece una hoja de cálculo como activa para un usuario.

        Args:
            user_id: ID único del usuario
            spreadsheet_id: ID de la hoja a establecer como activa

        Returns:
            True si se configuró correctamente

        Raises:
            RuntimeError: Si hay un error al configurar la hoja
        """
        try:
            return self.setup_for_user(user_id, spreadsheet_id)
        except Exception as e:
            logger.error(f"Error al establecer hoja activa para usuario {user_id}: {e}")
            raise RuntimeError(f"No se pudo establecer la hoja activa: {e}")
