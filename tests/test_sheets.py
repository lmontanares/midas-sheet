"""
Tests para el módulo de Google Sheets.
"""

from unittest.mock import Mock, patch

import pytest

from src.sheets.client import GoogleSheetsClient
from src.sheets.operations import SheetsOperations


@patch("google.oauth2.service_account.Credentials.from_service_account_file")
@patch("googleapiclient.discovery.build")
def test_client_authentication(mock_build, mock_creds):
    """Prueba la autenticación del cliente de Google Sheets."""
    # Arrange
    mock_service = Mock()
    mock_build.return_value = mock_service
    client = GoogleSheetsClient("fake_credentials.json")

    # Act
    client.authenticate()

    # Assert
    assert client.service is not None
    mock_creds.assert_called_once()
    mock_build.assert_called_once_with("sheets", "v4", credentials=mock_creds.return_value)


def test_get_sheet_values_no_auth():
    """Prueba que se lanza error si no se ha autenticado."""
    # Arrange
    client = GoogleSheetsClient("fake_credentials.json")

    # Act & Assert
    with pytest.raises(RuntimeError, match="Debes autenticar antes de realizar operaciones"):
        client.get_sheet_values("fake_id", "Sheet1!A1:B10")


def test_sheets_operations_init():
    """Prueba la inicialización de operaciones."""
    # Arrange
    mock_client = Mock()

    # Act
    operations = SheetsOperations(mock_client)

    # Assert
    assert operations.client == mock_client
