"""
Module for managing configuration and environment variables.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger


class Config:
    """
    Manages project configuration and environment variables.
    """

    def __init__(self, env_file: str | Path | None = None) -> None:
        """
        Initializes the configuration from environment sources.

        Args:
            env_file: Path to .env file (optional)
        """
        self._load_env(env_file)

    def _load_env(self, env_file: str | Path | None = None) -> None:
        """
        Loads environment variables from .env file for configuration flexibility.

        Args:
            env_file: Path to .env file (optional)
        """
        if env_file and os.path.exists(env_file):
            load_dotenv(env_file)
            logger.info(f"Environment variables loaded from {env_file}")
        else:
            load_dotenv()
            logger.info("Environment variables loaded (default file)")

    @property
    def telegram_token(self) -> str:
        """
        Gets Telegram token from environment variables for API authentication.

        Returns:
            Telegram token

        Raises:
            ValueError: If token is not found
        """
        token = os.getenv("TELEGRAM_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_TOKEN not found in environment variables")
        return token

    @property
    def oauth_credentials_path(self) -> str:
        """
        Gets the path to OAuth credentials file for Google API access.

        Returns:
            Path to credentials file

        Raises:
            ValueError: If path is not found
        """
        path = os.getenv("OAUTH_CREDENTIALS_PATH")
        if not path:
            raise ValueError("OAUTH_CREDENTIALS_PATH not found in environment variables")
        return path

    @property
    def oauth_tokens_dir(self) -> str:
        """
        Gets directory for storing OAuth tokens for persistent authentication.

        Returns:
            Path to tokens directory
        """
        default_dir = str(Path.cwd() / "tokens")
        return os.getenv("OAUTH_TOKENS_DIR", default_dir)

    @property
    def oauth_server_host(self) -> str:
        """
        Gets host for OAuth server for authentication flow.

        Returns:
            OAuth server host
        """
        return os.getenv("OAUTH_SERVER_HOST", "localhost")

    @property
    def oauth_server_port(self) -> int:
        """
        Gets port for OAuth server for authentication flow.

        Returns:
            OAuth server port
        """
        try:
            return int(os.getenv("OAUTH_SERVER_PORT", "8000"))
        except ValueError:
            logger.warning("Invalid OAuth port in environment variables, using 8000")
            return 8000

    @property
    def oauth_redirect_uri(self) -> str:
        """
        Gets OAuth redirect URI for completing authentication flow.

        If not defined, it's built from host and port.

        Returns:
            Complete redirect URI
        """
        default_uri = f"http://{self.oauth_server_host}:{self.oauth_server_port}/oauth2callback"
        return os.getenv("OAUTH_REDIRECT_URI", default_uri)

    @property
    def oauth_encryption_key(self) -> bytes:
        """
        Gets encryption key for OAuth tokens to ensure secure storage.

        Returns:
            Encryption key as bytes

        Raises:
            ValueError: If key is not found
        """
        key = os.getenv("OAUTH_ENCRYPTION_KEY")
        if not key:
            raise ValueError(
                "OAUTH_ENCRYPTION_KEY not found in environment variables. "
                'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        return key.encode()

    @property
    def database_url(self) -> str:
        """
        Gets database connection URL for data persistence.

        Returns:
            Database connection URL

        Raises:
            ValueError: If URL is not found
        """
        url = os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL not found in environment variables")
        return url
