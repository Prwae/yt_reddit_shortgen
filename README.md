# Reddit Reads Video Generator

A fully automated system for creating short-form YouTube videos in the style of "Reddit Reads". This system fetches Reddit stories, generates narration using AI, creates subtitles, assembles complete videos, and can automatically upload to YouTube on a 24/7 schedule.

## Features

- 🔴 **Reddit Story Fetching**: Scrapes Reddit posts without API key
- 🎤 **AI Text-to-Speech**: Uses Google Gemini native TTS for natural narration
- 📝 **Automated Subtitles**: Word-timed subtitles with proper formatting
- 🎨 **Intro Card Generation**: Procedurally generates intro cards with avatar, nickname, and title
- 🎬 **Video Assembly**: Combines background footage, narration, subtitles, and music
- 📋 **Metadata Generation**: Creates YouTube titles, descriptions, and hashtags
- ✅ **Compliance Checking**: Ensures content meets YouTube guidelines
- 🔄 **Multiple API Key Support**: Automatic fallback if one Gemini API key fails
- ⬆️ **YouTube Auto-Upload**: Automated uploads with OAuth 2.0 authentication
- 🤖 **24/7 Scheduler**: Daily video generation and scheduled uploads

## System Requirements

- Python 3.8 or higher
- FFmpeg (required for video processing)
- Google Gemini API key(s) (for TTS and story processing)
- YouTube API credentials (optional, for auto-upload - see [YOUTUBE_SETUP.md](YOUTUBE_SETUP.md))

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg:**
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt-get install ffmpeg` (Ubuntu/Debian)

4. **Set up environment variables:**
   - Create a `.env` file in the project root
   - Add your API keys:
     ```
     # Gemini API keys (supports multiple keys for fallback)
     GEMINI_API_KEY=your_gemini_api_key_here
     # Or use multiple keys (comma-separated or numbered):
     # GEMINI_API_KEY=key1,key2,key3
     # GEMINI_API_KEY_1=key1
     # GEMINI_API_KEY_2=key2
     
     # TTS Provider (default: gemini)
     TTS_PROVIDER=gemini
     
     # YouTube upload settings (optional)
     YOUTUBE_PRIVACY_STATUS=private  # private, unlisted, or public
     YOUTUBE_CATEGORY_ID=22  # 22 = People & Blogs
     ```
   - Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - **Multiple API Keys**: The system supports multiple Gemini API keys with automatic fallback. If one key runs out of quota, it automatically tries the next one.

5. **Prepare your media files:**
   - Create a `videos/backgrounds/` folder and add background video files (MP4, MOV, WEBM, etc.)
   - Create a `videos/music/` folder and add background music files (MP3, WAV)
   - Create a `videos/avatar/` folder and add your avatar image (PNG, JPG)
   - Create a `videos/nickname.txt` file with your channel nickname
   - (Optional) Create a `videos/intro_images/` folder for custom intro images

6. **Set up YouTube upload (optional):**
   - Follow the guide in [YOUTUBE_SETUP.md](YOUTUBE_SETUP.md) to configure YouTube API credentials
   - Place `client_secrets.json` in the project root after setup

## Directory Structure

```
Autogen2/
├── main_pipeline.py          # Main video generation orchestrator
├── server_scheduler.py       # 24/7 scheduler for daily generation/upload
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── YOUTUBE_SETUP.md          # YouTube API setup guide
├── src/                      # Source code package
│   ├── __init__.py
│   ├── config.py            # Configuration settings
│   ├── story_sourcing.py    # Reddit story fetcher
│   ├── tts_narration.py     # Text-to-speech module (Gemini native TTS)
│   ├── subtitles.py         # Subtitle generator
│   ├── intro_card.py        # Intro card generator
│   ├── video_assembly.py    # Video assembly module
│   ├── metadata_generator.py # YouTube metadata generator
│   ├── compliance.py        # Content compliance checker
│   ├── youtube_uploader.py  # YouTube upload module
│   ├── story_cache.py       # Story ID cache to avoid duplicates
│   ├── setup_check.py       # Setup verification script
│   └── list_voices.py       # TTS voice listing utility
├── fonts/                    # Font files for subtitles/intro cards
│   ├── Qilka-Bold copy.otf
│   └── CuteOutline-Regular.ttf
├── videos/                   # User-provided media files
│   ├── backgrounds/         # Background video files
│   ├── music/               # Background music files
│   ├── avatar/              # Avatar image
│   ├── nickname.txt         # Channel nickname
│   └── intro_images/        # Custom intro images (optional)
├── output/                   # Generated videos (for manual runs)
└── daily_packs/              # Daily video packs (for scheduler)
    └── YYYYMMDD/            # Daily pack folders
