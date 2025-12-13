"""
Semi-Automatic Manual Video Uploader

Scans the manual_uploads/ folder for video directories,
uploads them to YouTube, and deletes them after successful upload.

Usage:
    python manual_uploader.py

Place video folders (with final_video.mp4 and metadata.json) in manual_uploads/
"""

import json
import shutil
from pathlib import Path
from typing import List, Optional, Dict
import argparse

from src.config import BASE_DIR, YOUTUBE_PRIVACY_STATUS
from src.youtube_uploader import upload_video_to_youtube


MANUAL_UPLOADS_DIR = BASE_DIR / "manual_uploads"
MANUAL_UPLOADS_DIR.mkdir(exist_ok=True)


def find_video_folders(upload_dir: Path) -> List[Path]:
    """
    Find all video folders in the upload directory.
    A video folder must contain:
    - final_video.mp4 (or any .mp4 file)
    - metadata.json
    """
    video_folders = []
    
    for item in upload_dir.iterdir():
        if not item.is_dir():
            continue
        
        # Check for video file
        video_files = list(item.glob("*.mp4"))
        if not video_files:
            continue
        
        # Check for metadata.json
        metadata_path = item / "metadata.json"
        if not metadata_path.exists():
            print(f"⚠️  Skipping {item.name}: no metadata.json found")
            continue
        
        # Use the first MP4 file found (usually final_video.mp4)
        video_folders.append((item, video_files[0], metadata_path))
    
    return video_folders


def upload_and_delete(video_folder: Path, video_path: Path, metadata_path: Path, 
                      privacy_status: str = "private", dry_run: bool = False) -> bool:
    """
    Upload video to YouTube and delete folder if successful.
    
    Args:
        video_folder: Path to the video folder
        video_path: Path to the video file
        metadata_path: Path to the metadata.json file
        privacy_status: YouTube privacy status
        dry_run: If True, don't actually upload or delete
    
    Returns:
        True if successful, False otherwise
    """
    folder_name = video_folder.name
    print(f"\n{'='*60}")
    print(f"Processing: {folder_name}")
    print(f"{'='*60}")
    print(f"📁 Folder: {video_folder}")
    print(f"🎥 Video: {video_path}")
    print(f"📋 Metadata: {metadata_path}")
    
    if dry_run:
        print("🔍 DRY RUN: Would upload and delete this folder")
        return True
    
    try:
        # Upload to YouTube
        print(f"\n📤 Uploading to YouTube (privacy: {privacy_status})...")
        upload_result = upload_video_to_youtube(
            video_path=str(video_path),
            metadata_path=str(metadata_path),
            privacy_status=privacy_status
        )
        
        video_id = upload_result.get("video_id")
        video_url = upload_result.get("video_url")
        
        print(f"✅ Upload successful!")
        print(f"   Video ID: {video_id}")
        print(f"   URL: {video_url}")
        
        # Delete the folder after successful upload
        print(f"\n🗑️  Deleting folder: {video_folder}")
        shutil.rmtree(video_folder)
        print(f"✅ Folder deleted successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        print(f"⚠️  Folder kept for manual review: {video_folder}")
        return False


def main(dry_run: bool = False, privacy_status: Optional[str] = None):
    """
    Main function to process all videos in manual_uploads/ folder.
    
    Args:
        dry_run: If True, show what would be uploaded without actually uploading
        privacy_status: Override privacy status from config
    """
    if privacy_status is None:
        privacy_status = YOUTUBE_PRIVACY_STATUS
    
    print(f"🔍 Scanning {MANUAL_UPLOADS_DIR} for video folders...")
    
    video_folders = find_video_folders(MANUAL_UPLOADS_DIR)
    
    if not video_folders:
        print("ℹ️  No video folders found in manual_uploads/")
        print("   Place video folders (with final_video.mp4 and metadata.json) in this folder")
        return
    
    print(f"📦 Found {len(video_folders)} video folder(s) to process")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE: No uploads or deletions will be performed")
    
    successful = 0
    failed = 0
    
    for video_folder, video_path, metadata_path in video_folders:
        success = upload_and_delete(
            video_folder=video_folder,
            video_path=video_path,
            metadata_path=metadata_path,
            privacy_status=privacy_status,
            dry_run=dry_run
        )
        
        if success:
            successful += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Summary")
    print(f"{'='*60}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📦 Total: {len(video_folders)}")
    
    if failed > 0:
        print(f"\n⚠️  {failed} folder(s) were kept for manual review")
        print(f"   Check {MANUAL_UPLOADS_DIR} for failed uploads")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Semi-automatic YouTube uploader for manually placed videos"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without actually uploading or deleting"
    )
    parser.add_argument(
        "--privacy",
        type=str,
        choices=["private", "unlisted", "public"],
        help="Override privacy status (default: from config)"
    )
    args = parser.parse_args()
    
    main(dry_run=args.dry_run, privacy_status=args.privacy)

