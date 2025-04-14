"""
Module for managing financial system categories.
"""

import datetime
import json
from pathlib import Path

import yaml
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.database import UserCategories


class CategoryManager:
    """
    Category manager for the financial system.

    This class manages expense and income categories, supporting both
    global defaults and user-specific customizations.
    """

    def __init__(self, config_path: Path | str | None = None):
        """
        Initializes the category manager with a configuration file.

        Args:
            config_path: Path to the default categories YAML configuration file.
                         If None, the default path will be used.
        """
        if config_path is None:
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config" / "categories.yaml"

        self.config_path = Path(config_path)
        self._default_expense_categories: dict[str, list[str]] = {}
        self._default_income_categories: list[str] = []
        self._user_categories: dict[str, dict] = {}
        self._load_default_categories()

    def _load_default_categories(self) -> None:
        """
        Loads default categories from YAML file for system configuration.

        Raises:
            FileNotFoundError: If configuration file is not found.
            yaml.YAMLError: If YAML file has incorrect format.
        """
        try:
            with self.config_path.open("r", encoding="utf-8") as file:
                config = yaml.safe_load(file)

                self._default_expense_categories = config.get("expense_categories", {})
                self._default_income_categories = config.get("income_categories", [])

            logger.info(f"Default categories successfully loaded from {self.config_path}")
            logger.debug(
                f"Default expense categories: {len(self._default_expense_categories)}, Default income categories: {len(self._default_income_categories)}"
            )

        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading default categories: {e}")
            raise

    def load_user_categories(self, user_id: str, db_session: Session) -> None:
        """
        Loads user-specific categories from database, falls back to defaults if not found.

        Args:
            user_id: The user's unique identifier
            db_session: SQLAlchemy database session
        """
        try:
            # Query user categories from the database
            stmt = select(UserCategories).where(UserCategories.user_id == user_id)
            user_categories = db_session.scalars(stmt).first()

            if user_categories:
                categories_dict = json.loads(user_categories.categories_json)
                self._user_categories[user_id] = categories_dict
                logger.info(f"Loaded custom categories for user {user_id}")
            else:
                self._user_categories[user_id] = {
                    "expense_categories": self._default_expense_categories,
                    "income_categories": self._default_income_categories,
                }
                logger.info(f"Using default categories for user {user_id}")

        except Exception as e:
            logger.error(f"Error loading categories for user {user_id}: {e}")
            self._user_categories[user_id] = {
                "expense_categories": self._default_expense_categories,
                "income_categories": self._default_income_categories,
            }

    def save_user_categories(self, user_id: str, expense_categories: dict[str, list[str]], income_categories: list[str], db_session: Session) -> bool:
        """
        Saves user-specific categories to the database.

        Args:
            user_id: The user's unique identifier
            expense_categories: Dictionary of expense categories and subcategories
            income_categories: List of income categories
            db_session: SQLAlchemy database session

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            categories_dict = {"expense_categories": expense_categories, "income_categories": income_categories}

            categories_json = json.dumps(categories_dict, ensure_ascii=False)

            stmt = select(UserCategories).where(UserCategories.user_id == user_id)
            existing = db_session.scalars(stmt).first()

            if existing:
                existing.categories_json = categories_json
                existing.updated_at = datetime.datetime.now()
            else:
                new_categories = UserCategories(user_id=user_id, categories_json=categories_json)
                db_session.add(new_categories)

            db_session.commit()

            self._user_categories[user_id] = categories_dict

            logger.info(f"Categories saved successfully for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving categories for user {user_id}: {e}")
            db_session.rollback()
            return False

    def get_expense_categories(self, user_id: str) -> dict[str, list[str]]:
        """
        Gets expense categories for a specific user.

        Args:
            user_id: The user's unique identifier

        Returns:
            Dictionary with expense categories and their subcategories
        """
        if user_id in self._user_categories:
            return self._user_categories[user_id]["expense_categories"]
        return self._default_expense_categories

    def get_income_categories(self, user_id: str) -> list[str]:
        """
        Gets income categories for a specific user.

        Args:
            user_id: The user's unique identifier

        Returns:
            List with income categories
        """
        if user_id in self._user_categories:
            return self._user_categories[user_id]["income_categories"]
        return self._default_income_categories

    @property
    def expense_categories(self) -> dict[str, list[str]]:
        """
        Gets default expense categories (for backward compatibility).

        Returns:
            Dictionary with expense categories and their subcategories.
        """
        return self._default_expense_categories

    @property
    def income_categories(self) -> list[str]:
        """
        Gets default income categories (for backward compatibility).

        Returns:
            List with income categories.
        """
        return self._default_income_categories

    def get_expense_category_names(self, user_id: str = None) -> list[str]:
        """
        Gets expense category names for UI display.

        Args:
            user_id: The user's unique identifier (optional)

        Returns:
            List with expense category names.
        """
        if user_id and user_id in self._user_categories:
            return list(self._user_categories[user_id]["expense_categories"].keys())
        return list(self._default_expense_categories.keys())

    def get_subcategories(self, category: str, user_id: str = None) -> list[str]:
        """
        Gets subcategories of an expense category for detailed classification.

        Args:
            category: Main category name.
            user_id: The user's unique identifier (optional)

        Returns:
            List with subcategories of the specified category.
            Empty list if category doesn't exist.
        """
        if user_id and user_id in self._user_categories:
            return self._user_categories[user_id]["expense_categories"].get(category, [])
        return self._default_expense_categories.get(category, [])

    def reset_user_categories(self, user_id: str, db_session: Session) -> bool:
        """
        Resets a user's categories to system defaults.

        Args:
            user_id: The user's unique identifier
            db_session: SQLAlchemy database session

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete custom categories from the database
            stmt = select(UserCategories).where(UserCategories.user_id == user_id)
            existing = db_session.scalars(stmt).first()

            if existing:
                db_session.delete(existing)
                db_session.commit()

            # Update the in-memory cache
            if user_id in self._user_categories:
                del self._user_categories[user_id]

            logger.info(f"Categories reset to defaults for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error resetting categories for user {user_id}: {e}")
            db_session.rollback()
            return False


# Global instance of category manager for use throughout the application
category_manager = CategoryManager()
