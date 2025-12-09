# YouTube Upload Setup Guide

This guide explains how to set up YouTube API credentials for automatic video uploads.

## Prerequisites

- A Google account
- A YouTube channel
- Python packages installed: `pip install -r requirements.txt`

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter a project name (e.g., "Reddit Reads Uploader")
4. Click "Create"

## Step 2: Enable YouTube Data API v3

1. In your project, go to "APIs & Services" → "Library"
2. Search for "YouTube Data API v3"
3. Click on it and press "Enable"

## Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" user type
   - Fill in required fields (App name, User support email, Developer contact)
   - Add your email to test users
   - Save and continue through scopes (default is fine)
   - Save and continue through test users
   - Back to dashboard
4. Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: "Reddit Reads Uploader" (or any name)
   - Click "Create"
5. Download the credentials:
   - Click the download icon (⬇️) next to your newly created OAuth client
   - Save the file as `client_secrets.json` in the project root directory

## Step 4: First-Time Authentication

### Option A: Local Machine (with browser)

When you run `server_scheduler.py` for the first time on a machine with a browser:

1. A browser window will open automatically
2. Sign in with your Google account (the one associated with your YouTube channel)
3. Click "Advanced" → "Go to [Your App Name] (unsafe)" if you see a warning
4. Click "Allow" to grant permissions
5. The token will be saved to `youtube_token.json` automatically

### Option B: Headless Server (no browser)

For Linux servers without a browser, use the standalone authentication script:

1. **Install dependencies:**
   ```bash
   pip install google-auth-oauthlib
   ```

2. **Run the authentication script:**
   ```bash
   python youtube_auth_headless.py
   ```

3. **Follow the prompts:**
   - The script will display a URL
   - Open that URL in a browser on any device (your local computer, phone, etc.)
   - Sign in with your Google account
   - Grant permissions
   - Copy the authorization code
   - Paste it back into the terminal on your server

4. **The token will be saved automatically** to `youtube_token.json`

**Note:** The token will be reused for future uploads. You only need to authenticate once unless the token expires.

## Step 5: Configure Privacy Settings

Edit your `.env` file or set environment variables:

```bash
# YouTube privacy status: "private", "unlisted", or "public"
YOUTUBE_PRIVACY_STATUS=private

# YouTube category ID (default: 22 = People & Blogs)
YOUTUBE_CATEGORY_ID=22
```

### Privacy Options:
- **private**: Only you can see the video (good for testing)
- **unlisted**: Anyone with the link can see it (good for review before publishing)
- **public**: Visible to everyone (use when ready to publish)

## Step 6: Run the Scheduler

```bash
python server_scheduler.py
```

The scheduler will:
1. Generate videos daily
2. Upload them to YouTube at evenly spaced intervals
3. Handle authentication automatically
4. Retry failed uploads on the next cycle

## Troubleshooting

### "client_secrets.json not found"
- Make sure you downloaded the OAuth credentials from Google Cloud Console
- Save it as `client_secrets.json` in the project root (same folder as `main_pipeline.py`)

### "Token expired" or authentication errors
- Delete `youtube_token.json` and run again to re-authenticate
- Make sure your OAuth consent screen is published (if using external app type)

### "Quota exceeded" errors
- YouTube API has daily quotas (default: 10,000 units/day)
- Each video upload uses ~1,600 units
- You can request quota increases in Google Cloud Console

### Upload fails with "Forbidden" error
- Make sure you're authenticated with the correct Google account
- Verify the account has a YouTube channel
- Check that YouTube Data API v3 is enabled in your project

## File Structure

After setup, you should have:
```
Autogen2/
├── client_secrets.json      # OAuth credentials (from Google Cloud)
├── youtube_token.json        # Auto-generated after first auth
├── server_scheduler.py       # Main scheduler script
└── ...
```

## Security Notes

- **Never commit `client_secrets.json` or `youtube_token.json` to version control**
- Add them to `.gitignore`:
  ```
  client_secrets.json
  youtube_token.json
  ```
- Keep your credentials secure and don't share them

## YouTube API Quotas

- Default quota: 10,000 units per day
- Video upload: ~1,600 units per upload
- You can upload approximately 6 videos per day with default quota
- Request quota increase if needed: Google Cloud Console → APIs & Services → Quotas

