"""
Module for managing financial system categories.
"""

from pathlib import Path

import yaml
from loguru import logger


class CategoryManager:
    """
    Category manager for the financial system.

    This class is responsible for loading and providing access to expense
    and income categories defined in a YAML file.
    """

    def __init__(self, config_path: Path | str | None = None):
        """
        Initializes the category manager with a configuration file.

        Args:
            config_path: Path to the categories YAML configuration file.
                         If None, the default path will be used.
        """
        if config_path is None:
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config" / "categories.yaml"

        self.config_path = Path(config_path)
        self._expense_categories: dict[str, list[str]] = {}
        self._income_categories: list[str] = []
        self._load_categories()

    def _load_categories(self) -> None:
        """
        Loads categories from YAML file for system configuration.

        Raises:
            FileNotFoundError: If configuration file is not found.
            yaml.YAMLError: If YAML file has incorrect format.
        """
        try:
            with self.config_path.open("r", encoding="utf-8") as file:
                config = yaml.safe_load(file)

                self._expense_categories = config.get("expense_categories", {})

                self._income_categories = config.get("income_categories", [])

            logger.info(f"Categories successfully loaded from {self.config_path}")
            logger.debug(f"Expense categories: {len(self._expense_categories)}, Income categories: {len(self._income_categories)}")

        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading categories: {e}")
            raise

    @property
    def expense_categories(self) -> dict[str, list[str]]:
        """
        Gets expense categories for transaction categorization.

        Returns:
            Dictionary with expense categories and their subcategories.
        """
        return self._expense_categories

    @property
    def income_categories(self) -> list[str]:
        """
        Gets income categories for transaction categorization.

        Returns:
            List with income categories.
        """
        return self._income_categories

    def get_expense_category_names(self) -> list[str]:
        """
        Gets expense category names for UI display.

        Returns:
            List with expense category names.
        """
        return list(self._expense_categories.keys())

    def get_subcategories(self, category: str) -> list[str]:
        """
        Gets subcategories of an expense category for detailed classification.

        Args:
            category: Main category name.

        Returns:
            List with subcategories of the specified category.
            Empty list if category doesn't exist.
        """
        return self._expense_categories.get(category, [])

    def reload_categories(self) -> None:
        """
        Reloads categories from YAML file for dynamic configuration.

        Useful when the configuration file has been modified.

        Raises:
            Same as _load_categories().
        """
        self._load_categories()


# Global instance of category manager for use throughout the application
category_manager = CategoryManager()
