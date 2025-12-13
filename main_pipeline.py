"""
Main Pipeline Orchestrator - Coordinates all modules to create complete videos
"""
import json
import time
import traceback
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

from src.story_sourcing import fetch_story
from src.story_cache import get_avoid_ids, add_story_id
from src.intro_card import generate_intro_card
from src.tts_narration import generate_narration
from src.subtitles import generate_subtitles
from src.video_assembly import assemble_video
from src.metadata_generator import generate_metadata
from src.compliance import check_compliance
from src.config import (
    OUTPUT_DIR, BACKGROUNDS_DIR, MUSIC_DIR, INTRO_IMAGES_DIR, SKIP_AUDIO_GENERATION,
    FAST_RENDER_MODE, FAST_RENDER_PLACEHOLDER_TEXT, FAST_RENDER_PLACEHOLDER_TITLE
)


class VideoPipeline:
    """Main pipeline for generating Reddit Reads videos"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_video(self,
                      subreddits: Optional[list] = None,
                      background_video: Optional[str] = None,
                      music_file: Optional[str] = None,
                      intro_image: Optional[str] = None,
                      custom_story: Optional[Dict] = None) -> Dict:
        """
        Generate a complete Reddit Reads video
        
        Args:
            subreddits: List of subreddits to fetch from (optional)
            background_video: Path to background video (optional, will auto-select)
            music_file: Path to music file (optional)
            intro_image: Path to intro image template (optional)
            custom_story: Custom story dict to use instead of fetching (optional)
        
        Returns:
            Dict with paths to generated files and metadata
        """
        # Retry logic for TTS errors - try up to 3 different posts
        max_retries = 3
        failed_story_ids = []  # Track failed story IDs to avoid retrying them
        
        for attempt in range(max_retries):
            try:
                result = self._generate_video_internal(
                    subreddits=subreddits,
                    background_video=background_video,
                    music_file=music_file,
                    intro_image=intro_image,
                    custom_story=custom_story,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    avoid_story_ids=failed_story_ids
                )
                # Success! Return the result
                return result
            except Exception as e:
                error_msg = str(e).lower()
                # Check if it's any TTS-related error (not just speech generation)
                is_tts_error = False
                
                # Check if error originates from TTS module
                try:
                    tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                    if 'tts_narration' in tb_str.lower() or 'generate_narration' in tb_str.lower():
                        is_tts_error = True
                except:
                    pass
                
                # Also check error message for TTS-related keywords
                if not is_tts_error:
                    tts_keywords = [
                        'tts', 'text-to-speech', 'text to speech', 'narration',
                        'audio generation', 'generate audio', 'speech',
                        'no audio content', 'audio.*failed', 'narration.*failed',
                        'generate.*failed'
                    ]
                    is_tts_error = any(keyword in error_msg for keyword in tts_keywords)
                
                if is_tts_error and attempt < max_retries - 1:
                    # Try to extract story ID from the error or from the internal state
                    # We'll track it in the internal method
                    print(f"\n⚠️  TTS generation failed (attempt {attempt + 1}/{max_retries}): {e}")
                    print("   Retrying with a different post...")
                    time.sleep(2)  # Brief delay before retry
                    # Note: failed_story_ids will be populated by _generate_video_internal
                    continue
                else:
                    # Not a TTS error, or we've exhausted retries
                    raise
    
    def _generate_video_internal(self,
                                 subreddits: Optional[list] = None,
                                 background_video: Optional[str] = None,
                                 music_file: Optional[str] = None,
                                 intro_image: Optional[str] = None,
                                 custom_story: Optional[Dict] = None,
                                 attempt: int = 1,
                                 max_retries: int = 3,
                                 avoid_story_ids: Optional[list] = None) -> Dict:
        """
        Internal method to generate a video (called by generate_video with retry logic)
        """
        # Create output folder for this video
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_output_dir = self.output_dir / f"video_{timestamp}"
        video_output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Step 1: Fetch story (or use placeholder for fast render mode)
            if FAST_RENDER_MODE:
                print("⚡ FAST RENDER MODE: Using placeholder text for debugging...")
                story = {
                    'id': 'fast_render_placeholder',
                    'title': FAST_RENDER_PLACEHOLDER_TITLE,
                    'text': FAST_RENDER_PLACEHOLDER_TEXT,
                    'author': 'DebugMode',
                    'score': 999,
                    'subreddit': 'debug',
                    'url': 'https://debug.local'
                }
                print(f"✓ Using placeholder story: {story['title']}")
                word_count = len(story['text'].split())
                print(f"  Word count: {word_count} words")
            else:
                print("📖 Fetching story from Reddit...")
                if custom_story:
                    story = custom_story
                else:
                    # Get list of recently used story IDs to avoid duplicates
                    # Also avoid story IDs that failed TTS in previous retry attempts
                    avoid_ids = get_avoid_ids()
                    if avoid_story_ids:
                        avoid_ids = list(set(avoid_ids + avoid_story_ids))
                    story = fetch_story(subreddits, avoid_ids)
                
                if not story:
                    # Try one more time with a longer delay
                    print("⚠️  First attempt failed, retrying with longer delay...")
                    time.sleep(3)
                    story = fetch_story(subreddits, avoid_ids)
                    
                    if not story:
                        raise Exception(
                            "Failed to fetch story from Reddit. This might be due to:\n"
                            "- Rate limiting from Reddit (try again in a few minutes)\n"
                            "- Network connectivity issues\n"
                            "- All posts being filtered out (check MIN_STORY_WORDS, MAX_STORY_WORDS, MIN_UPVOTES in config.py)\n"
                            "- Reddit API changes or blocking"
                        )
                
                print(f"✓ Found story: {story['title'][:50]}...")
                print(f"  From r/{story.get('subreddit', 'unknown')} ({story.get('score', 0)} upvotes)")
                word_count = len(story['text'].split())
                print(f"  Word count: {word_count} words")
            
            # Step 2: Use story directly (no rewriting)
            print("📖 Using story directly (no rewriting)...")
            # Create script with title first, then story text
            title = story['title']
            story_text = story['text']
            # Prepend title to script so TTS reads it
            script = f"{title}. {story_text}"
            # Estimate duration based on word count (~2.5 words per second)
            total_word_count = len(script.split())
            duration_estimate = int(total_word_count / 2.5)
            print(f"✓ Story ready ({duration_estimate}s estimated, includes title)")
            
            # Create rewritten_story dict for compatibility with rest of pipeline
            rewritten_story = {
                'script': script,
                'subtitle_segments': None,  # Will be generated automatically
                'duration_estimate': duration_estimate,
                'original_title': story['title'],
                'original_author': story.get('author', 'Unknown')
            }
            
            # Step 3: Compliance check (simplified - just check story)
            print("🔍 Checking compliance...")
            is_compliant, issues = check_compliance(story, rewritten_story)
            if not is_compliant:
                print(f"⚠️ Compliance issues found: {issues}")
                print("Continuing anyway, but review recommended...")
            
            # Step 4: Generate intro card (uses user's avatar and nickname)
            print("🎨 Generating intro card...")
            intro_card_path = str(video_output_dir / "intro_card.png")
            generate_intro_card(
                title=story['title'],
                nickname=None,  # Will load from user's nickname file
                output_path=intro_card_path
            )
            print("✓ Intro card generated")
            
            # Step 5: Generate TTS narration (or skip if disabled)
            if SKIP_AUDIO_GENERATION:
                print("⏭️  Skipping audio generation (SKIP_AUDIO_GENERATION=True)")
                # Create a dummy audio file path and estimate duration
                narration_path = str(video_output_dir / "narration.mp3")
                # Estimate audio duration based on word count (~2.5 words per second)
                word_count = len(rewritten_story['script'].split())
                estimated_duration = word_count / 2.5  # Convert to seconds
                word_timings = []
                print(f"   Estimated duration: {estimated_duration:.1f} seconds")
            else:
                print("🎤 Generating narration...")
                narration_path = str(video_output_dir / "narration.mp3")
                try:
                    narration_path, word_timings = generate_narration(rewritten_story['script'], narration_path)
                    print("✓ Narration generated")
                    
                    # Only add story to cache after TTS succeeds
                    # This allows retries with different stories if TTS fails
                    if not FAST_RENDER_MODE and 'id' in story:
                        add_story_id(story['id'])
                except Exception as e:
                    error_msg = str(e).lower()
                    # Check if it's any TTS-related error (not just speech generation)
                    is_tts_error = False
                    
                    # Check if error originates from TTS module
                    try:
                        tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                        if 'tts_narration' in tb_str.lower() or 'generate_narration' in tb_str.lower():
                            is_tts_error = True
                    except:
                        pass
                    
                    # Also check error message for TTS-related keywords
                    if not is_tts_error:
                        tts_keywords = [
                            'tts', 'text-to-speech', 'text to speech', 'narration',
                            'audio generation', 'generate audio', 'speech',
                            'no audio content', 'audio.*failed', 'narration.*failed',
                            'generate.*failed'
                        ]
                        is_tts_error = any(keyword in error_msg for keyword in tts_keywords)
                    
                    if is_tts_error:
                        # Add this story ID to the avoid list for retries
                        if not FAST_RENDER_MODE and 'id' in story and avoid_story_ids is not None:
                            avoid_story_ids.append(story['id'])
                        # Re-raise as a specific exception that will trigger retry
                        raise RuntimeError(f"TTS generation failed: {e}")
                    else:
                        # Other errors, re-raise as-is
                        raise
            
            # Step 6: Generate subtitles
            print("📝 Generating subtitles...")
            if SKIP_AUDIO_GENERATION:
                # Use estimated duration for subtitles
                audio_duration = estimated_duration
            else:
                from moviepy.editor import AudioFileClip
                audio = AudioFileClip(narration_path)
                audio_duration = audio.duration
                audio.close()
            
            subtitles = generate_subtitles(
                rewritten_story['script'],
                audio_duration,
                rewritten_story.get('subtitle_segments'),
                str(video_output_dir / "subtitles.json"),
                word_timings=word_timings,
                audio_path=narration_path if not SKIP_AUDIO_GENERATION else None
            )
            print("✓ Subtitles generated")
            
            # Step 7: Assemble video
            print("🎬 Assembling video...")
            final_video_path = str(video_output_dir / "final_video.mp4")
            
            # Select background video
            if background_video and Path(background_video).exists():
                bg_video = background_video
            else:
                bg_video = None  # Will auto-select
            
            # Select music
            if music_file and Path(music_file).exists():
                music = music_file
            else:
                # Try to find any music file
                music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav"))
                music = str(music_files[0]) if music_files else None
            
            assemble_video(
                intro_card_path=intro_card_path,
                narration_audio_path=narration_path,
                subtitles=subtitles,
                background_video_path=bg_video,
                music_path=music,
                output_path=final_video_path
            )
            print("✓ Video assembled")
            
            # Step 8: Generate metadata
            print("📋 Generating metadata...")
            metadata = generate_metadata(story, rewritten_story)
            metadata_path = str(video_output_dir / "metadata.json")
            
            # Save complete metadata
            complete_metadata = {
                'title': metadata['title'],
                'description': metadata['description'],
                'hashtags': metadata['hashtags'],
                'tags': metadata['tags'],
                'original_story': {
                    'title': story['title'],
                    'subreddit': story.get('subreddit'),
                    'author': story.get('author'),
                    'url': story.get('url')
                },
                'video_path': final_video_path,
                'generated_at': timestamp
            }
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(complete_metadata, f, indent=2, ensure_ascii=False)
            
            print("✓ Metadata generated")
            
            print(f"\n✅ Video generation complete!")
            print(f"📁 Output directory: {video_output_dir}")
            print(f"🎥 Video: {final_video_path}")
            print(f"📋 Metadata: {metadata_path}")
            
            return {
                'success': True,
                'video_path': final_video_path,
                'metadata_path': metadata_path,
                'output_dir': str(video_output_dir),
                'metadata': complete_metadata
            }
        
        except Exception as e:
            print(f"\n❌ Error during video generation: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'output_dir': str(video_output_dir)
            }
    
    def batch_generate(self, count: int = 5, **kwargs) -> list:
        """
        Generate multiple videos in batch
        
        Args:
            count: Number of videos to generate
            **kwargs: Arguments to pass to generate_video()
        
        Returns:
            List of generation results
        """
        results = []
        for i in range(count):
            print(f"\n{'='*60}")
            print(f"Generating video {i+1}/{count}")
            print(f"{'='*60}\n")
            
            result = self.generate_video(**kwargs)
            results.append(result)
            
            if not result.get('success'):
                print(f"⚠️ Video {i+1} failed, continuing...")
        
        print(f"\n{'='*60}")
        print(f"Batch generation complete: {sum(1 for r in results if r.get('success'))}/{count} successful")
        print(f"{'='*60}")
        
        return results


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Reddit Reads YouTube videos")
    parser.add_argument('--count', type=int, default=1, help='Number of videos to generate')
    parser.add_argument('--subreddit', type=str, help='Specific subreddit to fetch from')
    parser.add_argument('--background', type=str, help='Path to background video')
    parser.add_argument('--music', type=str, help='Path to music file')
    parser.add_argument('--intro', type=str, help='Path to intro image')
    
    args = parser.parse_args()
    
    pipeline = VideoPipeline()
    
    subreddits = [args.subreddit] if args.subreddit else None
    
    if args.count > 1:
        pipeline.batch_generate(
            count=args.count,
            subreddits=subreddits,
            background_video=args.background,
            music_file=args.music,
            intro_image=args.intro
        )
    else:
        pipeline.generate_video(
            subreddits=subreddits,
            background_video=args.background,
            music_file=args.music,
            intro_image=args.intro
        )


if __name__ == "__main__":
    main()

