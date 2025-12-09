# Reddit Reads Video Generator

A fully automated system for creating short-form YouTube videos in the style of "Reddit Reads". This system fetches Reddit stories, rewrites them using AI, generates narration, creates subtitles, and assembles complete videos with your provided background footage and music.

## Features

- 🔴 **Reddit Story Fetching**: Scrapes Reddit posts without API key
- ✍️ **AI Story Rewriting**: Uses Google Gemini API to transform stories into 25-50 second scripts
- 🎤 **Text-to-Speech**: Natural human-like narration using ElevenLabs (with Edge TTS fallback)
- 📝 **Automated Subtitles**: Word-timed subtitles with proper formatting
- 🎨 **Intro Card Generation**: Procedurally generates intro cards with avatar, nickname, and title
- 🎬 **Video Assembly**: Combines background footage, narration, subtitles, and music
- 📋 **Metadata Generation**: Creates YouTube titles, descriptions, and hashtags
- ✅ **Compliance Checking**: Ensures content meets YouTube guidelines

## System Requirements

- Python 3.8 or higher
- FFmpeg (required for video processing)
- Google Gemini API key (for story rewriting)
- ElevenLabs API key (recommended for high-quality TTS, or use free Edge TTS fallback)

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
   - Copy `.env.example` to `.env` (if it exists) or create a `.env` file
   - Add your API keys:
     ```
     GEMINI_API_KEY=your_gemini_api_key_here
     ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
     TTS_PROVIDER=elevenlabs
     ```
   - Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Get your ElevenLabs API key from [ElevenLabs](https://elevenlabs.io/app/settings/api-keys)
   - **Note**: If you don't set `ELEVENLABS_API_KEY`, the system will automatically use Edge TTS (free, no API key needed)

5. **Prepare your media files:**
   - Create a `videos/backgrounds/` folder and add background video files (MP4, MOV)
   - Create a `videos/music/` folder and add background music files (MP3, WAV)
   - (Optional) Create a `videos/intro_images/` folder for custom intro images

## Directory Structure

```
Autogen2/
├── story_sourcing.py      # Reddit story fetcher
├── story_rewrite.py       # Gemini-based story rewriter
├── intro_card.py          # Intro card generator
├── tts_narration.py       # Text-to-speech module
├── subtitles.py           # Subtitle generator
├── video_assembly.py      # Video assembly module
├── metadata_generator.py  # YouTube metadata generator
├── compliance.py          # Content compliance checker
├── main_pipeline.py       # Main orchestrator
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── videos/
│   ├── backgrounds/       # Background video files (user-provided)
│   ├── music/            # Background music files (user-provided)
│   └── intro_images/     # Intro image templates (optional)
└── output/                # Generated videos and files
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

Combine options:

```bash
python main_pipeline.py --count 3 --subreddit AskReddit --background bg.mp4 --music track.mp3
```

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
- Filters by upvotes, emotional intensity, and readability
- Cleans formatting and identifies hooks
- **No API key required** - uses public Reddit JSON endpoints

### 2. Story Rewriting
- Uses Google Gemini API to transform stories
- Creates 25-50 second scripts with strong hooks
- Ensures clear story structure (beginning → conflict → climax → resolution)
- Removes identifying details and policy-violating content

### 3. Intro Card Generation
- Procedurally generates intro cards with:
  - Rounded corner rectangle background
  - Circular avatar (from Reddit or generated default)
  - Username/nickname
  - Post title
- Can use custom intro images if provided

### 4. TTS Narration
- Uses Edge TTS for natural, human-like voices
- Calm but engaging pacing
- Optimized for short-form viewing
- Exports MP3 audio ready for video sync

### 5. Subtitle Generation
- Creates word-timed subtitles (SRT or JSON format)
- High-contrast, readable formatting
- Safe-zone placement (1-2 lines max)
- Auto-splits long sentences

### 6. Video Assembly
- **Uses only user-provided background footage** (no generation)
- Fits/crops to 9:16 aspect ratio (YouTube Shorts)
- Adds subtitles synchronized with narration
- Mixes in background music at appropriate volume
- Creates intro sequence with intro card
- Exports MP4 optimized for YouTube

### 7. Metadata Generation
- Creates viral-style titles
- Generates descriptions with disclaimers
- Adds relevant hashtags and tags
- Saves metadata as JSON for easy upload

### 8. Compliance Checking
- Checks for policy-violating content
- Identifies potential identifying information
- Ensures transformative content
- Flags issues for review

## Output

Each video generation creates a folder in `output/` with:
- `final_video.mp4` - The complete video (9:16, ready for YouTube)
- `narration.mp3` - The TTS audio file
- `intro_card.png` - The generated intro card
- `subtitles.json` - Subtitle data with timing
- `metadata.json` - Complete YouTube metadata (title, description, tags)

## Configuration

Edit `config.py` to customize:
- Video dimensions and FPS
- Subtitle styling (font, size, position)
- TTS voice and settings
- Music volume
- Allowed subreddits
- Story filtering criteria

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

### Content Guidelines
- Stories are automatically filtered for compliance
- All identifying information is removed/altered
- Content is rewritten to be transformative
- Review compliance warnings before uploading

### API Usage
- Reddit scraping: No API key needed (uses public endpoints)
- Gemini API: Requires API key (free tier available)
- ElevenLabs TTS: Requires API key (paid, but highest quality) - [Get API key](https://elevenlabs.io/app/settings/api-keys)
- Edge TTS: Free fallback, no API key needed (automatically used if ElevenLabs unavailable)

## Troubleshooting

### "No background videos found"
- Add video files to `videos/backgrounds/` folder
- Supported formats: MP4, MOV, WEBM, AVI, MKV, FLV, WMV, M4V
- Check that files have correct extensions (case-insensitive)

### "FFmpeg not found"
- Install FFmpeg and ensure it's in your system PATH
- Test with: `ffmpeg -version`

### "GEMINI_API_KEY not set"
- Create a `.env` file with your Gemini API key
- Get key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### Video generation fails
- Check that background videos are valid
- Ensure audio files are not corrupted
- Check available disk space
- Review error messages in console

### TTS issues
- **ElevenLabs**: Check your API key and account credits
- **Edge TTS**: Requires internet connection, check firewall settings
- To switch providers, set `TTS_PROVIDER=elevenlabs` or `TTS_PROVIDER=edge` in `.env`
- To use a different ElevenLabs voice, set `ELEVENLABS_VOICE_ID` in `.env` or `config.py`
- **Popular natural female voices**:
  - ElevenLabs: `EXAVITQu4vr4xnSDxMaL` (Bella - very natural), `ThT5KcBeYPX3keUQqHPh` (Domi - expressive)
  - Edge TTS: `en-US-JennyNeural` (very natural), `en-GB-SoniaNeural` (British)
- List available voices: Run `python list_voices.py` to see all available options
- **Voice sounds robotic?** Try lowering `ELEVENLABS_STABILITY` (e.g., 0.3-0.4) in `config.py` for more natural variation

## Scaling & Automation

The system supports:
- **Batch processing**: Generate multiple videos at once
- **Automatic story selection**: Picks best stories based on engagement
- **Background rotation**: Automatically rotates through available backgrounds
- **Error handling**: Continues processing even if individual videos fail
- **Multi-language**: Can be extended for other languages (change TTS voice)

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
3. Ensure all dependencies are installed correctly
4. Verify media files are in correct formats and locations

---

**Generate the complete automated project blueprint now.** ✅

