"""
24/7 daily video generator/uploader runner.

Behavior:
- Starts daily cycles at midnight Pacific Time
- Once every 24 hours: generate a daily "pack" of videos into a non-output folder.
- Each daily pack goes under DAILY_PACKS_DIR/YYYYMMDD/.
- Generate videos until credits/quota are exhausted (or generation fails).
- Upload all videos for the day at evenly spaced intervals over 24h.
- Do not start the next day's generation until all uploads for the current pack finish.
- Keep only the last 3 daily packs (delete anything older than 2 days).
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import argparse

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Python < 3.9 fallback
    try:
        import pytz
        ZoneInfo = None  # Will use pytz instead
    except ImportError:
        raise ImportError(
            "Timezone support requires Python 3.9+ (zoneinfo) or pytz package.\n"
            "Install pytz: pip install pytz"
        )

from main_pipeline import VideoPipeline
from src.config import BASE_DIR, YOUTUBE_PRIVACY_STATUS
from src.youtube_uploader import upload_video_to_youtube


DAILY_PACKS_DIR = BASE_DIR / "daily_packs"
DAILY_PACKS_DIR.mkdir(exist_ok=True)

PACK_RETENTION_DAYS = 3  # keep today + previous 2 days
RUN_INTERVAL_HOURS = 24
MANIFEST_NAME = "manifest.json"

# Pacific Time zone (handles PST/PDT automatically)
if ZoneInfo:
    PACIFIC_TZ = ZoneInfo("America/Los_Angeles")
else:
    PACIFIC_TZ = pytz.timezone("America/Los_Angeles")


def _now_pacific() -> datetime:
    """Get current time in Pacific Time."""
    if ZoneInfo:
        return datetime.now(PACIFIC_TZ)
    else:
        return datetime.now(pytz.UTC).astimezone(PACIFIC_TZ)


def _today_str() -> str:
    """Get today's date string in Pacific Time."""
    return _now_pacific().strftime("%Y%m%d")


def _next_midnight_pacific() -> datetime:
    """Calculate next midnight Pacific Time."""
    now = _now_pacific()
    
    if ZoneInfo:
        # Using zoneinfo (Python 3.9+)
        midnight_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if now >= midnight_today:
            midnight_today += timedelta(days=1)
    else:
        # Using pytz
        today = now.date()
        midnight_today = PACIFIC_TZ.localize(
            datetime(today.year, today.month, today.day, 0, 0, 0)
        )
        if now >= midnight_today:
            tomorrow = today + timedelta(days=1)
            midnight_today = PACIFIC_TZ.localize(
                datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
            )
    
    return midnight_today


def _load_manifest(pack_dir: Path) -> Dict:
    manifest_path = pack_dir / MANIFEST_NAME
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"date": pack_dir.name, "videos": []}


def _save_manifest(pack_dir: Path, manifest: Dict) -> None:
    manifest_path = pack_dir / MANIFEST_NAME
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def _is_credit_error(err: Exception) -> bool:
    """Check if error is related to API quota/credits."""
    from src.youtube_uploader import QuotaExceededError
    
    # Check for YouTube quota errors
    if isinstance(err, QuotaExceededError):
        return True
    
    msg = str(err).lower()
    keywords = ["quota", "credit", "insufficient", "limit", "billing", "exceeded", "rate limit"]
    return any(k in msg for k in keywords)


def _cleanup_old_packs() -> None:
    """Delete packs older than PACK_RETENTION_DAYS."""
    cutoff = _now_pacific().date() - timedelta(days=PACK_RETENTION_DAYS - 1)
    for item in DAILY_PACKS_DIR.iterdir():
        if not item.is_dir():
            continue
        try:
            pack_date = datetime.strptime(item.name, "%Y%m%d").date()
        except ValueError:
            continue
        if pack_date < cutoff:
            print(f"🧹 Removing old pack: {item}")
            for child in item.iterdir():
                if child.is_file():
                    child.unlink(missing_ok=True)
                elif child.is_dir():
                    for sub in child.rglob("*"):
                        if sub.is_file():
                            sub.unlink(missing_ok=True)
                    subdirs = sorted([d for d in child.rglob("*") if d.is_dir()], reverse=True)
                    for d in subdirs:
                        d.rmdir()
                    child.rmdir()
            item.rmdir()


