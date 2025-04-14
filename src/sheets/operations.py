"""
Operations for manipulating Google Sheets data using gspread with OAuth 2.0.
Interacts with the database to retrieve the user's active spreadsheet.
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
    Provides high-level operations for manipulating Google Sheets data.
    Retrieves the user's active spreadsheet from the database.
    """

    def __init__(self, client: GoogleSheetsClient) -> None:
        """
        Initializes operations with a Google Sheets client for authenticated access.

        Args:
            client: Google Sheets client with OAuth support
        """
        self.client = client

    def _get_active_spreadsheet_id(self, db: Session, user_id: str) -> str | None:
        """Retrieves active spreadsheet ID from database for persistence."""
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
        Verifies spreadsheet access and prepares internal sheets.
        Doesn't store references in memory for statelessness.
        Active sheet is saved in the DB through the /sheet command handler.

        Args:
            user_id: User's unique ID
            spreadsheet_id: Spreadsheet ID to verify and configure

        Returns:
            Spreadsheet title if setup successful, None if failed.

        Raises:
            Exception: If operation fails (propagated from client or ensure_sheets_exist)
        """
        try:
            if not self.client.is_authenticated(user_id):
                logger.warning(f"User {user_id} not authenticated for setup_for_user")
                return None

            spreadsheet = self.client.open_spreadsheet(user_id, spreadsheet_id)
            if not spreadsheet:
                logger.error(f"Failed to open spreadsheet {spreadsheet_id} for user {user_id} during setup.")
                return None

            logger.info(f"Spreadsheet '{spreadsheet.title}' (ID: {spreadsheet_id}) accessed successfully for user {user_id}.")

            self.ensure_sheets_exist(user_id, spreadsheet)

            return spreadsheet.title

        except Exception as e:
            logger.error(f"Error setting up spreadsheet {spreadsheet_id} for user {user_id}: {e}")
            raise

    def ensure_sheets_exist(self, user_id: str, spreadsheet: gspread.Spreadsheet) -> None:
        """
        Ensures required internal sheets exist for data organization.
        Creates them if missing for proper application functioning.

        Args:
            user_id: User's unique ID (for logging)
            spreadsheet: Already opened and verified gspread.Spreadsheet object.

        Raises:
            APIError: If there are issues interacting with the Sheets API.
            Exception: For other unexpected errors.
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
                    spreadsheet.add_worksheet(title=sheet_name, rows=1, cols=len(headers))
                    logger.info(f"Internal sheet '{sheet_name}' created in '{spreadsheet.title}' for user {user_id}. Adding headers...")
                    if not self.append_row(user_id, sheet_name, headers):
                        logger.error(f"Failed to add headers to newly created sheet '{sheet_name}' for user {user_id}")
                else:
                    worksheet = self.get_worksheet(user_id, sheet_name)
                    if worksheet:
                        actual_headers = worksheet.row_values(1)
                        if not actual_headers:
                            logger.info(f"Headers missing in internal sheet '{sheet_name}'. Adding headers...")
                            if not self.append_row(user_id, sheet_name, headers):
                                logger.error(f"Failed to add headers to existing empty sheet '{sheet_name}' for user {user_id}")
                        elif actual_headers != headers:
                            logger.warning(
                                f"Headers in existing internal sheet '{sheet_name}' do not match expected for user {user_id} in '{spreadsheet.title}'. "
                                "Not modifying existing headers."
                            )
                    else:
                        logger.error(f"Failed to retrieve existing worksheet '{sheet_name}' for header check for user {user_id}.")
        except gspread.exceptions.APIError as e:
            logger.error(f"API error ensuring internal sheets exist for user {user_id} in '{spreadsheet.title}': {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error ensuring internal sheets exist for user {user_id} in '{spreadsheet.title}': {e}")
            raise

    def get_worksheet(self, user_id: str, sheet_name: str) -> gspread.Worksheet | None:
        """
        Gets a specific worksheet from the user's active spreadsheet.
        Handles authentication and database lookup for data persistence.

        Args:
            user_id: User's unique ID
            sheet_name: Worksheet name ("gastos" or "ingresos")

        Returns:
            gspread Worksheet object or None if not found or access issues.

        Raises:
            RuntimeError: If user not authenticated.
            APIError: If there are issues with the Sheets API.
            Exception: For other unexpected errors.
        """
        db: Session | None = None
        try:
            if not self.client.is_authenticated(user_id):
                raise RuntimeError(f"User {user_id} is not authenticated.")

            db = SessionLocal()
            spreadsheet_id = self._get_active_spreadsheet_id(db, user_id)
            if not spreadsheet_id:
                return None

            spreadsheet = self.client.open_spreadsheet(user_id, spreadsheet_id)
            if not spreadsheet:
                logger.error(f"Failed to open active spreadsheet {spreadsheet_id} for user {user_id} in get_worksheet.")
                return None

            worksheet = spreadsheet.worksheet(sheet_name)
            logger.debug(f"Retrieved worksheet '{sheet_name}' from spreadsheet '{spreadsheet.title}' for user {user_id}")
            return worksheet

        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Internal worksheet '{sheet_name}' not found in active sheet for user {user_id}.")
            return None
        except RuntimeError as e:
            logger.error(f"Authentication error in get_worksheet for user {user_id}: {e}")
            raise
        except gspread.exceptions.APIError as e:
            logger.error(f"API error getting worksheet '{sheet_name}' for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error getting worksheet '{sheet_name}' for user {user_id}: {e}")
            raise
        finally:
            if db:
                db.close()

    def append_row(self, user_id: str, sheet_name: str, values: list[Any]) -> bool:
        """
        Adds a row of data to record expense or income transactions.

        Args:
            user_id: User's unique ID
            sheet_name: Worksheet name to add data to ("gastos" or "ingresos")
            values: List of values to add as a new row

        Returns:
            True if operation successful, False otherwise.
        """
        try:
            worksheet = self.get_worksheet(user_id, sheet_name)
            if not worksheet:
                logger.error(f"Could not get worksheet '{sheet_name}' to append row for user {user_id}.")
                return False

            worksheet.append_row(values)
            logger.info(f"Data appended to sheet '{sheet_name}' for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to append row to sheet '{sheet_name}' for user {user_id}: {e}")
            return False
