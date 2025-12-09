"""
Standalone YouTube OAuth authentication script for headless servers.

This script can be run on a server without a browser to authenticate YouTube API.
It uses a manual OAuth flow which provides a URL to open in a browser and a code to paste back.

Usage:
    python youtube_auth_headless.py
"""

import json
import os
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
except ImportError:
    print("❌ Required packages not installed!")
    print("   Install with: pip install google-auth-oauthlib google-auth")
    exit(1)

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# Get project root (assuming script is in project root)
BASE_DIR = Path(__file__).resolve().parent

# File paths
CLIENT_SECRETS_FILE = BASE_DIR / "client_secrets.json"
TOKEN_FILE = BASE_DIR / "youtube_token.json"


def main():
    """Run OAuth flow for headless server authentication."""
    
    # Check if client_secrets.json exists
    if not CLIENT_SECRETS_FILE.exists():
        print(f"❌ client_secrets.json not found at: {CLIENT_SECRETS_FILE}")
        print("\nTo get client_secrets.json:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create/select a project")
        print("3. Enable YouTube Data API v3")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Download and save as: client_secrets.json")
        exit(1)
    
    print("🔐 Starting YouTube OAuth authentication (manual flow)...")
    print(f"   Client secrets: {CLIENT_SECRETS_FILE}")
    print(f"   Token will be saved to: {TOKEN_FILE}\n")
    
    # Create OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRETS_FILE), 
        SCOPES
    )
    
    # Get authorization URL
    flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'  # Out-of-band flow
    
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    # Display instructions
    print("=" * 60)
    print("MANUAL AUTHENTICATION - Follow these steps:")
    print("=" * 60)
    print("1. Open this URL in a browser (on any device):")
    print()
    print(f"   {auth_url}")
    print()
    print("2. Sign in with your Google account")
    print("3. Grant permissions to the application")
    print("4. You will see an authorization code")
    print("5. Copy that code and paste it below")
    print("=" * 60)
    print()
    
    # Get authorization code from user
    try:
        auth_code = input("Enter the authorization code: ").strip()
    except KeyboardInterrupt:
        print("\n❌ Authentication cancelled by user")
        exit(1)
    
    if not auth_code:
        print("❌ No authorization code provided")
        exit(1)
    
    # Exchange code for credentials
    try:
        flow.fetch_token(code=auth_code)
        creds = flow.credentials
    except Exception as e:
        print(f"\n❌ Failed to exchange code for token: {e}")
        print("   Make sure you copied the entire authorization code")
        exit(1)
    
    # Save credentials
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())
    
    print()
    print("=" * 60)
    print("✅ Authentication successful!")
    print("=" * 60)
    print(f"Token saved to: {TOKEN_FILE}")
    print("\nYou can now use the YouTube uploader without browser authentication.")
    print("The token will be reused automatically until it expires.")


if __name__ == "__main__":
    main()