def _ensure_dirs(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _upload_video(video_path: str, metadata_path: str, privacy_status: str = "private") -> Dict:
    """
    Upload video to YouTube using metadata file.
    
    Args:
        video_path: Path to video file
        metadata_path: Path to metadata.json file
        privacy_status: YouTube privacy status (private, unlisted, public)
    
    Returns:
        Dict with upload result (video_id, video_url, etc.)
    """
    return upload_video_to_youtube(
        video_path=video_path,
        metadata_path=metadata_path,
        privacy_status=privacy_status
    )


def _schedule_uploads(manifest: Dict, pack_dir: Path) -> None:
    """Upload all videos for the pack at evenly spaced intervals across 24h."""
    videos = manifest.get("videos", [])
    pending = [v for v in videos if not v.get("uploaded")]
    if not pending:
        print("✓ All videos already uploaded for this pack.")
        return

    # Calculate interval: spread uploads evenly over 24 hours
    # But ensure minimum 1 hour between uploads to avoid rate limits
    # YouTube default quota: ~6 uploads/day (1,600 units per upload, 10,000 units/day)
    min_interval_seconds = 3600  # 1 hour minimum between uploads
    ideal_interval = 24 * 3600 / max(1, len(videos))
    interval_seconds = max(ideal_interval, min_interval_seconds)
    
    start_time = _now_pacific()

    for idx, video in enumerate(pending):
        scheduled_time = start_time + timedelta(seconds=interval_seconds * idx)
        wait_seconds = (scheduled_time - _now_pacific()).total_seconds()
        if wait_seconds > 0:
            print(f"⏳ Waiting {wait_seconds/60:.1f} minutes until next upload slot...")
            time.sleep(wait_seconds)

        try:
            # Upload video to YouTube
            upload_result = _upload_video(
                video_path=video["video_path"],
                metadata_path=video["metadata_path"],
                privacy_status=YOUTUBE_PRIVACY_STATUS
            )
            
            # Update manifest with upload info
            video["uploaded"] = True
            video["uploaded_at"] = _now_pacific().isoformat()
            video["youtube_video_id"] = upload_result.get("video_id")
            video["youtube_url"] = upload_result.get("video_url")
            _save_manifest(pack_dir, manifest)
            print(f"✓ Uploaded {video['video_path']} → {upload_result.get('video_url')}")
        except Exception as e:
            print(f"❌ Upload failed for {video['video_path']}: {e}")
            import traceback
            traceback.print_exc()
            _save_manifest(pack_dir, manifest)
            
            # Check if it's a quota error - stop all uploads and wait for next day
            if _is_credit_error(e):
                print("⚠️  YouTube API quota exceeded. Stopping uploads for today.")
                print("   Remaining videos will be uploaded tomorrow when quota resets.")
                break
            
            # For other errors, stop to avoid cascading issues; retry next cycle
            break


def _generate_daily_pack(pack_dir: Path) -> Dict:
    """Generate videos until credits are exhausted or generation fails."""
    _ensure_dirs(pack_dir)
    manifest = _load_manifest(pack_dir)
    pipeline = VideoPipeline(output_dir=pack_dir)

    while True:
        try:
            result = pipeline.generate_video()
            if not result.get("success"):
                err_msg = result.get("error", "unknown error")
                print(f"⚠️  Generation failed: {err_msg}")
                if _is_credit_error(Exception(err_msg)):
                    break
                else:
                    # Non-credit error: stop this cycle but keep what we have
                    break

            manifest["videos"].append(
                {
                    "video_path": result["video_path"],
                    "metadata_path": result["metadata_path"],
                    "output_dir": result["output_dir"],
                    "uploaded": False,
                    "uploaded_at": None,
                    "generated_at": _now_pacific().isoformat(),
                }
            )
            _save_manifest(pack_dir, manifest)
            print(f"🎥 Generated video: {result['video_path']}")
        except Exception as e:
            print(f"❌ Generation exception: {e}")
            if _is_credit_error(e):
                print("Stopping generation due to suspected credit/quota exhaustion.")
            break

    return manifest


def run_forever(start_now: bool = False) -> None:
    """Main loop: daily generation + scheduled uploads, forever."""
    # Wait until next midnight Pacific Time before starting (unless start_now is True)
    if not start_now:
        next_midnight = _next_midnight_pacific()
        now = _now_pacific()
        wait_seconds = (next_midnight - now).total_seconds()
        
        if wait_seconds > 0:
            wait_hours = wait_seconds / 3600
            print(f"⏰ Waiting until midnight Pacific Time ({next_midnight.strftime('%Y-%m-%d %H:%M:%S %Z')})")
            print(f"   Current Pacific Time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"   Waiting {wait_hours:.2f} hours...")
            time.sleep(wait_seconds)
    else:
        print("▶️ start_now enabled: beginning immediately, next cycles at Pacific midnight.")
        now = _now_pacific()
        print(f"   Current Pacific Time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
    while True:
        cycle_start = _now_pacific()
        today = _today_str()
        pack_dir = DAILY_PACKS_DIR / today

        print(f"\n=== Daily cycle start for {today} (Pacific Time: {cycle_start.strftime('%Y-%m-%d %H:%M:%S %Z')}) ===")
        _cleanup_old_packs()

        manifest = _load_manifest(pack_dir)
        if not manifest.get("videos"):
            print("No existing videos for today. Generating pack...")
            manifest = _generate_daily_pack(pack_dir)
        else:
            print(f"Found existing pack with {len(manifest['videos'])} video(s). Resuming uploads.")

        if not manifest.get("videos"):
            print("Nothing to upload for this pack.")
        else:
            _schedule_uploads(manifest, pack_dir)

        # Sleep until next midnight Pacific Time
        next_midnight = _next_midnight_pacific()
        now = _now_pacific()
        sleep_seconds = (next_midnight - now).total_seconds()
        if sleep_seconds > 0:
            wait_hours = sleep_seconds / 3600
            print(f"🛌 Sleeping {wait_hours:.2f} hours until next midnight Pacific Time ({next_midnight.strftime('%Y-%m-%d %H:%M:%S %Z')})...")
            time.sleep(sleep_seconds)


def main():
    parser = argparse.ArgumentParser(description="Daily video generator/uploader scheduler")
    parser.add_argument(
        "--start-now",
        action="store_true",
        help="Start immediately (skip initial wait until Pacific midnight). Subsequent cycles still start at midnight PT."
    )
    args = parser.parse_args()
    run_forever(start_now=args.start_now)


if __name__ == "__main__":
    main()


