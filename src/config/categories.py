"""
Módulo para la gestión de categorías del sistema financiero.
"""

from pathlib import Path

import yaml
from loguru import logger


class CategoryManager:
    """
    Gestor de categorías para el sistema financiero.

    Esta clase se encarga de cargar y proporcionar acceso a las categorías
    de gastos e ingresos definidas en un archivo YAML.
    """

    def __init__(self, config_path: Path | str | None = None):
        """
        Inicializa el gestor de categorías.

        Args:
            config_path: Ruta al archivo YAML de configuración de categorías.
                         Si es None, se utilizará la ruta predeterminada.
        """
        if config_path is None:
            # Obtener la ruta absoluta del directorio actual usando Path
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config" / "categories.yaml"

        # Asegurar que config_path sea un objeto Path
        self.config_path = Path(config_path)
        self._expense_categories: dict[str, list[str]] = {}
        self._income_categories: list[str] = []
        self._load_categories()

    def _load_categories(self) -> None:
        """
        Carga las categorías desde el archivo YAML.

        Raises:
            FileNotFoundError: Si no se encuentra el archivo de configuración.
            yaml.YAMLError: Si el archivo YAML tiene un formato incorrecto.
        """
        try:
            with self.config_path.open("r", encoding="utf-8") as file:
                config = yaml.safe_load(file)

                # Cargar categorías de gastos
                self._expense_categories = config.get("expense_categories", {})

                # Cargar categorías de ingresos
                self._income_categories = config.get("income_categories", [])

            logger.info(f"Categorías cargadas correctamente desde {self.config_path}")
            logger.debug(f"Categorías de gastos: {len(self._expense_categories)}, Categorías de ingresos: {len(self._income_categories)}")

        except FileNotFoundError:
            logger.error(f"No se encontró el archivo de configuración: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error al parsear el archivo YAML: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al cargar categorías: {e}")
            raise

    @property
    def expense_categories(self) -> dict[str, list[str]]:
        """
        Obtiene las categorías de gastos.

        Returns:
            Diccionario con las categorías de gastos y sus subcategorías.
        """
        return self._expense_categories

    @property
    def income_categories(self) -> list[str]:
        """
        Obtiene las categorías de ingresos.

        Returns:
            Lista con las categorías de ingresos.
        """
        return self._income_categories

    def get_expense_category_names(self) -> list[str]:
        """
        Obtiene los nombres de las categorías de gastos.

        Returns:
            Lista con los nombres de las categorías de gastos.
        """
        return list(self._expense_categories.keys())

    def get_subcategories(self, category: str) -> list[str]:
        """
        Obtiene las subcategorías de una categoría de gastos.

        Args:
            category: Nombre de la categoría principal.

        Returns:
            Lista con las subcategorías de la categoría especificada.
            Lista vacía si la categoría no existe.
        """
        return self._expense_categories.get(category, [])

    def reload_categories(self) -> None:
        """
        Recarga las categorías desde el archivo YAML.

        Útil cuando se ha modificado el archivo de configuración.

        Raises:
            Mismo que _load_categories().
        """
        self._load_categories()


# Instancia global del gestor de categorías para uso en toda la aplicación
category_manager = CategoryManager()
