"""
TTS Narration Module - Edge-TTS (Microsoft Azure Neural Voices)
"""
from pathlib import Path
from typing import Optional
import random

from .config import (
    TTS_VOICE, TTS_RATE, TTS_PITCH, OUTPUT_DIR,
    EDGE_TTS_VOICE_NAME, EDGE_TTS_VOICES, EDGE_TTS_RANDOMIZE
)


class TTSGenerator:
    """Generates text-to-speech narration using Edge-TTS."""

    def __init__(self, 
                 provider: Optional[str] = None,
                 voice: Optional[str] = None,
                 use_elevenlabs: Optional[bool] = None):
        # Edge-TTS does not return word timings; keep for API compatibility
        self.word_timings = []
        self.voice = voice or TTS_VOICE  # kept for compatibility

        # Choose Edge-TTS voice
        if EDGE_TTS_VOICE_NAME:
            self.edge_voice = EDGE_TTS_VOICE_NAME
        elif EDGE_TTS_RANDOMIZE and EDGE_TTS_VOICES:
            self.edge_voice = random.choice(EDGE_TTS_VOICES)
        elif EDGE_TTS_VOICES:
            self.edge_voice = EDGE_TTS_VOICES[0]
        else:
            self.edge_voice = "en-US-AriaNeural"

    def generate_audio(self, text: str, output_path: Optional[str] = None) -> str:
        """Generate TTS audio and return path."""
        if output_path is None:
            output_path = str(OUTPUT_DIR / "narration.mp3")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Edge-TTS can output MP3 or WAV, default to MP3
        if not output_path.lower().endswith((".mp3", ".wav")):
            output_path = str(Path(output_path).with_suffix(".mp3"))
        
        return self._generate_edge_tts(text, output_path)

    def _generate_edge_tts(self, text: str, output_path: str) -> str:
        """Generate audio via Edge-TTS (Microsoft Azure Neural Voices)."""
        try:
            import edge_tts
        except ImportError as e:
            raise ImportError("edge-tts not installed. Install with: pip install edge-tts") from e

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            # Create Communicate object with text and voice
            communicate = edge_tts.Communicate(text, self.edge_voice)
            
            # Save synchronously (blocking)
            communicate.save_sync(output_path)
            
            self.word_timings = []  # No timings available from Edge-TTS
            print(f"✓ Generated audio with Edge-TTS (voice: {self.edge_voice}) to {output_path}")
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"Edge-TTS generation failed: {e}") from e


def generate_narration(text: str, 
                      output_path: Optional[str] = None, 
                      voice: Optional[str] = None,
                      provider: Optional[str] = None) -> tuple:
    """
    Main function to generate narration using Edge-TTS
    
    Args:
        text: Script to narrate
        output_path: Path to save audio file
        voice: Voice ID/name to use (optional override, ignored)
        provider: TTS provider (ignored, always uses Edge-TTS)
    
    Returns:
        (audio_path, word_timings)
    """
    generator = TTSGenerator(voice=voice)
    print(f"🎤 Using Edge-TTS")
    print(f"   Voice: {generator.edge_voice}")
    audio_path = generator.generate_audio(text, output_path)
    return audio_path, getattr(generator, 'word_timings', [])

