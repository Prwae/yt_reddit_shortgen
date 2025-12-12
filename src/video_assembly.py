"""
Visual Assembly Module - Assembles final video with background footage, subtitles, and music
"""
from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip,
    CompositeAudioClip, concatenate_videoclips
)
# Import speedx function for video speed adjustment
from moviepy.video.fx.all import speedx
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from pathlib import Path
import random
import os
from typing import Optional, List, Dict
from .config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, FPS, BACKGROUNDS_DIR, MUSIC_DIR,
    SUBTITLE_FONT_SIZE, SUBTITLE_FONT_COLOR, SUBTITLE_STROKE_COLOR,
    SUBTITLE_STROKE_WIDTH, SUBTITLE_POSITION, SUBTITLE_MARGIN,
    MUSIC_VOLUME, OUTPUT_VIDEO_CODEC, OUTPUT_VIDEO_BITRATE,
    OUTPUT_AUDIO_CODEC, OUTPUT_AUDIO_BITRATE, INTRO_DURATION,
    SUBTITLE_WORDS_PER_LINE, SUBTITLE_ANIMATION_DURATION,
    SUBTITLE_SCALE_START, SUBTITLE_SCALE_END, SUBTITLE_FONT_SIZE,
    VIDEO_SPEED_MULTIPLIER, BASE_DIR, MAX_VIDEO_DURATION_SECONDS, FONTS_DIR, OUTPUT_DIR
)


