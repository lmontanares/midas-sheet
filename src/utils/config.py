"""
Módulo para la gestión de configuración y variables de entorno.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger


class Config:
    """
    Gestiona la configuración y variables de entorno del proyecto.
    """

    def __init__(self, env_file: str | Path | None = None) -> None:
        """
        Inicializa la configuración.

        Args:
            env_file: Ruta al archivo .env (opcional)
        """
        self._load_env(env_file)

    def _load_env(self, env_file: str | Path | None = None) -> None:
        """
        Carga variables de entorno desde archivo .env.

        Args:
            env_file: Ruta al archivo .env (opcional)
        """
        if env_file and os.path.exists(env_file):
            load_dotenv(env_file)
            logger.info(f"Variables de entorno cargadas desde {env_file}")
        else:
            load_dotenv()
            logger.info("Variables de entorno cargadas (archivo por defecto)")

    @property
    def telegram_token(self) -> str:
        """
        Obtiene el token de Telegram desde variables de entorno.

        Returns:
            Token de Telegram

        Raises:
            ValueError: Si no se encuentra el token
        """
        token = os.getenv("TELEGRAM_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_TOKEN no encontrado en variables de entorno")
        return token

    @property
    def oauth_credentials_path(self) -> str:
        """
        Obtiene la ruta al archivo de credenciales OAuth.

        Returns:
            Ruta al archivo de credenciales

        Raises:
            ValueError: Si no se encuentra la ruta
        """
        path = os.getenv("OAUTH_CREDENTIALS_PATH")
        if not path:
            raise ValueError("OAUTH_CREDENTIALS_PATH no encontrado en variables de entorno")
        return path

    @property
    def oauth_tokens_dir(self) -> str:
        """
        Obtiene el directorio para almacenar tokens OAuth.

        Returns:
            Ruta al directorio de tokens
        """
        default_dir = str(Path.cwd() / "tokens")
        return os.getenv("OAUTH_TOKENS_DIR", default_dir)

    @property
    def oauth_server_host(self) -> str:
        """
        Obtiene el host para el servidor OAuth.

        Returns:
            Host del servidor OAuth
        """
        return os.getenv("OAUTH_SERVER_HOST", "localhost")

    @property
    def oauth_server_port(self) -> int:
        """
        Obtiene el puerto para el servidor OAuth.

        Returns:
            Puerto del servidor OAuth
        """
        try:
            return int(os.getenv("OAUTH_SERVER_PORT", "8000"))
        except ValueError:
            logger.warning("Puerto OAuth inválido en variables de entorno, usando 8000")
            return 8000

    @property
    def oauth_redirect_uri(self) -> str:
        """
        Obtiene la URI de redirección para OAuth.

        Si no está definida, se construye a partir del host y puerto.

        Returns:
            URI de redirección completa
        """
        default_uri = f"http://{self.oauth_server_host}:{self.oauth_server_port}/oauth2callback"
        return os.getenv("OAUTH_REDIRECT_URI", default_uri)

    @property
    def oauth_encryption_key(self) -> bytes:
        """
        Obtiene la clave de encriptación para los tokens OAuth.

        Returns:
            Clave de encriptación como bytes

        Raises:
            ValueError: Si no se encuentra la clave
        """
        key = os.getenv("OAUTH_ENCRYPTION_KEY")
        if not key:
            raise ValueError(
                "OAUTH_ENCRYPTION_KEY no encontrada en variables de entorno. "
                'Genera una con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        return key.encode()

    @property
    def database_url(self) -> str:
        """
        Obtiene la URL de conexión a la base de datos.

        Returns:
            URL de conexión a la base de datos

        Raises:
            ValueError: Si no se encuentra la URL
        """
        url = os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL no encontrado en variables de entorno")
        return url
