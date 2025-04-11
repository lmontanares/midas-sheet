#!/usr/bin/env python
"""
Simple script to test that imports with the updated typing work correctly.
"""
import sys
import traceback

def test_imports():
    """Test importing key modules with updated typing."""
    try:
        # Try importing the main module
        from main import main
        print("✅ Successfully imported main function.")
    except Exception as e:
        print(f"❌ Error importing main: {e}")
        traceback.print_exc()

    try:
        # Try importing key modules with updated typing
        from src.db.database import User, AuthToken, UserSheet
        print("✅ Successfully imported database models.")
    except Exception as e:
        print(f"❌ Error importing database: {e}")
        traceback.print_exc()

    try:
        from src.auth.oauth import OAuthManager
        print("✅ Successfully imported OAuthManager.")
    except Exception as e:
        print(f"❌ Error importing OAuthManager: {e}")
        traceback.print_exc()

    try:
        from src.server.oauth_server import OAuthServer
        print("✅ Successfully imported OAuthServer.")
    except Exception as e:
        print(f"❌ Error importing OAuthServer: {e}")
        traceback.print_exc()

    try:
        from src.sheets.client import GoogleSheetsClient
        from src.sheets.operations import SheetsOperations
        print("✅ Successfully imported Sheets modules.")
    except Exception as e:
        print(f"❌ Error importing Sheets modules: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_imports()
    print("All imports tested.")
