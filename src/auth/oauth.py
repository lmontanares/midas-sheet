import base64
import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests  # Added for revocation
from cryptography.fernet import Fernet, InvalidToken  # Added for encryption
from google.auth.exceptions import RefreshError  # Added for specific exception
from google.auth.transport.requests import Request as GoogleAuthRequest  # Added for refresh
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from loguru import logger


class OAuthManager:
    """
    Manages OAuth 2.0 authentication for Google Sheets, incorporating security best practices.

    Handles:
    - Authorization URL generation with secure state parameter
    - Code exchange for tokens
    - Secure (encrypted) token storage and loading
    - Token refresh
    - Token revocation
    """

    # Use a more specific scope if only spreadsheet access is needed
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    # If drive access is truly needed:
    # SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    # Google's token revocation endpoint
    REVOCATION_ENDPOINT = "https://oauth2.googleapis.com/revoke"

    def __init__(
        self,
        client_secrets_file: str,
        token_dir: str,
        redirect_uri: str,
        encryption_key: bytes,
    ) -> None:
        """
        Initializes the OAuth manager.

        Args:
            client_secrets_file: Path to the OAuth client secrets JSON file.
            token_dir: Directory to store encrypted user tokens.
            redirect_uri: Redirect URI for the OAuth callback.
            encryption_key: Fernet key for encrypting/decrypting tokens.
        """
        self.client_secrets_file = client_secrets_file
        self.token_dir = Path(token_dir)
        self.redirect_uri = redirect_uri
        self.fernet = Fernet(encryption_key)
        self._pending_states: Dict[str, str] = {}  # In-memory state -> user_id mapping

        self.token_dir.mkdir(exist_ok=True, parents=True)

        if not os.path.exists(self.client_secrets_file):
            logger.error(f"OAuth client secrets file not found: {self.client_secrets_file}")
            raise FileNotFoundError(f"OAuth client secrets file not found: {self.client_secrets_file}")

        # Load client secrets once
        try:
            with open(self.client_secrets_file, "r") as f:
                self._client_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load or parse client secrets file {self.client_secrets_file}: {e}")
            raise ValueError(f"Invalid client secrets file: {e}") from e

    def _get_client_id(self) -> str:
        # Helper to safely get client_id
        try:
            return self._client_config["web"]["client_id"]
        except KeyError:
            logger.error("Client ID not found in client secrets file.")
            raise ValueError("Client ID missing in client secrets configuration.")

    def _get_client_secret(self) -> str:
        # Helper to safely get client_secret
        try:
            return self._client_config["web"]["client_secret"]
        except KeyError:
            logger.error("Client secret not found in client secrets file.")
            raise ValueError("Client secret missing in client secrets configuration.")

    def generate_auth_url(self, user_id: str) -> Tuple[str, str]:
        """
        Generates a secure authorization URL for a user.

        Args:
            user_id: Unique ID of the user.

        Returns:
            Tuple containing (authorization_url, state).

        Raises:
            ValueError: If client secrets file is invalid.
            Exception: For other errors during URL generation.
        """
        try:
            flow = Flow.from_client_secrets_file(self.client_secrets_file, scopes=self.SCOPES, redirect_uri=self.redirect_uri)

            # Generate a cryptographically secure state parameter
            state = secrets.token_urlsafe(32)
            self._pending_states[state] = user_id  # Store state -> user_id mapping

            auth_url, _ = flow.authorization_url(
                access_type="offline",  # Request refresh token
                include_granted_scopes="true",
                prompt="consent",  # Force consent screen to ensure refresh token
                state=state,  # Use the secure state
            )

            logger.info(f"Authorization URL generated for user {user_id} with state {state}")
            return auth_url, state

        except FileNotFoundError:
            logger.error(f"Client secrets file not found at {self.client_secrets_file} during auth URL generation.")
            raise
        except Exception as e:
            logger.error(f"Error generating authorization URL for user {user_id}: {e}")
            # Clean up potentially stored state if URL generation failed mid-way
            if "state" in locals() and state in self._pending_states:
                del self._pending_states[state]
            raise

    def exchange_code(self, state: str, code: str) -> Optional[str]:
        """
        Exchanges an authorization code for tokens using the provided state.

        Args:
            state: The state parameter received from the callback.
            code: The authorization code received.

        Returns:
            The user_id associated with the state if successful, None otherwise.

        Raises:
            ValueError: If the state is invalid or not found.
            Exception: For errors during the token exchange process.
        """
        user_id = self._pending_states.pop(state, None)

        if not user_id:
            logger.error(f"Invalid or expired state received: {state}")
            raise ValueError("Invalid or expired OAuth state.")

        try:
            # Create a new flow object for the exchange
            flow = Flow.from_client_secrets_file(self.client_secrets_file, scopes=self.SCOPES, redirect_uri=self.redirect_uri)
            flow.oauth2session.state = state  # Set the state for validation by the library

            # Exchange code for tokens
            flow.fetch_token(code=code)

            credentials = flow.credentials
            token_data = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                # DO NOT store client_secret here
                "scopes": credentials.scopes,
                # Store expiry for potential proactive refresh checks (optional)
                "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            }
            self.save_token(user_id, token_data)

            logger.info(f"Authorization code exchanged successfully for user {user_id}")
            return user_id

        except Exception as e:
            logger.error(f"Error exchanging code for user {user_id} (state: {state}): {e}")
            # State was already popped, no need to clean _pending_states here
            raise

    def get_credentials(self, user_id: str) -> Optional[Credentials]:
        """
        Loads, decrypts, and potentially refreshes credentials for a user.

        Args:
            user_id: Unique ID of the user.

        Returns:
            A valid Credentials object or None if unavailable or refresh fails.
        """
        token_data = self.load_token(user_id)
        if not token_data:
            logger.debug(f"No token found for user {user_id}")
            return None

        try:
            credentials = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                # Client secret is loaded from the secrets file by the library if needed
                client_secret=self._get_client_secret(),
                scopes=token_data.get("scopes"),
            )

            # Check if token needs refreshing
            if credentials.expired and credentials.refresh_token:
                logger.info(f"Token expired for user {user_id}, attempting refresh.")
                try:
                    # Use google.auth.transport.requests for refresh
                    request = GoogleAuthRequest()
                    credentials.refresh(request)
                    logger.info(f"Token refreshed successfully for user {user_id}")

                    # Save the updated token data (including potentially new access token and expiry)
                    refreshed_token_data = {
                        "token": credentials.token,
                        "refresh_token": credentials.refresh_token,  # Usually stays the same
                        "token_uri": credentials.token_uri,
                        "client_id": credentials.client_id,
                        "scopes": credentials.scopes,
                        "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                    }
                    self.save_token(user_id, refreshed_token_data)

                except RefreshError as re:
                    logger.error(f"Failed to refresh token for user {user_id}: {re}")
                    # Token is invalid, revoke and delete
                    self.revoke_token(user_id, token_to_revoke=credentials.refresh_token)  # Revoke refresh token
                    return None
                except Exception as e:
                    logger.error(f"Unexpected error during token refresh for user {user_id}: {e}")
                    # Don't revoke here, might be a temporary network issue
                    return None  # Indicate failure

            # Return valid credentials (original or refreshed)
            if credentials.valid:
                return credentials
            else:
                # This case might happen if the token was invalid but didn't trigger RefreshError
                logger.warning(f"Credentials for user {user_id} are invalid after load/refresh attempt.")
                return None

        except KeyError as ke:
            logger.error(f"Missing key in token data for user {user_id}: {ke}")
            # Corrupted token file, attempt to delete it
            self._delete_token_file(user_id)
            return None
        except Exception as e:
            logger.error(f"Error processing credentials for user {user_id}: {e}")
            return None

    def revoke_token(self, user_id: str, token_to_revoke: Optional[str] = None) -> bool:
        """
        Revokes Google API access for the user and deletes the local token file.

        Args:
            user_id: Unique ID of the user.
            token_to_revoke: Specific token (access or refresh) to revoke. If None, attempts
                             to load the refresh token.

        Returns:
            True if revocation (or cleanup) was successful, False otherwise.
        """
        token_path = self._get_token_path(user_id)
        token_data = self.load_token(user_id)  # Load before deleting

        # Attempt to revoke the token with Google
        token = token_to_revoke or (token_data.get("refresh_token") if token_data else None)

        revocation_success = False
        if token:
            try:
                response = requests.post(
                    self.REVOCATION_ENDPOINT,
                    params={"token": token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10,  # Add a timeout
                )
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

                if response.status_code == 200:
                    logger.info(f"Token successfully revoked with Google for user {user_id}")
                    revocation_success = True
                else:
                    # Log unexpected success status codes? Maybe not necessary.
                    logger.warning(f"Token revocation for user {user_id} returned status {response.status_code}: {response.text}")
                    # Consider it potentially successful if status is 2xx, but log warning
                    revocation_success = 200 <= response.status_code < 300

            except requests.exceptions.RequestException as e:
                logger.error(f"Error during token revocation request for user {user_id}: {e}")
                # Don't block deletion of local file due to network error
            except Exception as e:
                logger.error(f"Unexpected error during token revocation API call for user {user_id}: {e}")

        # Always delete the local token file regardless of revocation API call result
        deleted_local = self._delete_token_file(user_id)

        if deleted_local:
            logger.info(f"Local token file deleted for user {user_id}")
        else:
            # Log if deletion failed, but revocation might have succeeded
            logger.warning(f"Could not delete local token file for user {user_id}, but revocation might have been attempted.")

        # Return True if either Google revocation succeeded or local file was deleted
        return revocation_success or deleted_local

    def _delete_token_file(self, user_id: str) -> bool:
        """Deletes the token file for a user."""
        token_path = self._get_token_path(user_id)
        if token_path.exists():
            try:
                token_path.unlink()
                return True
            except OSError as e:
                logger.error(f"Error deleting token file {token_path} for user {user_id}: {e}")
        return False

    def save_token(self, user_id: str, token_data: Dict[str, Any]) -> None:
        """
        Encrypts and saves token data to a file specific to the user.

        Args:
            user_id: Unique ID of the user.
            token_data: Dictionary containing token information.
        """
        token_path = self._get_token_path(user_id)
        try:
            # Ensure refresh token exists before saving (critical)
            if not token_data.get("refresh_token"):
                logger.warning(f"Attempted to save token for user {user_id} without a refresh token. Aborting save.")
                # Optionally raise an error here if a refresh token is always expected
                # raise ValueError("Cannot save token without a refresh token.")
                return  # Or handle as appropriate

            token_json = json.dumps(token_data).encode("utf-8")
            encrypted_token = self.fernet.encrypt(token_json)

            with open(token_path, "wb") as f:  # Write bytes
                f.write(encrypted_token)
            logger.debug(f"Encrypted token saved for user {user_id} at {token_path}")

        except TypeError as e:
            logger.error(f"Serialization error saving token for user {user_id}: {e}. Data: {token_data}")
            raise
        except IOError as e:
            logger.error(f"I/O error saving token to {token_path} for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving token for user {user_id}: {e}")
            raise

    def load_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads and decrypts token data from a user-specific file.

        Args:
            user_id: Unique ID of the user.

        Returns:
            Dictionary with token data or None if not found or decryption fails.
        """
        token_path = self._get_token_path(user_id)

        if not token_path.exists():
            return None

        try:
            with open(token_path, "rb") as f:  # Read bytes
                encrypted_token = f.read()

            decrypted_token_json = self.fernet.decrypt(encrypted_token)
            token_data = json.loads(decrypted_token_json.decode("utf-8"))
            logger.debug(f"Encrypted token loaded and decrypted for user {user_id}")
            return token_data

        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error reading or parsing token file {token_path} for user {user_id}: {e}")
            # Consider deleting the corrupted file
            # self._delete_token_file(user_id)
            return None
        except InvalidToken:
            logger.error(f"Failed to decrypt token for user {user_id}. Key mismatch or corrupted file: {token_path}")
            # Definitely delete corrupted/unreadable file
            self._delete_token_file(user_id)
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading token for user {user_id}: {e}")
            return None

    def is_authenticated(self, user_id: str) -> bool:
        """
        Checks if a user has valid, non-expired credentials.

        Args:
            user_id: Unique ID of the user.

        Returns:
            True if the user has valid credentials, False otherwise.
        """
        credentials = self.get_credentials(user_id)
        # get_credentials handles refresh, so we just check validity
        return credentials is not None and credentials.valid

    def _get_token_path(self, user_id: str) -> Path:
        """
        Generates a secure path for the user's token file using a hash.

        Args:
            user_id: Unique ID of the user.

        Returns:
            Path object for the token file.
        """
        # Use SHA-256 for a strong, non-reversible hash
        hasher = hashlib.sha256(str(user_id).encode("utf-8"))
        # Use URL-safe base64 encoding for the filename
        safe_filename = base64.urlsafe_b64encode(hasher.digest()).decode("utf-8").rstrip("=")
        return self.token_dir / f"user_{safe_filename}.token"

    # Removed _save_flow_state, _load_flow_state, _clean_flow_state
    # State management is now handled by _pending_states dictionary
