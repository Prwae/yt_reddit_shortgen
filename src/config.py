"""
Configuration file for Reddit Reads Video Generator
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project directories (BASE_DIR is the project root)
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
FONTS_DIR = BASE_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

VIDEOS_DIR = BASE_DIR / "videos"
BACKGROUNDS_DIR = VIDEOS_DIR / "backgrounds"
MUSIC_DIR = VIDEOS_DIR / "music"
INTRO_IMAGES_DIR = VIDEOS_DIR / "intro_images"
AVATAR_DIR = VIDEOS_DIR / "avatar"  # User's avatar image
NICKNAME_FILE = VIDEOS_DIR / "nickname.txt"  # User's nickname text file

# Create directories if they don't exist
for dir_path in [VIDEOS_DIR, BACKGROUNDS_DIR, MUSIC_DIR, INTRO_IMAGES_DIR, AVATAR_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# API Configuration
# Support multiple Gemini API keys (comma-separated or multiple env vars)
# Format: GEMINI_API_KEY=key1,key2,key3 or GEMINI_API_KEY_1=key1, GEMINI_API_KEY_2=key2, etc.
_gemini_keys_raw = os.getenv("GEMINI_API_KEY", "")
_gemini_keys_list = []

# Parse comma-separated keys from GEMINI_API_KEY
if _gemini_keys_raw:
    _gemini_keys_list.extend([k.strip() for k in _gemini_keys_raw.split(",") if k.strip()])

# Also check for numbered keys (GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.)
i = 1
while True:
    key = os.getenv(f"GEMINI_API_KEY_{i}", "")
    if not key:
        break
    # Support comma-separated in numbered keys too
    _gemini_keys_list.extend([k.strip() for k in key.split(",") if k.strip()])
    i += 1

# Remove duplicates while preserving order
_seen = set()
GEMINI_API_KEYS = []
for key in _gemini_keys_list:
    if key and key not in _seen:
        _seen.add(key)
        GEMINI_API_KEYS.append(key)

# Backward compatibility: single key
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")

# YouTube Upload Configuration
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "private")  # private, unlisted, or public
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "22")  # 22 = People & Blogs

# Reddit Configuration
ALLOWED_SUBREDDITS = [
    "AmItheAsshole",
    "AskReddit",
    "confession",
    "TrueOffMyChest",
    "relationship_advice",
    "tifu",
    "entitledparents",
    "prorevenge",
    "pettyrevenge"
]

MIN_UPVOTES = 100
MAX_POST_LENGTH = 5000  # characters

# Story Configuration
# Target duration: maximum 3 minutes (180 seconds) after speed-up
# With 1.35x speed multiplier, original content should be max 180 * 1.35 = 243 seconds
# Reading speed: ~2.5 words per second, so max ~607 words
MAX_VIDEO_DURATION_SECONDS = 180  # 3 minutes maximum
VIDEO_SPEED_MULTIPLIER = 1.2  # Speed up video by 1.35x
# Story word count filtering: stories should be 400-600 words to fit in 3 minutes
MIN_STORY_WORDS = 400  # Minimum words for a good story
MAX_STORY_WORDS = 600  # Maximum words to fit in 3 minutes

# Debug/Fast Render Mode
FAST_RENDER_MODE = False  # Set to True for fast debugging with placeholder text
FAST_RENDER_PLACEHOLDER_TEXT = "This is a test story for fast debugging. It contains just a few sentences to make rendering quick. Perfect for testing video generation without waiting for full stories."
FAST_RENDER_PLACEHOLDER_TITLE = "Test Story for Debugging hi wejfnw ieujfhwuefhwoie wefhwiue fhwefhw w efhwe hwuefhw hwief h"

# Video Configuration
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # 9:16 aspect ratio
FPS = 30

# Subtitle Configuration
SUBTITLE_FONT_SIZE = 72  # Font size for 1-2 words
SUBTITLE_FONT_COLOR = (255, 255, 255)  # White
SUBTITLE_STROKE_COLOR = (0, 0, 0)  # Black outline
SUBTITLE_STROKE_WIDTH = 6  # Outline for visibility (increased for better outline effect)
SUBTITLE_POSITION = "center"  # Center of screen
SUBTITLE_MARGIN = 0  # Not used for center positioning
SUBTITLE_WORDS_PER_LINE = 1  # One word per subtitle
SUBTITLE_ANIMATION_DURATION = 0.08  # Fast but subtle animation
SUBTITLE_SCALE_START = 0.95  # Start at 95% size (very subtle)
SUBTITLE_SCALE_END = 0.97  # End at 97% size (very subtle)

# Intro Card Configuration
INTRO_CARD_WIDTH = 900
INTRO_CARD_HEIGHT = 500
INTRO_CARD_BG_COLOR = (255, 255, 255)  # White background
INTRO_CARD_CORNER_RADIUS = 20
AVATAR_SIZE = 80
AVATAR_POSITION = (40, 40)  # Top left
NICKNAME_POSITION = (140, 50)  # Right of avatar
TITLE_POSITION = (40, 140)  # Below avatar and nickname
NICKNAME_FONT_SIZE = 32
TITLE_FONT_SIZE = 28
INTRO_DURATION = 4.0  # How long intro card shows (seconds)

# TTS Configuration
# Uses Edge-TTS (Microsoft Azure Neural Voices) - Free, no API keys required
EDGE_TTS_VOICE_NAME = os.getenv("EDGE_TTS_VOICE_NAME", None)  # If set, forces this voice
EDGE_TTS_VOICES = [
    "en-US-AriaNeural",      # Female, US English
    "en-US-JennyNeural",     # Female, US English
    "en-US-GuyNeural",       # Male, US English
    "en-GB-SoniaNeural",     # Female, British English
    "en-GB-RyanNeural",      # Male, British English
    "en-AU-NatashaNeural",   # Female, Australian English
    "en-AU-WilliamNeural",   # Male, Australian English
]
EDGE_TTS_RANDOMIZE = os.getenv("EDGE_TTS_RANDOMIZE", "true").lower() == "true"

SKIP_AUDIO_GENERATION = False  # Temporarily skip audio generation (set to False to enable)
TTS_VOICE = None  # Not used by Gemini/Edge-TTS, kept for compatibility
TTS_RATE = "+0%"  # Unused for Gemini/Edge-TTS, kept for compatibility
TTS_PITCH = "+0Hz"  # Unused for Gemini/Edge-TTS, kept for compatibility

# Subtitle fine-tuning
SUBTITLE_LEAD_SECONDS = float(os.getenv("SUBTITLE_LEAD_SECONDS", "-0.10"))  # Negative = delay (shift later), positive = lead (shift earlier)
SUBTITLE_DURATION_SCALE = float(os.getenv("SUBTITLE_DURATION_SCALE", "1.0"))  # 1.0 = no scaling, <1.0 = shorten, >1.0 = lengthen
SUBTITLE_MIN_DURATION = float(os.getenv("SUBTITLE_MIN_DURATION", "0.25"))

# Music Configuration
MUSIC_VOLUME = 0.3  # 30% volume for background music

# Output Configuration
OUTPUT_VIDEO_CODEC = "libx264"
OUTPUT_VIDEO_BITRATE = "5000k"
OUTPUT_AUDIO_CODEC = "aac"
OUTPUT_AUDIO_BITRATE = "192k"


def get_working_gemini_api_key():
    """
    Get a working Gemini API key by trying each key until one works.
    Returns the first key if no test is performed, or None if all keys fail.
    
    This function can be used to test keys, but for performance,
    you may want to cache the working key.
    """
    if not GEMINI_API_KEYS:
        return None
    
    # For now, just return the first key
    # The actual testing will happen in the code that uses it
    return GEMINI_API_KEYS[0]


def try_gemini_api_keys(func, *args, **kwargs):
    """
    Try executing a function with each Gemini API key until one succeeds.
    
    Args:
        func: A function that takes api_key as first argument (after *args)
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func (api_key will be overridden)
    
    Returns:
        The result of the first successful function call
    
    Raises:
        The last exception if all keys fail
    """
    if not GEMINI_API_KEYS:
        raise ValueError("No Gemini API keys configured. Set GEMINI_API_KEY in .env file.")
    
    last_exception = None
    for i, api_key in enumerate(GEMINI_API_KEYS):
        try:
            # Call function with api_key as first kwarg or positional
            if 'api_key' in kwargs:
                kwargs['api_key'] = api_key
                result = func(*args, **kwargs)
            else:
                # Try as first positional argument after *args
                result = func(*args, api_key, **kwargs)
            
            if i > 0:
                print(f"✓ Using Gemini API key #{i+1} (previous key(s) failed)")
            return result
        except Exception as e:
            last_exception = e
            error_msg = str(e).lower()
            # Check if it's an API key related error
            if any(keyword in error_msg for keyword in ['api', 'key', 'auth', 'permission', 'quota', 'invalid']):
                if i < len(GEMINI_API_KEYS) - 1:
                    print(f"⚠️  Gemini API key #{i+1} failed: {e}")
                    print(f"   Trying next key...")
                else:
                    print(f"⚠️  Gemini API key #{i+1} failed: {e}")
            else:
                # Not an API key error, re-raise immediately
                raise
    
    # All keys failed
    raise last_exception or ValueError("All Gemini API keys failed")

