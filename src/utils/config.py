"""
Módulo para la gestión de configuración y variables de entorno.
"""
import os
from loguru import logger
from pathlib import Path
from dotenv import load_dotenv

# El logger ya está importado de loguru

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
    def google_credentials_path(self) -> str:
        """
        Obtiene la ruta al archivo de credenciales de Google.
        
        Returns:
            Ruta al archivo de credenciales
            
        Raises:
            ValueError: Si no se encuentra la ruta
        """
        path = os.getenv("GOOGLE_CREDENTIALS_PATH")
        if not path:
            raise ValueError("GOOGLE_CREDENTIALS_PATH no encontrado en variables de entorno")
        return path
    
    @property
    def spreadsheet_id(self) -> str:
        """
        Obtiene el ID de la hoja de cálculo.
        
        Returns:
            ID de la hoja de cálculo
            
        Raises:
            ValueError: Si no se encuentra el ID
        """
        id = os.getenv("SPREADSHEET_ID")
        if not id:
            raise ValueError("SPREADSHEET_ID no encontrado en variables de entorno")
        return id