class VideoAssembler:
    """Assembles final video from components"""
    
    def __init__(self):
        self.video_width = VIDEO_WIDTH
        self.video_height = VIDEO_HEIGHT
        self.fps = FPS
    
    def assemble_video(self,
                      intro_card_path: str,
                      narration_audio_path: str,
                      subtitles: List[Dict],
                      background_video_path: Optional[str] = None,
                      music_path: Optional[str] = None,
                      output_path: Optional[str] = None) -> str:
        """
        Assemble complete video
        
        Args:
            intro_card_path: Path to intro card image
            narration_audio_path: Path to TTS audio file
            subtitles: List of subtitle dictionaries with timing
            background_video_path: Path to background video (optional, will auto-select if None)
            music_path: Path to background music (optional)
            output_path: Path to save final video
        
        Returns:
            Path to generated video
        """
        if output_path is None:
            output_path = str(Path(narration_audio_path).parent / "final_video.mp4")
        
        # Load narration audio (or create silent audio if file doesn't exist)
        if Path(narration_audio_path).exists():
            narration = AudioFileClip(narration_audio_path)
            audio_duration = narration.duration
        else:
            # Create silent audio if narration file doesn't exist
            print("⚠️  No narration audio file found, creating silent audio...")
            from moviepy.audio.AudioClip import AudioArrayClip
            import numpy as np
            # Create silent audio with estimated duration from subtitles
            if subtitles:
                audio_duration = subtitles[-1]['end'] if subtitles else 60.0
            else:
                audio_duration = 60.0  # Default 60 seconds
            # Create silent audio array
            sample_rate = 44100
            silent_audio = np.zeros((int(audio_duration * sample_rate), 2), dtype=np.float32)
            narration = AudioArrayClip(silent_audio, fps=sample_rate)
            print(f"   Created silent audio with duration: {audio_duration:.1f} seconds")
        
        # Create main content at ORIGINAL duration (before speed-up)
        # Subtitles are timed to original audio, so we use original duration
        if background_video_path is None:
            background_video_path = self._select_background_video()
        
        # Create video at original duration with original subtitle timings
        main_clip = self._create_main_content(
            background_video_path,
            narration,
            subtitles,  # Use original subtitle timings (not adjusted)
            music_path,
            intro_card_path,
            target_duration=audio_duration  # Use original audio duration
        )
        
        # Speed up video by VIDEO_SPEED_MULTIPLIER (this will also speed up subtitles automatically)
        final_video = main_clip.fx(speedx, VIDEO_SPEED_MULTIPLIER)
        
        # Speed up audio to match
        narration = narration.fx(speedx, VIDEO_SPEED_MULTIPLIER)
        
        # Calculate final duration after speed-up
        target_final_duration = audio_duration / VIDEO_SPEED_MULTIPLIER
        
        # Ensure final video duration matches sped-up audio duration exactly
        # Also enforce maximum duration of 3 minutes
        final_duration = min(final_video.duration, narration.duration, MAX_VIDEO_DURATION_SECONDS)
        final_video = final_video.subclip(0, final_duration)
        narration = narration.subclip(0, final_duration)
        
        # Set audio
        final_video = final_video.set_audio(narration)
        
        # Add music if provided
        if music_path and Path(music_path).exists():
            music = AudioFileClip(music_path)
            music = music.volumex(MUSIC_VOLUME)
            music = music.fx(speedx, VIDEO_SPEED_MULTIPLIER)  # Speed up music too
            music = music.subclip(0, min(music.duration, final_video.duration))
            final_audio = CompositeAudioClip([narration, music])
            final_video = final_video.set_audio(final_audio)
        
        # Write final video
        final_video.write_videofile(
            output_path,
            codec=OUTPUT_VIDEO_CODEC,
            bitrate=OUTPUT_VIDEO_BITRATE,
            audio_codec=OUTPUT_AUDIO_CODEC,
            audio_bitrate=OUTPUT_AUDIO_BITRATE,
            fps=self.fps,
            preset='medium'
        )
        
        # Cleanup
        narration.close()
        main_clip.close()
        final_video.close()
        if music_path and Path(music_path).exists():
            music.close()
        
        return output_path
    
    def _create_main_content(self,
                            background_video_path: str,
                            narration: AudioFileClip,
                            subtitles: List[Dict],
                            music_path: Optional[str] = None,
                            intro_card_path: Optional[str] = None,
                            target_duration: Optional[float] = None) -> CompositeVideoClip:
        """Create main content with background video, subtitles, and intro overlay"""
        # Use target_duration if provided (for final duration after speed-up), otherwise use narration duration
        content_duration = target_duration if target_duration is not None else narration.duration
        
        # Load background video
        bg_video = VideoFileClip(background_video_path)
        
        # Crop/resize to 9:16
        bg_video = self._fit_to_9_16(bg_video)
        
        # Pick random starting point and loop if needed to match target duration
        bg_video = self._prepare_background_video(bg_video, content_duration)
        bg_video = bg_video.set_fps(self.fps)
        
        # Create subtitle clips
        subtitle_clips = self._create_subtitle_clips(subtitles)
        
        # Create intro card overlay if provided
        intro_clip = None
        if intro_card_path and Path(intro_card_path).exists():
            intro_clip = self._create_intro_overlay(intro_card_path, content_duration)
        
        # Composite everything
        clips = [bg_video] + subtitle_clips
        if intro_clip:
            clips.append(intro_clip)
        
        main_content = CompositeVideoClip(clips, size=(self.video_width, self.video_height))
        # Set duration to exact target duration
        main_content = main_content.set_duration(content_duration)
        main_content = main_content.set_fps(self.fps)
        
        return main_content
    
    def _prepare_background_video(self, video: VideoFileClip, target_duration: float) -> VideoFileClip:
        """
        Pick random starting point and loop video if needed to match target duration
        """
        video_duration = video.duration
        
        # If video is longer than needed, pick random start point
        if video_duration > target_duration:
            max_start = video_duration - target_duration
            random_start = random.uniform(0, max_start)
            video = video.subclip(random_start, random_start + target_duration)
        else:
            # Video is shorter, loop it
            loops_needed = int(target_duration / video_duration) + 1
            video_loops = [video] * loops_needed
            video = concatenate_videoclips(video_loops)
            # Trim to exact duration
            video = video.subclip(0, target_duration)
        
        return video
    
    def _create_intro_overlay(self, intro_card_path: str, total_duration: float) -> ImageClip:
        """Create intro card overlay that appears above text (between text and top edge) with animations"""
        # Load intro card
        intro_card = ImageClip(intro_card_path)
        
        # Store original dimensions for animation
        original_width = intro_card.w
        original_height = intro_card.h
        
        # Resize to fit video width (maintain aspect ratio)
        # Card should be at most 90% of video width
        max_width = int(self.video_width * 0.9)
        card_ratio = original_width / original_height
        
        if original_width > max_width:
            # Resize to fit width
            target_width = max_width
            target_height = int(target_width / card_ratio)
        else:
            # Keep original size
            target_width = original_width
            target_height = original_height
        
        # Set duration (show intro for first few seconds)
        intro_duration = min(INTRO_DURATION, total_duration)
        
        # Animation parameters
        scale_in_duration = 0.8  # 0.8 seconds to enlarge
        fade_out_duration = 0.6  # 0.6 seconds to fade out
        
        # Scale animation: slowly enlarge from 0.7 to 1.0
        def get_scale(t):
            if t < scale_in_duration:
                # Scale from 0.7 to 1.0 during scale-in
                progress = t / scale_in_duration
                # Ease-out curve for smooth enlargement
                ease_progress = 1 - (1 - progress) ** 3
                return 0.7 + (0.3 * ease_progress)
            else:
                # Full size after scale-in
                return 1.0
        
        # Apply scale animation - preserve aspect ratio by scaling both dimensions equally
        def resize_func(t):
            scale = get_scale(t)
            # Simply scale both dimensions by the same factor - this preserves aspect ratio perfectly
            w = max(1, int(target_width * scale))
            h = max(1, int(target_height * scale))
            return (w, h)
        
        intro_card = intro_card.resize(resize_func)
        
        # Position above text (between text and top edge)
        # Center horizontally, position closer to text (center) than to top edge
        def position_func(t):
            scale = get_scale(t)
            current_width = max(1, int(target_width * scale))
            current_height = max(1, int(target_height * scale))
            x_center = (self.video_width - current_width) // 2
            # Position closer to top to avoid overlapping subtitles
            # Previously 40% of distance to center; raise it to create more gap
            center_y = self.video_height // 2
            y_position = int(center_y * 0.4)  # 30% of the way from top to center
            return (x_center, y_position)
        
        intro_card = intro_card.set_position(position_func)
        
        # Set duration and fps FIRST (required before fadeout)
        intro_card = intro_card.set_duration(intro_duration)
        intro_card = intro_card.set_fps(self.fps)
        
        # Apply fade out animation using fadeout method
        # fadeout expects duration to be set first
        if fade_out_duration > 0 and intro_duration > fade_out_duration:
            # Fade out over the last fade_out_duration seconds
            intro_card = intro_card.fadeout(fade_out_duration)
        
        return intro_card
    
    def _fit_to_9_16(self, video: VideoFileClip) -> VideoFileClip:
        """Fit video to 9:16 aspect ratio"""
        target_ratio = self.video_width / self.video_height  # 9:16 = 0.5625
        video_ratio = video.w / video.h
        
        if abs(video_ratio - target_ratio) < 0.01:
            # Already correct ratio, just resize
            return video.resize((self.video_width, self.video_height))
        elif video_ratio > target_ratio:
            # Video is wider, crop sides
            new_width = int(video.h * target_ratio)
            x_center = video.w / 2
            return video.crop(x_center=x_center, width=new_width).resize((self.video_width, self.video_height))
        else:
            # Video is taller, crop top/bottom
            new_height = int(video.w / target_ratio)
            y_center = video.h / 2
            return video.crop(y_center=y_center, height=new_height).resize((self.video_width, self.video_height))
    
    def _create_subtitle_clips(self, subtitles: List[Dict]) -> List[ImageClip]:
        """Create subtitle text clips using PIL (no ImageMagick required)"""
        subtitle_clips = []
        
        for subtitle in subtitles:
            try:
                # Create subtitle image using PIL
                subtitle_img = self._create_subtitle_image(subtitle['text'])
                
                # Use natural image dimensions BEFORE creating clip
                natural_width = subtitle_img.width
                natural_height = subtitle_img.height
                
                # Debug: Print dimensions to verify they're different for each subtitle
                print(f"DEBUG: Subtitle '{subtitle['text'][:30]}...' - Image width: {natural_width}, height: {natural_height}")
                
                # Save image temporarily to verify dimensions (debug only - can remove later)
                # debug_path = Path(__file__).parent / f"debug_subtitle_{len(subtitle_clips)}.png"
                # subtitle_img.save(debug_path)
                
                # Convert PIL image to numpy array for MoviePy
                # IMPORTANT: Array shape is (height, width, channels) - MoviePy reads this correctly
                img_array = np.array(subtitle_img)
                
                # Verify array shape matches our expectations
                if len(img_array.shape) == 3:
                    array_height, array_width, channels = img_array.shape
                    if array_width != natural_width or array_height != natural_height:
                        print(f"WARNING: Array dimensions don't match! Expected ({natural_height}, {natural_width}), got ({array_height}, {array_width})")
                
                # Create ImageClip from array - NO RESIZE, use image exactly as-is
                text_clip = ImageClip(img_array)
                
                # Set timing
                start_time = subtitle['start']
                duration = subtitle['end'] - subtitle['start']
                text_clip = text_clip.set_start(start_time)
                text_clip = text_clip.set_duration(duration)
                text_clip = text_clip.set_fps(self.fps)
                
                # Position in center - simple, no animation, no resizing, just paste the image
                center_x = self.video_width // 2
                center_y = self.video_height // 2
                x = center_x - text_clip.w // 2
                y = center_y - text_clip.h // 2
                
                text_clip = text_clip.set_position((x, y))
                
                subtitle_clips.append(text_clip)
            except Exception as e:
                print(f"Error creating subtitle clip: {e}")
                print(f"  Subtitle text: {subtitle['text'][:50]}...")
                continue
        
        return subtitle_clips
    
    def _create_subtitle_image(self, text: str) -> Image.Image:
        """Create a subtitle image using PIL with bubbly font (preserves aspect ratio, NO STRETCHING)"""
        # Ensure single word (one word per subtitle)
        words = text.split()
        if len(words) > SUBTITLE_WORDS_PER_LINE:
            text = words[0]  # Take only the first word
        
        # Load bubbly font (Comic Sans or similar rounded font)
        font = self._get_bubbly_font(SUBTITLE_FONT_SIZE)
        
        # Create temporary image to measure text - use large canvas for accurate measurement
        temp_img = Image.new('RGB', (2000, 2000))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Calculate image dimensions with padding - use EXACT text dimensions
        # Each subtitle gets its own natural width based on text content - NO FORCED WIDTH
        padding = 40
        img_width = text_width + padding * 2
        img_height = text_height + padding * 2
        
        # Ensure minimum dimensions
        img_width = max(img_width, 1)
        img_height = max(img_height, 1)
        
        # DO NOT force width - each subtitle should have its natural width
        
        # Create transparent background
        img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Center text in image
        x_pos = padding
        y_pos = padding
        
        # Draw stroke (outline) - draw multiple times for thickness to create visible outline
        # Draw outline first (behind the text) - this creates a black border around the text
        for adj in range(-SUBTITLE_STROKE_WIDTH, SUBTITLE_STROKE_WIDTH + 1):
            for adj2 in range(-SUBTITLE_STROKE_WIDTH, SUBTITLE_STROKE_WIDTH + 1):
                if adj != 0 or adj2 != 0:
                    draw.text(
                        (x_pos + adj, y_pos + adj2),
                        text,
                        font=font,
                        fill=SUBTITLE_STROKE_COLOR + (255,)  # Black outline
                    )
        
        # Draw main text on top (NO STRETCHING - uses natural font rendering, preserves aspect ratio)
        draw.text(
            (x_pos, y_pos),
            text,
            font=font,
            fill=SUBTITLE_FONT_COLOR + (255,)  # White text
        )
        
        return img
    
    def _get_bubbly_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Get a bubbly/rounded font - Qilka-Bold"""
        # Get username for user directories
        username = os.getenv("USERNAME", os.getenv("USER", ""))
        
        # Try Qilka-Bold first (user's new font in fonts folder)
        font_paths = [
            # Qilka-Bold (primary choice) - in fonts folder
            str(FONTS_DIR / "Qilka-Bold copy.otf"),
            str(FONTS_DIR / "Qilka-Bold copy.OTF"),
            str(FONTS_DIR / "qilka-bold copy.otf"),
            str(FONTS_DIR / "Qilka-Bold.otf"),
            str(FONTS_DIR / "qilka-bold.otf"),
            str(FONTS_DIR / "Qilka-Bold.ttf"),
            str(FONTS_DIR / "qilka-bold.ttf"),
            # CuteOutline-Regular (fallback) - in fonts folder
            str(FONTS_DIR / "CuteOutline-Regular.ttf"),
            str(FONTS_DIR / "CuteOutline-Regular.otf"),
            str(FONTS_DIR / "cuteoutline-regular.ttf"),
            str(FONTS_DIR / "cuteoutline-regular.otf"),
            str(FONTS_DIR / "CUTEOUTLINE-REGULAR.TTF"),
            str(FONTS_DIR / "CUTEOUTLINE-REGULAR.OTF"),
            f"C:/Users/{username}/Downloads/outline bubble regular.ttf",
            f"C:/Users/{username}/Downloads/OUTLINE BUBBLE REGULAR.TTF",
            f"C:/Users/{username}/Downloads/OutlineBubble-Regular.ttf",
            f"C:/Users/{username}/Downloads/outlinebubble-regular.ttf",
            f"C:/Users/{username}/Downloads/OutlineBubbleRegular.ttf",
            f"C:/Users/{username}/Downloads/outlinebubbleregular.ttf",
            f"C:/Users/{username}/Downloads/Outline Bubble.ttf",
            f"C:/Users/{username}/Downloads/outline bubble.ttf",
            f"C:/Users/{username}/Downloads/OutlineBubble.ttf",
            # Try Windows Fonts directory
            "C:/Windows/Fonts/Outline Bubble Regular.ttf",
            "C:/Windows/Fonts/outline bubble regular.ttf",
            "C:/Windows/Fonts/OUTLINE BUBBLE REGULAR.TTF",
            "C:/Windows/Fonts/OutlineBubble-Regular.ttf",
            "C:/Windows/Fonts/outlinebubble-regular.ttf",
            "C:/Windows/Fonts/OutlineBubbleRegular.ttf",
            "C:/Windows/Fonts/outlinebubbleregular.ttf",
            "C:/Windows/Fonts/Outline Bubble.ttf",
            "C:/Windows/Fonts/outline bubble.ttf",
            "C:/Windows/Fonts/OutlineBubble.ttf",
            # Try in user fonts directory
            f"C:/Users/{username}/AppData/Local/Microsoft/Windows/Fonts/Outline Bubble Regular.ttf",
            f"C:/Users/{username}/AppData/Local/Microsoft/Windows/Fonts/outline bubble regular.ttf",
            f"C:/Users/{username}/AppData/Local/Microsoft/Windows/Fonts/OutlineBubble-Regular.ttf",
            f"C:/Users/{username}/AppData/Local/Microsoft/Windows/Fonts/OutlineBubbleRegular.ttf",
            # Arial Rounded MT Bold (fallback - very bubbly, professional)
            "C:/Windows/Fonts/ARLRDBD.TTF",  # Arial Rounded MT Bold
            "C:/Windows/Fonts/ARLRDBD.ttf",
            "C:/Windows/Fonts/arial rounded mt bold.ttf",
            "C:/Windows/Fonts/Arial Rounded MT Bold.ttf",
            # Segoe UI (modern, slightly rounded)
            "C:/Windows/Fonts/segoeui.ttf",  # Segoe UI
            "C:/Windows/Fonts/segoeuib.ttf",  # Segoe UI Bold
            "C:/Windows/Fonts/segoeuil.ttf",  # Segoe UI Light
            # Century Gothic (rounded, elegant)
            "C:/Windows/Fonts/GOTHIC.TTF",  # Century Gothic
            "C:/Windows/Fonts/GOTHICB.TTF",  # Century Gothic Bold
            "C:/Windows/Fonts/gothic.ttf",
            "C:/Windows/Fonts/gothicb.ttf",
            # Verdana (rounded, readable)
            "C:/Windows/Fonts/verdana.ttf",  # Verdana
            "C:/Windows/Fonts/verdanab.ttf",  # Verdana Bold
            "C:/Windows/Fonts/VERDANA.TTF",
            "C:/Windows/Fonts/VERDANAB.TTF",
            # Tahoma (rounded)
            "C:/Windows/Fonts/tahoma.ttf",  # Tahoma
            "C:/Windows/Fonts/tahomabd.ttf",  # Tahoma Bold
            "C:/Windows/Fonts/TAHOMA.TTF",
            # Trebuchet MS (rounded, modern)
            "C:/Windows/Fonts/trebuc.ttf",  # Trebuchet MS
            "C:/Windows/Fonts/trebucbd.ttf",  # Trebuchet MS Bold
            "C:/Windows/Fonts/TREBUC.TTF",
            # Calibri (rounded, modern)
            "C:/Windows/Fonts/calibri.ttf",  # Calibri
            "C:/Windows/Fonts/calibrib.ttf",  # Calibri Bold
            "C:/Windows/Fonts/CALIBRI.TTF",
            # Fallback to Comic Sans if nothing else works
            "C:/Windows/Fonts/comic.ttf",  # Comic Sans MS
            "C:/Windows/Fonts/comicbd.ttf",  # Comic Sans MS Bold
            "C:/Windows/Fonts/Comic Sans MS.ttf",
            "/System/Library/Fonts/Supplemental/Comic Sans MS.ttf",  # macOS
            "/usr/share/fonts/truetype/comic/ComicSansMS.ttf",  # Linux
        ]
        
        for font_path in font_paths:
            try:
                if Path(font_path).exists():
                    return ImageFont.truetype(font_path, size)
            except:
                continue
        
        # Last resort: use default but make it bold
        try:
            return ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", size)
        except:
            return ImageFont.load_default()
    
    def _select_background_video(self) -> str:
        """Select a random background video from backgrounds directory"""
        # Support multiple video formats
        video_extensions = ["*.mp4", "*.mov", "*.webm", "*.avi", "*.mkv", "*.flv", "*.wmv", "*.m4v"]
        bg_files = []
        
        for ext in video_extensions:
            bg_files.extend(list(BACKGROUNDS_DIR.glob(ext)))
            # Also check case-insensitive
            bg_files.extend(list(BACKGROUNDS_DIR.glob(ext.upper())))
        
        if not bg_files:
            raise FileNotFoundError(
                f"No background videos found in {BACKGROUNDS_DIR}. "
                "Please add background video files (MP4, MOV, WEBM, AVI, MKV, etc.) to this directory."
            )
        
        return str(random.choice(bg_files))
    
    def _create_black_frame(self) -> str:
        """Create a black frame image for background"""
        from PIL import Image
        frame_path = str(OUTPUT_DIR / "temp_black_frame.png")
        img = Image.new('RGB', (self.video_width, self.video_height), (0, 0, 0))
        img.save(frame_path)
        return frame_path


def assemble_video(intro_card_path: str,
                  narration_audio_path: str,
                  subtitles: List[Dict],
                  background_video_path: Optional[str] = None,
                  music_path: Optional[str] = None,
                  output_path: Optional[str] = None) -> str:
    """
    Main function to assemble video
    """
    assembler = VideoAssembler()
    return assembler.assemble_video(
        intro_card_path,
        narration_audio_path,
        subtitles,
        background_video_path,
        music_path,
        output_path
    )

