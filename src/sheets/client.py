import threading

import gspread
from google.auth.exceptions import GoogleAuthError
from gspread.exceptions import APIError, SpreadsheetNotFound
from loguru import logger

from ..auth.oauth import OAuthManager


class GoogleSheetsClient:
    """
    Client for interacting with Google Sheets using gspread and secure OAuth 2.0.

    Handles authentication and provides methods for spreadsheet operations.
    Includes basic thread-safety for the client cache.
    """

    def __init__(self, oauth_manager: OAuthManager) -> None:
        """
        Initializes the Google Sheets client with OAuth manager for secure API access.

        Args:
            oauth_manager: The configured OAuthManager instance.
        """
        self.oauth_manager = oauth_manager
        self.client_cache: dict[str, gspread.Client] = {}
        self._cache_lock = threading.Lock()  # Lock for thread-safe cache access

    def _get_client(self, user_id: str) -> gspread.Client | None:
        """
        Gets an authenticated gspread client from cache or creates a new one for efficiency.
        Always ensures the client has valid, non-expired credentials.

        Args:
            user_id: Unique ID of the user.

        Returns:
            An authenticated gspread.Client or None if authentication fails.

        Raises:
            GoogleAuthError: If authentication fails during credential retrieval/refresh.
            APIError: If gspread authorization fails.
            Exception: For other unexpected errors.
        """
        create_new_client = False
        
        # Check if we already have a cached client
        with self._cache_lock:
            if user_id in self.client_cache:
                logger.debug(f"Found cached client for user {user_id}, checking if token is valid")
                try:
                    # Test the cached client with a simple API call
                    # This will trigger a token refresh if needed
                    client = self.client_cache[user_id]
                    
                    # We want to force a refresh, so bypass any cached client
                    # and always get fresh credentials
                    create_new_client = True
                except Exception as e:
                    logger.warning(f"Cached client for user {user_id} failed test: {e}")
                    create_new_client = True
            else:
                create_new_client = True

        if create_new_client:
            try:
                # Always get fresh credentials from the oauth manager
                # This will refresh the token if it's expired
                credentials = self.oauth_manager.get_credentials(user_id)
                
                if not credentials:
                    logger.warning(f"Authentication failed: No valid credentials for user {user_id}")
                    self._clear_cache(user_id)
                    return None

                # Create a new client with the fresh credentials
                client = gspread.authorize(credentials)

                # Cache the new client
                with self._cache_lock:
                    self.client_cache[user_id] = client

                logger.info(f"Successfully authenticated and cached new gspread client for user {user_id}")
                return client

            except GoogleAuthError as e:
                logger.error(f"Google authentication error for user {user_id}: {e}")
                self._clear_cache(user_id)
                
                # If it's a refresh error, we should clear the token from the database
                if "invalid_grant" in str(e).lower() or "token has been expired or revoked" in str(e).lower():
                    logger.warning(f"Token appears to be revoked or expired for user {user_id}, attempting to clear token")
                    try:
                        self.oauth_manager.revoke_token(user_id)
                    except Exception as revoke_error:
                        logger.error(f"Failed to revoke invalid token for user {user_id}: {revoke_error}")
                
                raise
                
            except APIError as e:
                logger.error(f"gspread API error during authorization for user {user_id}: {e}")
                
                # If it's related to auth, clear the cache
                if "invalid_grant" in str(e).lower() or "unauthorized" in str(e).lower():
                    self._clear_cache(user_id)
                
                raise
                
            except Exception as e:
                logger.exception(f"Unexpected error during authentication for user {user_id}: {e}")
                self._clear_cache(user_id)
                raise
        
        return client

    def _clear_cache(self, user_id: str) -> None:
        """Removes a user's client from the cache to prevent stale authentication."""
        with self._cache_lock:
            if user_id in self.client_cache:
                del self.client_cache[user_id]
                logger.debug(f"Cleared gspread client cache for user {user_id}")

    def open_spreadsheet(self, user_id: str, spreadsheet_id: str) -> gspread.Spreadsheet | None:
        """
        Opens a spreadsheet by its ID for validated user access control.
        Handles token refresh and authentication issues.

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
            # Always get a fresh client to ensure we have up-to-date credentials
            client = self._get_client(user_id)
            if not client:
                logger.warning(f"Could not get authenticated client for user {user_id}")
                return None

            # Try to open the spreadsheet
            spreadsheet = client.open_by_key(spreadsheet_id)
            logger.info(f"Opened spreadsheet '{spreadsheet.title}' (ID: {spreadsheet_id}) for user {user_id}")
            return spreadsheet

        except GoogleAuthError as e:
            # Handle authentication errors
            logger.error(f"Authentication error opening spreadsheet for user {user_id}: {e}")
            
            # Clear the client cache to force re-authentication on next attempt
            self._clear_cache(user_id)
            
            # If it's a token issue, attempt to revoke and clear the token
            if "invalid_grant" in str(e).lower() or "token has been expired or revoked" in str(e).lower():
                try:
                    logger.warning(f"Token expired for user {user_id}, attempting to revoke/clear token")
                    self.oauth_manager.revoke_token(user_id)
                except Exception as revoke_error:
                    logger.error(f"Failed to revoke token for user {user_id}: {revoke_error}")
            
            raise
            
        except SpreadsheetNotFound:
            logger.warning(f"Spreadsheet not found or inaccessible (ID: {spreadsheet_id}) for user {user_id}")
            raise
            
        except APIError as e:
            # Handle API errors
            logger.error(f"API error opening spreadsheet {spreadsheet_id} for user {user_id}: {e}")
            
            if "PERMISSION_DENIED" in str(e):
                logger.warning(f"Permission denied for spreadsheet {spreadsheet_id}, user {user_id}.")
            
            # Handle authentication-related API errors
            if "invalid_grant" in str(e).lower() or "unauthorized" in str(e).lower():
                logger.warning(f"Authentication-related API error for user {user_id}, clearing cache")
                self._clear_cache(user_id)
                
                # Try to clear the token if it appears to be an auth issue
                try:
                    self.oauth_manager.revoke_token(user_id)
                except Exception as revoke_error:
                    logger.error(f"Failed to revoke token after API error for user {user_id}: {revoke_error}")
            
            raise
            
        except Exception as e:
            logger.exception(f"Unexpected error opening spreadsheet {spreadsheet_id} for user {user_id}: {e}")
            self._clear_cache(user_id)
            raise

    def is_authenticated(self, user_id: str) -> bool:
        """
        Checks authentication status to prevent unauthorized operations.
        Tries to ensure the token is still valid by getting fresh credentials.

        Args:
            user_id: Unique ID of the user.

        Returns:
            True if the user is authenticated with valid credentials, False otherwise.
        """
        try:
            # For a thorough check, try to get a client
            # This will refresh the token if needed
            client = self._get_client(user_id)
            return client is not None
        except Exception as e:
            logger.warning(f"Error checking authentication status for user {user_id}: {e}")
            return False

    def clear_user_cache(self, user_id: str) -> None:
        """Explicitly clears the client cache for logout or token revocation."""
        self._clear_cache(user_id)
