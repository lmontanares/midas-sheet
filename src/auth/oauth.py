import datetime
import json
import os
import secrets
from typing import Any, Dict, Optional, Tuple

import requests
from cryptography.fernet import Fernet, InvalidToken
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# Assuming database.py is in the parent directory relative to this file's location in src/auth
# Adjust the import path if necessary based on your final project structure
from ..db.database import AuthToken, SessionLocal, User


class OAuthManager:
    """
    Manages OAuth 2.0 authentication for Google Sheets using a database backend.

    Handles:
    - Authorization URL generation with secure state parameter
    - Code exchange for tokens
    - Secure (encrypted) token storage and loading in the database
    - Token refresh
    - Token revocation
    """

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    REVOCATION_ENDPOINT = "https://oauth2.googleapis.com/revoke"

    def __init__(
        self,
        client_secrets_file: str,
        redirect_uri: str,
        encryption_key: bytes,
    ) -> None:
        """
        Initializes the OAuth manager.

        Args:
            client_secrets_file: Path to the OAuth client secrets JSON file.
            redirect_uri: Redirect URI for the OAuth callback.
            encryption_key: Fernet key for encrypting/decrypting tokens.
        """
        self.client_secrets_file = client_secrets_file
        self.redirect_uri = redirect_uri
        self.fernet = Fernet(encryption_key)
        self._pending_states: Dict[str, str] = {}

        if not os.path.exists(self.client_secrets_file):
            logger.error(f"OAuth client secrets file not found: {self.client_secrets_file}")
            raise FileNotFoundError(f"OAuth client secrets file not found: {self.client_secrets_file}")

        try:
            with open(self.client_secrets_file, "r") as f:
                self._client_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load or parse client secrets file {self.client_secrets_file}: {e}")
            raise ValueError(f"Invalid client secrets file: {e}") from e

    def _get_client_id(self) -> str:
        try:
            return self._client_config["web"]["client_id"]
        except KeyError:
            logger.error("Client ID not found in client secrets file.")
            raise ValueError("Client ID missing in client secrets configuration.")

    def _get_client_secret(self) -> str:
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
            self._pending_states[state] = user_id

            auth_url, _ = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",
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

    def _upsert_user(self, db: Session, user_id: str) -> None:
        """Creates or updates a user entry in the database."""
        try:
            stmt = select(User).where(User.user_id == user_id)
            existing_user = db.scalars(stmt).first()

            if existing_user:
                # Optionally update fields like updated_at if needed, but not strictly necessary here
                logger.debug(f"User {user_id} already exists in the database.")
            else:
                logger.info(f"User {user_id} not found, creating new entry.")
                new_user = User(user_id=user_id)  # Add other fields if available
                db.add(new_user)
                db.flush()  # Flush to ensure user exists before token insertion
                logger.info(f"User {user_id} created successfully.")
        except Exception as e:
            logger.error(f"Error upserting user {user_id}: {e}")
            db.rollback()  # Rollback on error during user upsert
            raise  # Re-raise the exception to be caught by the caller

    def exchange_code(self, state: str, code: str) -> Optional[str]:
        """
        Exchanges an authorization code for tokens using the provided state.
        Ensures the user exists in the DB before saving the token.

        Args:
            state: The state parameter received from the callback.
            code: The authorization code received.

        Returns:
            The user_id associated with the state if successful, None otherwise.

        Raises:
            ValueError: If the state is invalid or not found.
            Exception: For errors during the token exchange process or DB operations.
        """
        user_id = self._pending_states.pop(state, None)

        if not user_id:
            logger.error(f"Invalid or expired state received: {state}")
            raise ValueError("Invalid or expired OAuth state.")

        db: Session | None = None
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

            # --- Database Interaction ---
            db = SessionLocal()
            self._upsert_user(db, user_id)  # Ensure user exists before saving token
            self.save_token(user_id, token_data, db_session=db)  # Pass the existing session
            db.commit()  # Commit both user upsert and token save
            # --- End Database Interaction ---

            logger.info(f"Authorization code exchanged successfully for user {user_id}")
            return user_id

        except Exception as e:
            logger.error(f"Error exchanging code for user {user_id} (state: {state}): {e}")
            if db:
                db.rollback()  # Rollback any DB changes if exchange fails
            # State was already popped, no need to clean _pending_states here
            raise
        finally:
            if db:
                db.close()

    def get_credentials(self, user_id: str) -> Optional[Credentials]:
        """
        Loads, decrypts, and potentially refreshes credentials for a user from the database.

        Args:
            user_id: Unique ID of the user.

        Returns:
            A valid Credentials object or None if unavailable or refresh fails.
        """
        token_data = self.load_token(user_id)
        if not token_data:
            logger.debug(f"No token found in database for user {user_id}")
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
                    self.save_token(user_id, refreshed_token_data)  # Save updated token to DB

                except RefreshError as re:
                    logger.error(f"Failed to refresh token for user {user_id}: {re}")
                    # Token is invalid, revoke and delete from DB
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
            logger.error(f"Missing key in token data loaded from DB for user {user_id}: {ke}")
            # Corrupted data in DB? Log error. Deletion might be too aggressive here.
            return None
        except Exception as e:
            logger.error(f"Error processing credentials for user {user_id}: {e}")
            return None

    def revoke_token(self, user_id: str, token_to_revoke: Optional[str] = None) -> bool:
        """
        Revokes Google API access for the user and deletes the token from the database.

        Args:
            user_id: Unique ID of the user.
            token_to_revoke: Specific token (access or refresh) to revoke. If None, attempts
                             to load the refresh token from the database.

        Returns:
            True if revocation (or cleanup) was successful, False otherwise.
        """
        db: Session | None = None
        token_data = None
        if not token_to_revoke:
            token_data = self.load_token(user_id)  # Load to get refresh token if needed

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
                    logger.warning(f"Token revocation for user {user_id} returned status {response.status_code}: {response.text}")
                    revocation_success = 200 <= response.status_code < 300

            except requests.exceptions.RequestException as e:
                logger.error(f"Error during token revocation request for user {user_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during token revocation API call for user {user_id}: {e}")

        # Always attempt to delete the local token from the database
        deleted_local = False
        try:
            db = SessionLocal()
            stmt = delete(AuthToken).where(AuthToken.user_id == user_id)
            result = db.execute(stmt)
            db.commit()
            if result.rowcount > 0:
                deleted_local = True
                logger.info(f"Local token deleted from database for user {user_id}")
            else:
                logger.warning(f"No local token found in database to delete for user {user_id}.")
                # If revocation succeeded but no local token found, still consider it a success overall
                deleted_local = revocation_success

        except Exception as e:
            logger.error(f"Error deleting token from database for user {user_id}: {e}")
            if db:
                db.rollback()
        finally:
            if db:
                db.close()

        if not deleted_local and not revocation_success:
            logger.warning(f"Token revocation failed both with Google and locally for user {user_id}.")
        elif not deleted_local:
            logger.warning(f"Could not delete local token for user {user_id}, but Google revocation might have succeeded.")

        # Return True if either Google revocation succeeded or local DB deletion succeeded
        return revocation_success or deleted_local

    # Removed _delete_token_file method

    def save_token(self, user_id: str, token_data: Dict[str, Any], db_session: Optional[Session] = None) -> None:
        """
        Encrypts and saves token data to the database for the user.
        Can use an existing session or create a new one.

        Args:
            user_id: Unique ID of the user.
            token_data: Dictionary containing token information.
            db_session: Optional existing SQLAlchemy session to use.
        """
        db: Session | None = None
        try:
            # Ensure refresh token exists before saving (critical)
            if not token_data.get("refresh_token"):
                logger.warning(f"Attempted to save token for user {user_id} without a refresh token. Aborting save.")
                return

            token_json = json.dumps(token_data).encode("utf-8")
            encrypted_token_bytes = self.fernet.encrypt(token_json)

            # Extract expiry and convert to datetime object if present
            expiry_iso = token_data.get("expiry")
            token_expiry_dt: Optional[datetime.datetime] = None
            if expiry_iso:
                try:
                    # Handle potential timezone info (e.g., 'Z' or +HH:MM) if present
                    if expiry_iso.endswith("Z"):
                        expiry_iso = expiry_iso[:-1] + "+00:00"
                    token_expiry_dt = datetime.datetime.fromisoformat(expiry_iso)
                except ValueError:
                    logger.warning(f"Could not parse expiry date '{expiry_iso}' for user {user_id}. Storing as None.")

            # Use provided session or create a new one
            if db_session:
                db = db_session
                manage_session = False  # Don't commit/close if session is managed externally
            else:
                db = SessionLocal()
                manage_session = True

            # Check if token exists
            existing_token = db.get(AuthToken, user_id)

            if existing_token:
                # Update existing token
                existing_token.encrypted_token = encrypted_token_bytes
                existing_token.token_expiry = token_expiry_dt
                # updated_at is handled by onupdate=func.now()
                logger.debug(f"Updating existing token in database for user {user_id}")
            else:
                # Insert new token
                new_token = AuthToken(
                    user_id=user_id,
                    encrypted_token=encrypted_token_bytes,
                    token_expiry=token_expiry_dt,
                )
                db.add(new_token)
                logger.debug(f"Inserting new token into database for user {user_id}")

            if manage_session:
                db.commit()
            else:
                db.flush()  # Flush to ensure data is ready if session is managed externally

            logger.info(f"Encrypted token saved to database for user {user_id}")

        except IntegrityError as ie:
            # Should be rare if _upsert_user is called first in exchange_code
            logger.error(f"Database integrity error saving token for user {user_id}: {ie}")
            if manage_session and db:
                db.rollback()
            raise
        except TypeError as e:
            logger.error(f"Serialization error saving token for user {user_id}: {e}. Data: {token_data}")
            if manage_session and db:
                db.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving token to database for user {user_id}: {e}")
            if manage_session and db:
                db.rollback()
            raise
        finally:
            if manage_session and db:
                db.close()

    def load_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads and decrypts token data from the database for a user.

        Args:
            user_id: Unique ID of the user.

        Returns:
            Dictionary with token data or None if not found or decryption fails.
        """
        db: Session | None = None
        try:
            db = SessionLocal()
            token_record = db.get(AuthToken, user_id)

            if not token_record:
                return None

            decrypted_token_json = self.fernet.decrypt(token_record.encrypted_token)
            token_data = json.loads(decrypted_token_json.decode("utf-8"))
            logger.debug(f"Encrypted token loaded and decrypted from database for user {user_id}")
            return token_data

        except InvalidToken:
            logger.error(f"Failed to decrypt token for user {user_id}. Key mismatch or corrupted data in database.")
            # Delete the corrupted/unreadable token from the DB
            self._delete_invalid_token_entry(user_id)
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing decrypted token JSON for user {user_id}: {e}")
            # Consider deleting corrupted entry?
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading token from database for user {user_id}: {e}")
            return None
        finally:
            if db:
                db.close()

    def _delete_invalid_token_entry(self, user_id: str) -> None:
        """Deletes a specific token entry from the database, usually due to corruption."""
        db: Session | None = None
        try:
            db = SessionLocal()
            stmt = delete(AuthToken).where(AuthToken.user_id == user_id)
            db.execute(stmt)
            db.commit()
            logger.warning(f"Deleted potentially corrupted token entry from database for user {user_id}.")
        except Exception as e:
            logger.error(f"Failed to delete invalid token entry for user {user_id}: {e}")
            if db:
                db.rollback()
        finally:
            if db:
                db.close()

    def is_authenticated(self, user_id: str) -> bool:
        """
        Checks if a user has valid, non-expired credentials stored in the database.

        Args:
            user_id: Unique ID of the user.

        Returns:
            True if the user has valid credentials, False otherwise.
        """
        credentials = self.get_credentials(user_id)
        # get_credentials handles refresh, so we just check validity
        return credentials is not None and credentials.valid

    # Removed _get_token_path method