```

## Usage

### Basic Usage

Generate a single video:

```bash
python main_pipeline.py
```

### Advanced Usage

Generate multiple videos:

```bash
python main_pipeline.py --count 5
```

Specify a subreddit:

```bash
python main_pipeline.py --subreddit AmItheAsshole
```

Use custom background video:

```bash
python main_pipeline.py --background path/to/video.mp4
```

Use custom music:

```bash
python main_pipeline.py --music path/to/music.mp3
```

### 24/7 Automated Operation

Run the server scheduler for automated daily generation and uploads:

```bash
python server_scheduler.py
```

The scheduler will:
- Generate videos daily until credits are exhausted
- Upload videos at evenly spaced intervals over 24 hours
- Keep only the last 3 days of packs
- Automatically retry failed uploads

See [YOUTUBE_SETUP.md](YOUTUBE_SETUP.md) for YouTube API setup instructions.

### Programmatic Usage

```python
from main_pipeline import VideoPipeline

pipeline = VideoPipeline()

# Generate a single video
result = pipeline.generate_video(
    subreddits=['AmItheAsshole', 'AskReddit'],
    background_video='path/to/background.mp4',
    music_file='path/to/music.mp3'
)

# Generate multiple videos
results = pipeline.batch_generate(count=5)
```

## How It Works

### 1. Story Sourcing
- Fetches posts from allowed subreddits (AITA, AskReddit, Confessions, etc.)
- Filters by upvotes, word count, and readability
- Tracks used story IDs to avoid duplicates
- **No API key required** - uses public Reddit JSON endpoints

### 2. TTS Narration
- Uses Google Gemini native TTS (preview) for natural narration
- Supports multiple voices (Sadaltager, Charon, Kore, Orus, Leda, Aoede)
- Falls back to HuggingFace TTS if Gemini unavailable
- Generates WAV audio files with proper timing

### 3. Intro Card Generation
- Procedurally generates intro cards with:
  - Rounded corner rectangle background
  - Circular avatar (from user's avatar folder or generated default)
  - Username/nickname (from `videos/nickname.txt`)
  - Post title with wrapping
  - Verified checkmark and award icons
  - Interaction buttons (upvotes, comments, share)
- Uses custom fonts from `fonts/` directory

### 4. Subtitle Generation
- Creates word-timed subtitles synchronized with audio
- High-contrast, readable formatting (white text, black outline)
- Center-positioned, 1-2 words per line
- Smooth animations and scaling effects
- Exports JSON format with timing data

### 5. Video Assembly
- **Uses only user-provided background footage** (no generation)
- Fits/crops to 9:16 aspect ratio (YouTube Shorts)
- Adds subtitles synchronized with narration
- Mixes in background music at 30% volume
- Creates intro sequence with animated intro card
- Speeds up video by 1.35x for optimal pacing
- Exports MP4 optimized for YouTube

### 6. Metadata Generation
- Creates viral-style titles
- Generates descriptions with disclaimers
- Adds relevant hashtags and tags
- Saves metadata as JSON for easy upload

### 7. YouTube Upload (Optional)
- Automated uploads using YouTube Data API v3
- OAuth 2.0 authentication with token storage
- Resumable uploads with retry logic
- Updates metadata files with YouTube video IDs
- Supports private, unlisted, or public uploads

### 8. Compliance Checking
- Checks for policy-violating content
- Identifies potential identifying information
- Ensures transformative content
- Flags issues for review

## Output

Each video generation creates a folder in `output/` (or `daily_packs/YYYYMMDD/` for scheduler) with:
- `final_video.mp4` - The complete video (9:16, ready for YouTube)
- `narration.wav` - The TTS audio file
- `intro_card.png` - The generated intro card
- `subtitles.json` - Subtitle data with timing
- `metadata.json` - Complete YouTube metadata (title, description, tags)

## Configuration

Edit `src/config.py` or set environment variables to customize:

### API Configuration
- `GEMINI_API_KEY` - Single key or comma-separated multiple keys
- `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, etc. - Numbered keys for fallback
- `TTS_PROVIDER` - "gemini" (default) or "huggingface"

### Video Configuration
- `VIDEO_WIDTH`, `VIDEO_HEIGHT` - Video dimensions (default: 1080x1920)
- `VIDEO_SPEED_MULTIPLIER` - Speed multiplier (default: 1.35x)
- `MAX_VIDEO_DURATION_SECONDS` - Maximum video length (default: 180s)

### Subtitle Configuration
- `SUBTITLE_FONT_SIZE` - Font size (default: 72)
- `SUBTITLE_WORDS_PER_LINE` - Max words per subtitle (default: 2)
- `SUBTITLE_POSITION` - Position on screen (default: "center")

