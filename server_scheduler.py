"""
24/7 daily video generator/uploader runner.

Behavior:
- Once every 24 hours: generate a daily "pack" of videos into a non-output folder.
- Each daily pack goes under DAILY_PACKS_DIR/YYYYMMDD/.
- Generate videos until credits/quota are exhausted (or generation fails).
- Upload all videos for the day at evenly spaced intervals over 24h.
- Do not start the next day's generation until all uploads for the current pack finish.
- Keep only the last 3 daily packs (delete anything older than 2 days).

Note: upload_video() is a stub — replace with real upload logic.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from main_pipeline import VideoPipeline
from src.config import BASE_DIR, YOUTUBE_PRIVACY_STATUS
from src.youtube_uploader import upload_video_to_youtube


DAILY_PACKS_DIR = BASE_DIR / "daily_packs"
DAILY_PACKS_DIR.mkdir(exist_ok=True)

PACK_RETENTION_DAYS = 3  # keep today + previous 2 days
RUN_INTERVAL_HOURS = 24
MANIFEST_NAME = "manifest.json"


def _today_str() -> str:
    return datetime.utcnow().strftime("%Y%m%d")


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
    msg = str(err).lower()
    keywords = ["quota", "credit", "insufficient", "limit", "billing", "exceeded"]
    return any(k in msg for k in keywords)


def _cleanup_old_packs() -> None:
    """Delete packs older than PACK_RETENTION_DAYS."""
    cutoff = datetime.utcnow().date() - timedelta(days=PACK_RETENTION_DAYS - 1)
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

    interval_seconds = 24 * 3600 / max(1, len(videos))
    start_time = datetime.utcnow()

    for idx, video in enumerate(pending):
        scheduled_time = start_time + timedelta(seconds=interval_seconds * idx)
        wait_seconds = (scheduled_time - datetime.utcnow()).total_seconds()
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
            video["uploaded_at"] = datetime.utcnow().isoformat()
            video["youtube_video_id"] = upload_result.get("video_id")
            video["youtube_url"] = upload_result.get("video_url")
            _save_manifest(pack_dir, manifest)
            print(f"✓ Uploaded {video['video_path']} → {upload_result.get('video_url')}")
        except Exception as e:
            print(f"❌ Upload failed for {video['video_path']}: {e}")
            import traceback
            traceback.print_exc()
            _save_manifest(pack_dir, manifest)
            # Stop further uploads to avoid cascading issues; retry next cycle
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
                    "generated_at": datetime.utcnow().isoformat(),
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


def run_forever() -> None:
    """Main loop: daily generation + scheduled uploads, forever."""
    while True:
        cycle_start = datetime.utcnow()
        today = _today_str()
        pack_dir = DAILY_PACKS_DIR / today

        print(f"\n=== Daily cycle start for {today} ===")
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

        # Sleep until next 24h tick from cycle start
        next_run = cycle_start + timedelta(hours=RUN_INTERVAL_HOURS)
        sleep_seconds = (next_run - datetime.utcnow()).total_seconds()
        if sleep_seconds > 0:
            print(f"🛌 Sleeping {sleep_seconds/3600:.1f} hours until next cycle...")
            time.sleep(sleep_seconds)


if __name__ == "__main__":
    run_forever()


