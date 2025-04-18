"""
Operations for manipulating Google Sheets data using gspread with OAuth 2.0.
Interacts with the database to retrieve the user's active spreadsheet.
"""

from typing import Any

import gspread
from gspread.exceptions import APIError, WorksheetNotFound
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.database import SessionLocal, UserSheet
from .client import GoogleSheetsClient


class MissingHeadersError(Exception):
    """Raised when the sheet headers do not match the expected headers."""

    def __init__(self, sheet_name: str, expected: list[str], actual: list[str] | None) -> None:
        self.sheet_name = sheet_name
        self.expected = expected
        self.actual = actual if actual else []
        message = f"Header mismatch in sheet '{sheet_name}'. Expected: {expected}, Found: {self.actual}"
        super().__init__(message)


class SheetsOperations:
    """
    Provides high-level operations for manipulating Google Sheets data.
    Retrieves the user's active spreadsheet from the database.
    """

    # Define expected headers as a class attribute
    REQUIRED_SHEETS = {
        "gastos": ["Fecha", "Usuario", "Categoría", "Subcategoría", "Monto", "Timestamp", "Comentario"],
        "ingresos": ["Fecha", "Usuario", "Categoría", "Monto", "Timestamp", "Comentario"],
    }

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

        required_sheets = self.REQUIRED_SHEETS
        try:
            existing_sheets = [ws.title for ws in spreadsheet.worksheets()]

            for sheet_name, headers in required_sheets.items():
                if sheet_name not in existing_sheets:
                    # Create the worksheet if it doesn't exist
                    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1, cols=len(headers))
                    logger.info(f"Internal sheet '{sheet_name}' created in '{spreadsheet.title}' for user {user_id}. Adding headers...")
                    # Use the append_row method with the spreadsheet parameter
                    if not self.append_row(user_id, sheet_name, headers, spreadsheet=spreadsheet):
                        logger.error(f"Failed to add headers to newly created sheet '{sheet_name}' for user {user_id}")
                else:
                    # Get the worksheet directly from the spreadsheet object
                    try:
                        worksheet = spreadsheet.worksheet(sheet_name)
                        actual_headers = worksheet.row_values(1)
                        if not actual_headers:
                            logger.info(f"Headers missing in internal sheet '{sheet_name}'. Adding headers...")
                            # Use the append_row method with the spreadsheet parameter
                            if not self.append_row(user_id, sheet_name, headers, spreadsheet=spreadsheet):
                                logger.error(f"Failed to add headers to existing empty sheet '{sheet_name}' for user {user_id}")
                        elif actual_headers != headers:
                            logger.warning(
                                f"Headers in existing internal sheet '{sheet_name}' do not match expected for user {user_id} in '{spreadsheet.title}'. "
                                "Not modifying existing headers."
                            )
                    except Exception as e:
                        logger.error(f"Failed to retrieve existing worksheet '{sheet_name}' for header check for user {user_id}: {e}")
        except APIError as e:
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

        except WorksheetNotFound:
            logger.error(f"Internal worksheet '{sheet_name}' not found in active sheet for user {user_id}.")
            return None
        except RuntimeError as e:
            logger.error(f"Authentication error in get_worksheet for user {user_id}: {e}")
            raise
        except APIError as e:
            logger.error(f"API error getting worksheet '{sheet_name}' for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error getting worksheet '{sheet_name}' for user {user_id}: {e}")
            raise
        finally:
            if db:
                db.close()

    def append_row(self, user_id: str, sheet_name: str, values: list[Any], spreadsheet: gspread.Spreadsheet | None = None) -> bool:
        """
        Adds a row of data after validating sheet headers.

        Args:
            user_id: User's unique ID
            sheet_name: Worksheet name ("gastos" or "ingresos")
            values: List of values for the new row
            spreadsheet: Optional spreadsheet object to use directly instead of retrieving from DB

        Returns:
            bool: True if append was successful, False otherwise

        Raises:
            MissingHeadersError: If sheet headers don't match expected headers.
            RuntimeError: If user not authenticated.
            APIError: If there are issues with the Sheets API.
            WorksheetNotFound: If the target sheet doesn't exist.
            Exception: For other unexpected errors during worksheet access or append.
        """
        worksheet = None
        try:
            if spreadsheet:
                # Use the provided spreadsheet directly
                try:
                    worksheet = spreadsheet.worksheet(sheet_name)
                    logger.debug(f"Using provided spreadsheet to access worksheet '{sheet_name}' for user {user_id}")
                except WorksheetNotFound:
                    logger.error(f"Worksheet '{sheet_name}' not found in provided spreadsheet for user {user_id}")
                    return False
            else:
                # Get worksheet from the active spreadsheet in the database
                worksheet = self.get_worksheet(user_id, sheet_name)

            if not worksheet:
                raise WorksheetNotFound(f"Worksheet '{sheet_name}' not found for user {user_id}.")

            expected_headers = self.REQUIRED_SHEETS.get(sheet_name)
            if not expected_headers:
                raise ValueError(f"No expected headers defined for sheet name: {sheet_name}")

            try:
                actual_headers = worksheet.row_values(1)
            except APIError as api_err:
                logger.error(f"API error fetching headers for sheet '{sheet_name}', user {user_id}: {api_err}")
                raise
            except Exception as head_err:
                logger.error(f"Error fetching headers for sheet '{sheet_name}', user {user_id}: {head_err}")
                raise MissingHeadersError(sheet_name, expected_headers, None) from head_err

            # Special case: If we're trying to add headers to an empty sheet, allow it
            if not actual_headers and values == expected_headers:
                logger.info(f"Adding headers to empty sheet '{sheet_name}' for user {user_id}")
            elif not actual_headers or actual_headers != expected_headers:
                logger.warning(
                    f"Header mismatch for user {user_id} in sheet '{sheet_name}'. "
                    f"Expected: {expected_headers}, Found: {actual_headers}. Aborting append."
                )
                raise MissingHeadersError(sheet_name, expected_headers, actual_headers)

            worksheet.append_row(values)
            logger.info(f"Data appended to sheet '{sheet_name}' for user {user_id} after header validation.")
            return True

        except MissingHeadersError:
            raise
        except (RuntimeError, APIError, WorksheetNotFound) as e:
            logger.error(f"Error during append operation for user {user_id}, sheet '{sheet_name}': {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error appending row to sheet '{sheet_name}' for user {user_id}: {e}")
            raise

        return False  # This line should never be reached, but ensures consistent return type
