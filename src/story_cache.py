"""
Simple cache to track recently used stories and avoid duplicates
"""
from pathlib import Path
import json
from typing import List, Optional
from .config import OUTPUT_DIR

CACHE_FILE = OUTPUT_DIR / "story_cache.json"
MAX_CACHE_SIZE = 50  # Keep last 50 story IDs


def load_cache() -> List[str]:
    """Load list of recently used story IDs"""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('used_ids', [])
        except:
            return []
    return []


def save_cache(used_ids: List[str]):
    """Save list of recently used story IDs"""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Keep only last MAX_CACHE_SIZE entries
    used_ids = used_ids[-MAX_CACHE_SIZE:]
    with open(CACHE_FILE, 'w') as f:
        json.dump({'used_ids': used_ids}, f)


def add_story_id(story_id: str):
    """Add a story ID to the cache"""
    used_ids = load_cache()
    if story_id not in used_ids:
        used_ids.append(story_id)
    save_cache(used_ids)


def get_avoid_ids() -> List[str]:
    """Get list of story IDs to avoid"""
    return load_cache()





