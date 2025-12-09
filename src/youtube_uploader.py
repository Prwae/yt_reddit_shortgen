"""
YouTube Uploader Module - Uploads videos to YouTube using YouTube Data API v3
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import time

from src.config import BASE_DIR

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# YouTube API configuration
CLIENT_SECRETS_FILE = BASE_DIR / "client_secrets.json"
TOKEN_FILE = BASE_DIR / "youtube_token.json"


class YouTubeUploader:
    """Handles YouTube video uploads with OAuth 2.0 authentication"""
    
    def __init__(self):
        self.youtube = None
        self.credentials = None
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Authenticate with YouTube API using OAuth 2.0"""
        creds = None
        
        # Load existing token if available
        if TOKEN_FILE.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
            except Exception as e:
                print(f"⚠️  Error loading token: {e}")
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"⚠️  Token refresh failed: {e}")
                    creds = None
            
            if not creds:
                if not CLIENT_SECRETS_FILE.exists():
                    raise FileNotFoundError(
                        f"❌ YouTube API credentials not found!\n"
                        f"   Please download client_secrets.json from Google Cloud Console:\n"
                        f"   1. Go to https://console.cloud.google.com/\n"
                        f"   2. Create/select a project\n"
                        f"   3. Enable YouTube Data API v3\n"
                        f"   4. Create OAuth 2.0 credentials (Desktop app)\n"
                        f"   5. Download and save as: {CLIENT_SECRETS_FILE}\n"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CLIENT_SECRETS_FILE), SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            TOKEN_FILE.parent.mkdir(exist_ok=True)
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        self.credentials = creds
        self.youtube = build('youtube', 'v3', credentials=creds)
        print("✓ YouTube API authenticated")
    
    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list] = None,
        category_id: str = "22",  # People & Blogs
        privacy_status: str = "private",  # private, unlisted, public
        metadata_path: Optional[str] = None
    ) -> Dict:
        """
        Upload a video to YouTube
        
        Args:
            video_path: Path to video file
            title: Video title (max 100 chars)
            description: Video description
            tags: List of tags (max 500 chars total)
            category_id: YouTube category ID (default: 22 = People & Blogs)
            privacy_status: private, unlisted, or public
            metadata_path: Optional path to metadata.json to update with YouTube ID
        
        Returns:
            Dict with video_id, video_url, and upload status
        """
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Prepare metadata
        body = {
            'snippet': {
                'title': title[:100],  # YouTube limit
                'description': description[:5000],  # YouTube limit
                'tags': tags[:15] if tags else [],  # Max 15 tags
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Prepare media file
        media = MediaFileUpload(
            video_path,
            chunksize=-1,
            resumable=True,
            mimetype='video/*'
        )
        
        # Upload video
        print(f"⬆️  Uploading '{title[:50]}...' to YouTube...")
        try:
            insert_request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Execute upload with progress tracking
            response = self._resumable_upload(insert_request)
            
            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            print(f"✓ Upload successful! Video ID: {video_id}")
            print(f"  URL: {video_url}")
            
            # Update metadata file if provided
            if metadata_path and Path(metadata_path).exists():
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    metadata['youtube'] = {
                        'video_id': video_id,
                        'video_url': video_url,
                        'uploaded_at': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
                    }
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"⚠️  Could not update metadata file: {e}")
            
            return {
                'success': True,
                'video_id': video_id,
                'video_url': video_url,
                'title': title
            }
        
        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8'))
            error_msg = error_details.get('error', {}).get('message', str(e))
            print(f"❌ YouTube upload failed: {error_msg}")
            raise Exception(f"YouTube upload error: {error_msg}")
    
    def _resumable_upload(self, insert_request) -> Dict:
        """Execute resumable upload with retry logic"""
        response = None
        error = None
        retry = 0
        max_retries = 3
        
        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if response is not None:
                    if 'id' in response:
                        return response
                    else:
                        raise Exception(f"Upload failed: {response}")
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    # Retry on server errors
                    error = f"Retriable error {e.resp.status}: {e}"
                    if retry < max_retries:
                        retry += 1
                        wait_time = 2 ** retry  # Exponential backoff
                        print(f"⚠️  {error}, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                else:
                    # Non-retriable error
                    raise
            except Exception as e:
                error = str(e)
                if retry < max_retries:
                    retry += 1
                    wait_time = 2 ** retry
                    print(f"⚠️  {error}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        
        if error:
            raise Exception(f"Upload failed after {max_retries} retries: {error}")
        
        return response


def upload_video_to_youtube(
    video_path: str,
    metadata_path: str,
    privacy_status: str = "private"
) -> Dict:
    """
    Convenience function to upload video using metadata file
    
    Args:
        video_path: Path to video file
        metadata_path: Path to metadata.json file
        privacy_status: YouTube privacy status (private, unlisted, public)
    
    Returns:
        Dict with upload result
    """
    if not Path(metadata_path).exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    
    # Load metadata
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Extract upload info
    title = metadata.get('title', 'Untitled Video')
    description = metadata.get('description', '')
    tags = metadata.get('tags', [])
    hashtags = metadata.get('hashtags', [])
    
    # Combine hashtags into description if not already there
    if hashtags and '#RedditStories' not in description:
        hashtag_str = ' '.join(hashtags)
        description = f"{description}\n\n{hashtag_str}"
    
    # Upload
    uploader = YouTubeUploader()
    return uploader.upload_video(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        privacy_status=privacy_status,
        metadata_path=metadata_path
    )

