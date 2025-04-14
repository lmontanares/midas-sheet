"""
Tests para el módulo de Google Sheets.
"""

import pytest

from src.sheets.client import GoogleSheetsClient
from src.sheets.operations import SheetsOperations


def test_client_authentication(mocker):
    """Test Google Sheets client authentication."""
    # Arrange
    mock_client = mocker.Mock()
    mock_credentials = mocker.Mock()

    # Mock for Credentials.from_service_account_file
    mock_creds = mocker.patch("google.oauth2.service_account.Credentials.from_service_account_file")
    mock_creds.return_value = mock_credentials

    # Mock for gspread.authorize
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
    """Test that an error is raised if not authenticated."""
    # Arrange
    client = GoogleSheetsClient("fake_credentials.json")

    # Act & Assert
    with pytest.raises(RuntimeError, match="Debes autenticar antes de realizar operaciones"):
        client.open_spreadsheet("fake_id")


def test_sheets_operations_init(mocker):
    """Test operations initialization."""
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
    """Test spreadsheet setup."""
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
    """Test that an error is raised if the spreadsheet has not been set up."""
    # Arrange
    mock_client = mocker.Mock()
    operations = SheetsOperations(mock_client, "fake_spreadsheet_id")

    # Act & Assert
    with pytest.raises(RuntimeError, match="Debes configurar la hoja de cálculo antes de realizar operaciones"):
        operations.get_worksheet("Sheet1")


def test_get_worksheet(mocker):
    """Test getting a worksheet."""
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
    """Test error handling when a sheet is not found."""
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


def test_append_row(mocker):
    """Test adding a row to a worksheet."""
    # Arrange
    mock_client = mocker.Mock()
    mock_spreadsheet = mocker.Mock()
    mock_worksheet = mocker.Mock()

    mock_client.open_spreadsheet.return_value = mock_spreadsheet
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    mock_worksheet.append_row.return_value = None

    operations = SheetsOperations(mock_client, "fake_spreadsheet_id")
    operations.setup()

    # Act
    values = ["2023-10-15", "usuario", "comida", 50.5, "2023-10-15 12:34:56"]
    result = operations.append_row("gastos", values)

    # Assert
    assert result is True
    mock_spreadsheet.worksheet.assert_called_once_with("gastos")
    mock_worksheet.append_row.assert_called_once_with(values)


def test_append_row_error(mocker):
    """Test error handling when adding a row."""
    # Arrange
    mock_client = mocker.Mock()
    mock_spreadsheet = mocker.Mock()
    mock_worksheet = mocker.Mock()

    mock_client.open_spreadsheet.return_value = mock_spreadsheet
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    mock_worksheet.append_row.side_effect = Exception("Error al añadir fila")

    operations = SheetsOperations(mock_client, "fake_spreadsheet_id")
    operations.setup()

    # Act & Assert
    with pytest.raises(Exception, match="Error al añadir fila"):
        operations.append_row("gastos", ["2023-10-15", "usuario", "comida", 50.5, "2023-10-15 12:34:56"])


def test_ensure_sheets_exist(mocker):
    """Test creation of necessary sheets if they do not exist."""
    # Arrange
    mock_client = mocker.Mock()
    mock_spreadsheet = mocker.Mock()
    mock_worksheet = mocker.Mock()

    mock_client.open_spreadsheet.return_value = mock_spreadsheet
    # Simulate that the sheets do not exist initially
    mock_spreadsheet.worksheets.return_value = []
    mock_spreadsheet.add_worksheet.return_value = mock_worksheet

    operations = SheetsOperations(mock_client, "fake_spreadsheet_id")

    # Act
    operations.spreadsheet = mock_spreadsheet
    operations.ensure_sheets_exist()

    # Assert
    # Verify that the two necessary sheets are created
    assert mock_spreadsheet.add_worksheet.call_count == 2
    expected_calls = [mocker.call(title="gastos", rows=1, cols=5), mocker.call(title="ingresos", rows=1, cols=5)]
    assert mock_spreadsheet.add_worksheet.call_args_list == expected_calls
    # Verify that headers are added
    assert mock_worksheet.append_row.call_count == 2
