"""
Tests para el módulo de Google Sheets.
"""

import pytest

from src.sheets.client import GoogleSheetsClient
from src.sheets.operations import SheetsOperations


def test_client_authentication(mocker):
    """Prueba la autenticación del cliente de Google Sheets."""
    # Arrange
    mock_client = mocker.Mock()
    mock_credentials = mocker.Mock()
    
    # Mock para Credentials.from_service_account_file
    mock_creds = mocker.patch("google.oauth2.service_account.Credentials.from_service_account_file")
    mock_creds.return_value = mock_credentials
    
    # Mock para gspread.authorize
    mock_authorize = mocker.patch("gspread.authorize")
    mock_authorize.return_value = mock_client
    
    client = GoogleSheetsClient("fake_credentials.json")

    # Act
    client.authenticate()

    # Assert
    assert client.client is not None
    assert client.client == mock_client
    mock_creds.assert_called_once_with("fake_credentials.json", scopes=GoogleSheetsClient.SCOPES)
    mock_authorize.assert_called_once_with(mock_credentials)


def test_open_spreadsheet_no_auth():
    """Prueba que se lanza error si no se ha autenticado."""
    # Arrange
    client = GoogleSheetsClient("fake_credentials.json")

    # Act & Assert
    with pytest.raises(RuntimeError, match="Debes autenticar antes de realizar operaciones"):
        client.open_spreadsheet("fake_id")


def test_sheets_operations_init(mocker):
    """Prueba la inicialización de operaciones."""
    # Arrange
    mock_client = mocker.Mock()
    spreadsheet_id = "fake_spreadsheet_id"

    # Act
    operations = SheetsOperations(mock_client, spreadsheet_id)

    # Assert
    assert operations.client == mock_client
    assert operations.spreadsheet_id == spreadsheet_id
    assert operations.spreadsheet is None


def test_sheets_operations_setup(mocker):
    """Prueba la configuración de la hoja de cálculo."""
    # Arrange
    mock_client = mocker.Mock()
    mock_spreadsheet = mocker.Mock()
    mock_client.open_spreadsheet.return_value = mock_spreadsheet
    mock_spreadsheet.title = "Test Spreadsheet"
    
    operations = SheetsOperations(mock_client, "fake_spreadsheet_id")
    
    # Act
    operations.setup()
    
    # Assert
    assert operations.spreadsheet == mock_spreadsheet
    mock_client.open_spreadsheet.assert_called_once_with("fake_spreadsheet_id")


def test_get_worksheet_without_setup(mocker):
    """Prueba que se lanza error si no se ha configurado la hoja de cálculo."""
    # Arrange
    mock_client = mocker.Mock()
    operations = SheetsOperations(mock_client, "fake_spreadsheet_id")
    
    # Act & Assert
    with pytest.raises(RuntimeError, match="Debes configurar la hoja de cálculo antes de realizar operaciones"):
        operations.get_worksheet("Sheet1")


def test_get_worksheet(mocker):
    """Prueba la obtención de una hoja de trabajo."""
    # Arrange
    mock_client = mocker.Mock()
    mock_spreadsheet = mocker.Mock()
    mock_worksheet = mocker.Mock()
    
    mock_client.open_spreadsheet.return_value = mock_spreadsheet
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    
    operations = SheetsOperations(mock_client, "fake_spreadsheet_id")
    operations.setup()
    
    # Act
    result = operations.get_worksheet("Sheet1")
    
    # Assert
    assert result == mock_worksheet
    mock_spreadsheet.worksheet.assert_called_once_with("Sheet1")


def test_get_worksheet_not_found(mocker):
    """Prueba el manejo de errores cuando no se encuentra una hoja."""
    # Arrange
    mock_client = mocker.Mock()
    mock_spreadsheet = mocker.Mock()
    mock_spreadsheet.worksheet.side_effect = Exception("Worksheet not found")
    
    mock_client.open_spreadsheet.return_value = mock_spreadsheet
    
    operations = SheetsOperations(mock_client, "fake_spreadsheet_id")
    operations.setup()
    
    # Act & Assert
    with pytest.raises(ValueError, match="La hoja 'Sheet1' no existe"):
        operations.get_worksheet("Sheet1")
