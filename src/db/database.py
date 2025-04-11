"""
Database module for SQLAlchemy setup, models, and session management.
"""

import datetime

from loguru import logger
from sqlalchemy import (
    BLOB,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.sql import func

from ..utils.config import Config

# Load database URL from config
try:
    config = Config()
    DATABASE_URL = config.database_url
except ValueError as e:
    logger.error(f"Database configuration error: {e}")
    # Fallback or raise an error if DB is critical
    DATABASE_URL = "sqlite:///./finanzas_fallback.db"  # Example fallback
    logger.warning(f"Using fallback database URL: {DATABASE_URL}")


# SQLAlchemy engine setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base class for models
class Base(DeclarativeBase):
    pass


# --- SQLAlchemy Models ---


class User(Base):
    """SQLAlchemy model for users."""

    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<User(user_id='{self.user_id}', username='{self.telegram_username}')>"


class AuthToken(Base):
    """SQLAlchemy model for storing encrypted OAuth tokens."""

    __tablename__ = "auth_tokens"

    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"), primary_key=True)
    # Use BLOB for encrypted data, TEXT might work for Base64 but BLOB is safer
    encrypted_token: Mapped[bytes] = mapped_column(BLOB, nullable=False)
    token_expiry: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<AuthToken(user_id='{self.user_id}')>"


class UserSheet(Base):
    """SQLAlchemy model for associating users with their Google Sheets."""

    __tablename__ = "user_sheets"

    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"), primary_key=True)
    spreadsheet_id: Mapped[str] = mapped_column(Text, nullable=False)
    spreadsheet_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserSheet(user_id='{self.user_id}', sheet_id='{self.spreadsheet_id}')>"


# --- Database Initialization ---


def init_db() -> None:
    """
    Initializes the database by creating tables based on the defined models.
    """
    logger.info("Initializing database and creating tables if they don't exist...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables checked/created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


# --- Dependency for FastAPI-style session management (optional but good practice) ---
# If you were using FastAPI, you'd use this dependency.
# For this bot structure, you might pass SessionLocal directly or manage sessions differently.
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
