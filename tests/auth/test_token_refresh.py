"""
Tests for OAuth token refresh functionality.

These tests verify that token refreshing works correctly when tokens expire.
"""

import datetime
import os
import unittest
from unittest.mock import MagicMock, patch

import pytest
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from src.auth.oauth import OAuthManager
from src.sheets.client import GoogleSheetsClient


class TestTokenRefresh(unittest.TestCase):
    """Test suite for token refresh functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary test directory if it doesn't exist
        os.makedirs("tests/temp", exist_ok=True)
        # Create a dummy client secrets file
        with open("tests/temp/test_client_secrets.json", "w") as f:
            f.write('{"web": {"client_id": "test_id", "client_secret": "test_secret"}}')

        self.oauth_manager = OAuthManager(
            client_secrets_file="tests/temp/test_client_secrets.json",
            redirect_uri="http://localhost:8000/callback",
            encryption_key=b"test_encryption_key_must_be_32_bytes_!"
        )
        
        # Mock methods to avoid external dependencies
        self.oauth_manager.load_token = MagicMock()
        self.oauth_manager._get_client_secret = MagicMock(return_value="test_secret")
        self.oauth_manager.save_token = MagicMock()
        self.oauth_manager.revoke_token = MagicMock()

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove test files
        if os.path.exists("tests/temp/test_client_secrets.json"):
            os.remove("tests/temp/test_client_secrets.json")

    def test_token_refresh_when_expired(self):
        """Test that tokens are refreshed when they expire."""
        # Create expired token data
        expired_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        self.oauth_manager.load_token.return_value = {
            "token": "old_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
            "expiry": expired_time.isoformat()
        }
        
        # Mock credentials refresh
        with patch("google.oauth2.credentials.Credentials.refresh") as mock_refresh:
            def side_effect(request):
                # Update credentials when refresh is called
                credentials = Credentials(
                    token="new_token",
                    refresh_token="test_refresh_token",
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id="test_client_id",
                    client_secret="test_secret",
                    scopes=["https://www.googleapis.com/auth/spreadsheets"]
                )
                # Set an expiry time in the future
                credentials.expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
                # Replace the mocked credentials with the updated ones
                type(mock_refresh.return_value).token = "new_token"
                type(mock_refresh.return_value).expiry = credentials.expiry
                return credentials
                
            mock_refresh.side_effect = side_effect
            
            # Get credentials - this should trigger a refresh
            credentials = self.oauth_manager.get_credentials("test_user")
            
            # Verify refresh was called
            mock_refresh.assert_called_once()
            
            # Verify new token was saved
            self.oauth_manager.save_token.assert_called_once()
            
            # Verify credentials are valid and have the new token
            self.assertIsNotNone(credentials)
            self.assertEqual(credentials.token, "new_token")
            self.assertFalse(credentials.expired)

    def test_token_refresh_failure(self):
        """Test handling of refresh failures."""
        # Create expired token data
        expired_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        self.oauth_manager.load_token.return_value = {
            "token": "old_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
            "expiry": expired_time.isoformat()
        }
        
        # Mock refresh to fail
        with patch("google.oauth2.credentials.Credentials.refresh") as mock_refresh:
            mock_refresh.side_effect = RefreshError("Invalid grant")
            
            # Get credentials - this should trigger a refresh attempt that fails
            credentials = self.oauth_manager.get_credentials("test_user")
            
            # Verify refresh was called
            mock_refresh.assert_called_once()
            
            # Verify token was revoked due to refresh failure
            self.oauth_manager.revoke_token.assert_called_once()
            
            # Verify credentials are None
            self.assertIsNone(credentials)

    def test_proactive_refresh_for_soon_expiring_token(self):
        """Test that tokens are proactively refreshed if they're about to expire."""
        # Create token data that expires in 4 minutes
        expiry_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=4)
        self.oauth_manager.load_token.return_value = {
            "token": "old_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
            "expiry": expiry_time.isoformat()
        }
        
        # Mock credentials refresh
        with patch("google.oauth2.credentials.Credentials.refresh") as mock_refresh:
            def side_effect(request):
                # Update credentials when refresh is called
                credentials = Credentials(
                    token="new_token",
                    refresh_token="test_refresh_token",
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id="test_client_id",
                    client_secret="test_secret",
                    scopes=["https://www.googleapis.com/auth/spreadsheets"]
                )
                # Set an expiry time further in the future
                credentials.expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
                # Replace the mocked credentials with the updated ones
                type(mock_refresh.return_value).token = "new_token"
                type(mock_refresh.return_value).expiry = credentials.expiry
                return credentials
                
            mock_refresh.side_effect = side_effect
            
            # Get credentials - this should trigger a refresh since token expires soon
            credentials = self.oauth_manager.get_credentials("test_user")
            
            # Verify refresh was called
            mock_refresh.assert_called_once()
            
            # Verify new token was saved
            self.oauth_manager.save_token.assert_called_once()
            
            # Verify credentials are valid and have the new token
            self.assertIsNotNone(credentials)
            self.assertEqual(credentials.token, "new_token")
            self.assertFalse(credentials.expired)


class TestGoogleSheetsClientToken(unittest.TestCase):
    """Test suite for GoogleSheetsClient token handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock OAuth manager
        self.oauth_manager = MagicMock()
        self.client = GoogleSheetsClient(self.oauth_manager)
        
    def test_get_client_creates_new_client_when_cached_client_exists(self):
        """Test that _get_client creates a new client even when a cached client exists."""
        # Setup mock credentials
        mock_credentials = MagicMock()
        mock_credentials.expired = False
        mock_credentials.valid = True
        
        # Setup OAuth manager to return valid credentials
        self.oauth_manager.get_credentials.return_value = mock_credentials
        
        # Mock gspread.authorize
        with patch("gspread.authorize") as mock_authorize:
            mock_authorize.return_value = MagicMock()
            
            # Create a cached client first
            self.client.client_cache["test_user"] = MagicMock()
            
            # Call _get_client
            result = self.client._get_client("test_user")
            
            # Verify get_credentials was called to get fresh credentials
            self.oauth_manager.get_credentials.assert_called_once_with("test_user")
            
            # Verify gspread.authorize was called
            mock_authorize.assert_called_once_with(mock_credentials)
            
            # Verify new client was cached
            self.assertEqual(self.client.client_cache["test_user"], mock_authorize.return_value)
            
            # Verify result is the new client
            self.assertEqual(result, mock_authorize.return_value)
            
    def test_is_authenticated_checks_credentials(self):
        """Test that is_authenticated attempts to get a client to check credentials."""
        # Setup _get_client to return a mock client
        self.client._get_client = MagicMock(return_value=MagicMock())
        
        # Call is_authenticated
        result = self.client.is_authenticated("test_user")
        
        # Verify _get_client was called
        self.client._get_client.assert_called_once_with("test_user")
        
        # Verify result is True
        self.assertTrue(result)
        
        # Test when _get_client returns None
        self.client._get_client.reset_mock()
        self.client._get_client.return_value = None
        
        # Call is_authenticated
        result = self.client.is_authenticated("test_user")
        
        # Verify result is False
        self.assertFalse(result)