### TTS Configuration
- `GEMINI_TTS_MODEL` - TTS model (default: "gemini-2.5-flash-preview-tts")
- `GEMINI_TTS_VOICE_NAME` - Specific voice to use (optional)
- `GEMINI_TTS_RANDOMIZE` - Randomize voice selection (default: true)
- `GEMINI_TTS_STYLE_NOTE` - Style instructions for TTS

### YouTube Upload Configuration
- `YOUTUBE_PRIVACY_STATUS` - "private", "unlisted", or "public"
- `YOUTUBE_CATEGORY_ID` - YouTube category ID (default: 22)

## Important Notes

### Background Footage
- **You must provide your own background videos**
- Place them in `videos/backgrounds/`
- System will automatically select and loop them
- Supported formats: MP4, MOV, WEBM, AVI, MKV, FLV, WMV, M4V
- System will crop/resize to 9:16 automatically

### Music
- **You must provide your own music files**
- Place them in `videos/music/`
- System will automatically select and mix at 30% volume
- Supports MP3 and WAV formats

### Multiple API Keys
- The system supports multiple Gemini API keys for redundancy
- If one key fails (quota exceeded, invalid, etc.), it automatically tries the next
- Configure multiple keys in `.env`:
  ```
  GEMINI_API_KEY=key1,key2,key3
  ```
  Or use numbered variables:
  ```
  GEMINI_API_KEY_1=key1
  GEMINI_API_KEY_2=key2
  GEMINI_API_KEY_3=key3
  ```

### Content Guidelines
- Stories are automatically filtered for compliance
- All identifying information is removed/altered
- Content is rewritten to be transformative
- Review compliance warnings before uploading

### API Usage
- Reddit scraping: No API key needed (uses public endpoints)
- Gemini API: Requires API key (free tier available)
- YouTube API: Requires OAuth credentials (see [YOUTUBE_SETUP.md](YOUTUBE_SETUP.md))

## Troubleshooting

### "No background videos found"
- Add video files to `videos/backgrounds/` folder
- Supported formats: MP4, MOV, WEBM, AVI, MKV, FLV, WMV, M4V
- Check that files have correct extensions (case-insensitive)

### "FFmpeg not found"
- Install FFmpeg and ensure it's in your system PATH
- Test with: `ffmpeg -version`

### "No Gemini API keys configured"
- Create a `.env` file with your Gemini API key
- Get key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- You can add multiple keys for fallback support

### "Gemini API key failed"
- If you have multiple keys configured, the system will automatically try the next one
- Check your API key validity and quota limits
- Ensure you have credits/quota available

### Video generation fails
- Check that background videos are valid
- Ensure audio files are not corrupted
- Check available disk space
- Review error messages in console

### TTS issues
- **Gemini TTS**: Check your API key and account credits
- **HuggingFace TTS**: Requires internet connection, check firewall settings
- To switch providers, set `TTS_PROVIDER=gemini` or `TTS_PROVIDER=huggingface` in `.env`
- List available Gemini voices: Check `src/config.py` for `GEMINI_TTS_VOICES`

### YouTube upload issues
- See [YOUTUBE_SETUP.md](YOUTUBE_SETUP.md) for detailed setup instructions
- Ensure `client_secrets.json` is in the project root
- Check that OAuth consent screen is configured correctly
- Verify YouTube Data API v3 is enabled in Google Cloud Console

### Server scheduler issues
- Ensure all API keys are configured correctly
- Check that media files (backgrounds, music) are available
- Verify YouTube credentials if using auto-upload
- Check disk space for daily packs

## Setup Verification

Run the setup check script to verify your installation:

```bash
python -m src.setup_check
```

This will check:
- Python version
- Installed dependencies
- FFmpeg installation
- Required directories
- Media files availability
- API keys configuration

## Scaling & Automation

The system supports:
- **Batch processing**: Generate multiple videos at once
- **Automatic story selection**: Picks best stories based on engagement
- **Background rotation**: Automatically rotates through available backgrounds
- **Error handling**: Continues processing even if individual videos fail
- **24/7 operation**: Server scheduler for automated daily generation and uploads
- **Multiple API keys**: Automatic fallback for redundancy
- **Resumable uploads**: YouTube uploads resume on failure

## License

This project is provided as-is for educational and personal use.

## Disclaimer

- Stories are sourced from public online forums and rewritten for entertainment
- All identifying information is removed or altered
- Content is for entertainment purposes only
- Users are responsible for ensuring compliance with YouTube's terms of service
- Users must have rights to use any background footage and music they provide

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review error messages in console output
3. Run `python -m src.setup_check` to verify setup
4. Ensure all dependencies are installed correctly
5. Verify media files are in correct formats and locations
6. Check [YOUTUBE_SETUP.md](YOUTUBE_SETUP.md) for YouTube-specific issues

---

**Ready to generate automated Reddit Reads videos!** ✅
