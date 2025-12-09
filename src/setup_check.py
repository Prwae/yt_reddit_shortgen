"""
Setup Verification Script - Checks if all dependencies and directories are set up correctly
"""
import sys
from pathlib import Path
import subprocess


def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required. Current version:", sys.version)
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True


def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'requests', 'beautifulsoup4', 'google.generativeai',
        'edge_tts', 'moviepy', 'PIL', 'pysrt', 'dotenv', 'numpy', 'cv2'
    ]
    
    missing = []
    for package in required_packages:
        try:
            if package == 'PIL':
                __import__('PIL')
            elif package == 'cv2':
                __import__('cv2')
            elif package == 'dotenv':
                __import__('dotenv')
            else:
                __import__(package)
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} not installed")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True


def check_ffmpeg():
    """Check if FFmpeg is installed"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg installed: {version_line}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    
    print("❌ FFmpeg not found. Install from https://ffmpeg.org/download.html")
    return False


def check_directories():
    """Check if required directories exist"""
    from .config import VIDEOS_DIR, BACKGROUNDS_DIR, MUSIC_DIR, INTRO_IMAGES_DIR, OUTPUT_DIR
    
    dirs = {
        'Videos': VIDEOS_DIR,
        'Backgrounds': BACKGROUNDS_DIR,
        'Music': MUSIC_DIR,
        'Intro Images': INTRO_IMAGES_DIR,
        'Output': OUTPUT_DIR
    }
    
    all_ok = True
    for name, path in dirs.items():
        if path.exists():
            print(f"✅ {name} directory: {path}")
        else:
            print(f"⚠️  {name} directory missing: {path}")
            path.mkdir(parents=True, exist_ok=True)
            print(f"   Created directory")
    
    return all_ok


def check_media_files():
    """Check if media files are present"""
    from .config import BACKGROUNDS_DIR, MUSIC_DIR
    
    # Check for multiple video formats
    video_extensions = ["*.mp4", "*.mov", "*.webm", "*.avi", "*.mkv", "*.flv", "*.wmv", "*.m4v"]
    bg_files = []
    for ext in video_extensions:
        bg_files.extend(list(BACKGROUNDS_DIR.glob(ext)))
        bg_files.extend(list(BACKGROUNDS_DIR.glob(ext.upper())))
    
    music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav")) + \
                  list(MUSIC_DIR.glob("*.MP3")) + list(MUSIC_DIR.glob("*.WAV"))
    
    if bg_files:
        print(f"✅ Found {len(bg_files)} background video(s)")
        # Show file types found
        file_types = set([Path(f).suffix.lower() for f in bg_files])
        print(f"   Formats: {', '.join(file_types)}")
    else:
        print(f"⚠️  No background videos found in {BACKGROUNDS_DIR}")
        print("   Add background video files (MP4, MOV, WEBM, AVI, MKV, etc.) to this directory")
    
    if music_files:
        print(f"✅ Found {len(music_files)} music file(s)")
    else:
        print(f"⚠️  No music files found in {MUSIC_DIR}")
        print("   Add music files (MP3, WAV) to this directory")
    
    return len(bg_files) > 0 and len(music_files) > 0


def check_api_keys():
    """Check if required API keys are set"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Check for multiple Gemini API keys
    from .config import GEMINI_API_KEYS
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
    tts_provider = os.getenv("TTS_PROVIDER", "elevenlabs")
    
    all_ok = True
    
    if GEMINI_API_KEYS:
        key_count = len(GEMINI_API_KEYS)
        if key_count == 1:
            print("✅ Gemini API key found")
        else:
            print(f"✅ Found {key_count} Gemini API keys (fallback enabled)")
            print("   Keys will be tried in order if one fails")
    else:
        print("❌ No Gemini API keys set")
        print("   Create a .env file with: GEMINI_API_KEY=your_key_here")
        print("   For multiple keys: GEMINI_API_KEY=key1,key2,key3")
        print("   Or use: GEMINI_API_KEY_1=key1, GEMINI_API_KEY_2=key2, etc.")
        print("   Get your key from: https://makersuite.google.com/app/apikey")
        all_ok = False
    
    if tts_provider == "elevenlabs":
        if elevenlabs_key:
            print("✅ ElevenLabs API key found")
        else:
            print("⚠️  ElevenLabs API key not set (using Edge TTS fallback)")
            print("   For better quality, add: ELEVENLABS_API_KEY=your_key_here")
            print("   Get your key from: https://elevenlabs.io/app/settings/api-keys")
    else:
        print("✅ Using Edge TTS (no API key needed)")
    
    return all_ok


def main():
    """Run all checks"""
    print("=" * 60)
    print("Reddit Reads Video Generator - Setup Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("FFmpeg", check_ffmpeg),
        ("Directories", check_directories),
        ("Media Files", check_media_files),
        ("API Keys", check_api_keys),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n[{name}]")
        print("-" * 40)
        result = check_func()
        results.append((name, result))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_passed = all(result for _, result in results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print()
    if all_passed:
        print("🎉 All checks passed! You're ready to generate videos.")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("\nQuick setup:")
        print("1. pip install -r requirements.txt")
        print("2. Install FFmpeg")
        print("3. Create .env file with GEMINI_API_KEY")
        print("4. Add background videos to videos/backgrounds/")
        print("5. Add music to videos/music/")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

