"""
Operaciones para manipular datos en Google Sheets usando gspread con OAuth 2.0.
Interactúa con la base de datos para obtener la hoja de cálculo activa del usuario.
"""

from typing import Any

import gspread
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.database import SessionLocal, UserSheet
from .client import GoogleSheetsClient


class SheetsOperations:
    """
    Proporciona operaciones de alto nivel para manipular datos en Google Sheets.
    Obtiene la hoja de cálculo activa del usuario desde la base de datos.
    """

    def __init__(self, client: GoogleSheetsClient) -> None:
        """
        Inicializa las operaciones con un cliente Google Sheets.

        Args:
            client: Cliente Google Sheets con soporte OAuth
        """
        self.client = client
        # self.user_spreadsheets: dict[str, dict[str, Any]] = {} # Removed: Store active sheet in DB

    def _get_active_spreadsheet_id(self, db: Session, user_id: str) -> str | None:
        """Obtiene el ID de la hoja de cálculo activa para el usuario desde la BD."""
        stmt = select(UserSheet.spreadsheet_id).where(
            UserSheet.user_id == user_id,
            UserSheet.is_active == True,  # noqa: E712
        )
        spreadsheet_id = db.scalars(stmt).first()
        if not spreadsheet_id:
            logger.warning(f"No active spreadsheet found in DB for user {user_id}")
            return None
        return spreadsheet_id

    def setup_for_user(self, user_id: str, spreadsheet_id: str) -> str | None:
        """
        Verifica el acceso a la hoja de cálculo para un usuario específico y la prepara.
        NO guarda la referencia en memoria, solo verifica y asegura hojas internas.
        La hoja activa se guarda en la BD a través del handler del comando /sheet.

        Args:
            user_id: ID único del usuario
            spreadsheet_id: ID de la hoja de cálculo a verificar y configurar

        Returns:
            El título de la hoja de cálculo si la configuración fue exitosa, None si falla.

        Raises:
            Exception: Si falla la operación (propagada desde self.client o ensure_sheets_exist)
        """
        try:
            # Verificar si el usuario está autenticado
            if not self.client.is_authenticated(user_id):
                logger.warning(f"User {user_id} not authenticated for setup_for_user")
                return None  # Indicate failure clearly

            # Abrir la hoja de cálculo para verificar acceso y obtener título
            spreadsheet = self.client.open_spreadsheet(user_id, spreadsheet_id)
            if not spreadsheet:  # Should be handled by exceptions in open_spreadsheet, but check anyway
                logger.error(f"Failed to open spreadsheet {spreadsheet_id} for user {user_id} during setup.")
                return None

            logger.info(f"Spreadsheet '{spreadsheet.title}' (ID: {spreadsheet_id}) accessed successfully for user {user_id}.")

            # Asegurar que las hojas internas ("gastos", "ingresos") existan en la hoja verificada
            # Pasamos el objeto spreadsheet directamente para evitar abrirlo de nuevo
            self.ensure_sheets_exist(user_id, spreadsheet)

            # Devolver el título para confirmación en el bot handler
            return spreadsheet.title

        except Exception as e:
            # Exceptions like SpreadsheetNotFound, APIError, GoogleAuthError are raised by client
            logger.error(f"Error setting up spreadsheet {spreadsheet_id} for user {user_id}: {e}")
            raise  # Re-raise para que el handler del bot lo maneje

    def ensure_sheets_exist(self, user_id: str, spreadsheet: gspread.Spreadsheet) -> None:
        """
        Asegura que existan las hojas internas necesarias ("gastos", "ingresos")
        en la hoja de cálculo proporcionada. Si no existen, las crea.

        Args:
            user_id: ID único del usuario (para logging)
            spreadsheet: El objeto gspread.Spreadsheet ya abierto y verificado.

        Raises:
            APIError: Si hay problemas al interactuar con la API de Sheets.
            Exception: Para otros errores inesperados.
        """
        if not spreadsheet:
            raise ValueError("Spreadsheet object cannot be None for ensure_sheets_exist")

        logger.debug(f"Ensuring internal sheets exist in '{spreadsheet.title}' for user {user_id}")

        required_sheets = {
            "gastos": ["Fecha", "Usuario", "Categoría", "Subcategoría", "Monto", "Timestamp", "Comentario"],
            "ingresos": ["Fecha", "Usuario", "Categoría", "Monto", "Timestamp", "Comentario"],
        }

        try:
            existing_sheets = [ws.title for ws in spreadsheet.worksheets()]

            for sheet_name, headers in required_sheets.items():
                if sheet_name not in existing_sheets:
                    # Crear la hoja con los encabezados
                    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1, cols=len(headers))
                    worksheet.append_row(headers)
                    logger.info(f"Internal sheet '{sheet_name}' created in '{spreadsheet.title}' for user {user_id}")
                else:
                    # Verificar que los encabezados sean correctos (opcional, como antes)
                    worksheet = spreadsheet.worksheet(sheet_name)
                    actual_headers = worksheet.row_values(1)

                    if not actual_headers:
                        # La hoja existe pero está vacía
                        worksheet.append_row(headers)
                        logger.info(f"Headers added to empty internal sheet '{sheet_name}' in '{spreadsheet.title}' for user {user_id}")
                    elif actual_headers != headers:
                        logger.warning(
                            f"Headers in existing internal sheet '{sheet_name}' do not match expected for user {user_id} in '{spreadsheet.title}'. "
                            "Not modifying existing headers."
                        )
        except gspread.exceptions.APIError as e:
            logger.error(f"API error ensuring internal sheets exist for user {user_id} in '{spreadsheet.title}': {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error ensuring internal sheets exist for user {user_id} in '{spreadsheet.title}': {e}")
            raise

    def get_worksheet(self, user_id: str, sheet_name: str) -> gspread.Worksheet | None:
        """
        Obtiene una hoja de trabajo específica de la hoja de cálculo activa del usuario.

        Args:
            user_id: ID único del usuario
            sheet_name: Nombre de la hoja ("gastos" o "ingresos")

        Returns:
            Objeto Worksheet de gspread o None si no se encuentra la hoja activa o la hoja interna.

        Raises:
            RuntimeError: Si el usuario no está autenticado.
            APIError: Si hay problemas al interactuar con la API de Sheets.
            Exception: Para otros errores inesperados.
        """
        db: Session | None = None
        try:
            # 1. Verificar autenticación
            if not self.client.is_authenticated(user_id):
                raise RuntimeError(f"User {user_id} is not authenticated.")

            # 2. Obtener ID de la hoja activa desde la BD
            db = SessionLocal()
            spreadsheet_id = self._get_active_spreadsheet_id(db, user_id)
            if not spreadsheet_id:
                # Logged in _get_active_spreadsheet_id
                return None  # No active sheet configured

            # 3. Abrir la hoja de cálculo principal
            # Exceptions (SpreadsheetNotFound, APIError, AuthError) handled by client
            spreadsheet = self.client.open_spreadsheet(user_id, spreadsheet_id)
            if not spreadsheet:
                logger.error(f"Failed to open active spreadsheet {spreadsheet_id} for user {user_id} in get_worksheet.")
                return None  # Should have been caught by exception, but safety check

            # 4. Obtener la hoja interna específica
            worksheet = spreadsheet.worksheet(sheet_name)
            logger.debug(f"Retrieved worksheet '{sheet_name}' from spreadsheet '{spreadsheet.title}' for user {user_id}")
            return worksheet

        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Internal worksheet '{sheet_name}' not found in active sheet for user {user_id}.")
            return None  # Worksheet specifically not found
        except RuntimeError as e:  # Catch auth error
            logger.error(f"Authentication error in get_worksheet for user {user_id}: {e}")
            raise
        except gspread.exceptions.APIError as e:
            logger.error(f"API error getting worksheet '{sheet_name}' for user {user_id}: {e}")
            raise  # Re-raise API errors
        except Exception as e:
            logger.exception(f"Unexpected error getting worksheet '{sheet_name}' for user {user_id}: {e}")
            raise  # Re-raise other unexpected errors
        finally:
            if db:
                db.close()

    def append_row(self, user_id: str, sheet_name: str, values: list[Any]) -> bool:
        """
        Añade una fila de datos al final de una hoja específica en la hoja activa del usuario.

        Args:
            user_id: ID único del usuario
            sheet_name: Nombre de la hoja donde añadir los datos ("gastos" o "ingresos")
            values: Lista de valores a añadir como nueva fila

        Returns:
            True si la operación fue exitosa, False en caso contrario.
        """
        try:
            worksheet = self.get_worksheet(user_id, sheet_name)
            if not worksheet:
                logger.error(f"Could not get worksheet '{sheet_name}' to append row for user {user_id}.")
                return False

            worksheet.append_row(values)
            logger.info(f"Data appended to sheet '{sheet_name}' for user {user_id}: {values}")
            return True
        except Exception as e:
            # Errors are logged within get_worksheet or gspread
            logger.error(f"Failed to append row to sheet '{sheet_name}' for user {user_id}: {e}")
            return False

    # Removed clear_user_data method as it only managed the deleted dictionary.
    # Clearing DB entries should be handled elsewhere if needed (e.g., logout handler).
