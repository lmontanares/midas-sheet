import threading

import gspread
from google.auth.exceptions import GoogleAuthError  # More specific auth errors
from gspread.exceptions import APIError, SpreadsheetNotFound
from loguru import logger

from ..auth.oauth import OAuthManager


class GoogleSheetsClient:
    """
    Client for interacting with Google Sheets using gspread and secure OAuth 2.0.

    Handles authentication and provides methods for spreadsheet operations.
    Includes basic thread-safety for the client cache.
    """

    # SCOPES defined in OAuthManager, no need to repeat here unless different

    def __init__(self, oauth_manager: OAuthManager) -> None:
        """
        Initializes the Google Sheets client.

        Args:
            oauth_manager: The configured OAuthManager instance.
        """
        self.oauth_manager = oauth_manager
        self.client_cache: dict[str, gspread.Client] = {}
        self._cache_lock = threading.Lock()  # Lock for thread-safe cache access

    def _get_client(self, user_id: str) -> gspread.Client | None:
        """
        Gets an authenticated gspread client for the user, from cache or by authenticating.

        Args:
            user_id: Unique ID of the user.

        Returns:
            An authenticated gspread.Client or None if authentication fails.

        Raises:
            GoogleAuthError: If authentication fails during credential retrieval/refresh.
            APIError: If gspread authorization fails.
            Exception: For other unexpected errors.
        """
        with self._cache_lock:
            if user_id in self.client_cache:
                # TODO: Optionally check if the cached client's credentials are still valid?
                # gspread doesn't expose this easily. Assume valid if cached for now.
                return self.client_cache[user_id]

        # Not in cache, attempt authentication
        try:
            credentials = self.oauth_manager.get_credentials(user_id)
            if not credentials:
                logger.warning(f"Authentication failed: No valid credentials for user {user_id}")
                return None

            # Authorize with gspread
            client = gspread.authorize(credentials)

            # Store in cache
            with self._cache_lock:
                self.client_cache[user_id] = client

            logger.info(f"Successfully authenticated and cached gspread client for user {user_id}")
            return client

        except GoogleAuthError as e:
            logger.error(f"Google authentication error for user {user_id}: {e}")
            self._clear_cache(user_id)  # Clear cache on auth error
            raise  # Re-raise the specific auth error
        except APIError as e:
            logger.error(f"gspread API error during authorization for user {user_id}: {e}")
            self._clear_cache(user_id)
            raise  # Re-raise gspread API error
        except Exception as e:
            logger.exception(f"Unexpected error during authentication for user {user_id}: {e}")
            self._clear_cache(user_id)
            raise  # Re-raise unexpected errors

    def _clear_cache(self, user_id: str) -> None:
        """Removes a user's client from the cache."""
        with self._cache_lock:
            if user_id in self.client_cache:
                del self.client_cache[user_id]
                logger.debug(f"Cleared gspread client cache for user {user_id}")

    def open_spreadsheet(self, user_id: str, spreadsheet_id: str) -> gspread.Spreadsheet | None:
        """
        Opens a spreadsheet by its ID for a specific user.

        Args:
            user_id: Unique ID of the user.
            spreadsheet_id: The ID of the spreadsheet to open.

        Returns:
            gspread.Spreadsheet object or None if not found or auth fails.

        Raises:
            GoogleAuthError: If authentication fails.
            SpreadsheetNotFound: If the spreadsheet ID is invalid or inaccessible.
            APIError: For other Google API errors.
            Exception: For other unexpected errors.
        """
        try:
            client = self._get_client(user_id)
            if not client:
                # Auth failure already logged in _get_client
                return None

            spreadsheet = client.open_by_key(spreadsheet_id)
            logger.info(f"Opened spreadsheet '{spreadsheet.title}' (ID: {spreadsheet_id}) for user {user_id}")
            return spreadsheet

        except SpreadsheetNotFound:
            logger.warning(f"Spreadsheet not found or inaccessible (ID: {spreadsheet_id}) for user {user_id}")
            raise  # Re-raise specific error
        except APIError as e:
            # Handle potential quota errors, permission issues etc.
            logger.error(f"API error opening spreadsheet {spreadsheet_id} for user {user_id}: {e}")
            if "PERMISSION_DENIED" in str(e):
                logger.warning(f"Permission denied for spreadsheet {spreadsheet_id}, user {user_id}.")
                # Consider raising a custom PermissionError?
            raise  # Re-raise APIError
        # GoogleAuthError and other exceptions are raised by _get_client

    def is_authenticated(self, user_id: str) -> bool:
        """
        Checks if the user has valid credentials according to OAuthManager.

        Args:
            user_id: Unique ID of the user.

        Returns:
            True if the user is considered authenticated, False otherwise.
        """
        # Delegate directly to OAuthManager, which handles refresh checks etc.
        return self.oauth_manager.is_authenticated(user_id)

    def clear_user_cache(self, user_id: str) -> None:
        """Explicitly clears the client cache for a specific user (e.g., on logout)."""
        self._clear_cache(user_id)
