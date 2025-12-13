"""
TTS Narration Module - Supports Gemini native TTS and Edge-TTS
"""
from pathlib import Path
from typing import Optional
import random
import wave

from .config import (
    TTS_PROVIDER, TTS_VOICE, TTS_RATE, TTS_PITCH, OUTPUT_DIR,
    GEMINI_API_KEY, GEMINI_API_KEYS, GEMINI_TTS_MODEL, GEMINI_TTS_VOICE_NAME, GEMINI_TTS_VOICES,
    GEMINI_TTS_RANDOMIZE, GEMINI_TTS_SAMPLE_RATE, GEMINI_TTS_STYLE_NOTE,
    EDGE_TTS_VOICE_NAME, EDGE_TTS_VOICES, EDGE_TTS_RANDOMIZE
)


class TTSGenerator:
    """Generates text-to-speech narration using Gemini or Edge-TTS."""

    def __init__(self, 
                 provider: Optional[str] = None,
                 voice: Optional[str] = None,
                 use_elevenlabs: Optional[bool] = None):
        # TTS providers do not return word timings; keep for API compatibility
        self.word_timings = []
        self.provider = (provider or TTS_PROVIDER).lower()
        self.voice = voice or TTS_VOICE  # kept for compatibility

        # Choose Gemini voice
        if self.provider == "gemini":
            if GEMINI_TTS_VOICE_NAME:
                self.gemini_voice = GEMINI_TTS_VOICE_NAME
            elif GEMINI_TTS_RANDOMIZE and GEMINI_TTS_VOICES:
                self.gemini_voice = random.choice(GEMINI_TTS_VOICES)
            elif GEMINI_TTS_VOICES:
                self.gemini_voice = GEMINI_TTS_VOICES[0]
            else:
                self.gemini_voice = "Kore"
        else:
            self.gemini_voice = "Kore"

        # Choose Edge-TTS voice
        if self.provider == "edge-tts":
            if EDGE_TTS_VOICE_NAME:
                self.edge_voice = EDGE_TTS_VOICE_NAME
            elif EDGE_TTS_RANDOMIZE and EDGE_TTS_VOICES:
                self.edge_voice = random.choice(EDGE_TTS_VOICES)
            elif EDGE_TTS_VOICES:
                self.edge_voice = EDGE_TTS_VOICES[0]
            else:
                self.edge_voice = "en-US-AriaNeural"
        else:
            self.edge_voice = "en-US-AriaNeural"

        # Provider availability checks
        if self.provider == "gemini":
            if not GEMINI_API_KEYS:
                raise ValueError("No Gemini API keys set. Set GEMINI_API_KEY in .env.")
        elif self.provider == "edge-tts":
            # Edge-TTS doesn't need API keys
            pass
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}. Use 'gemini' or 'edge-tts'.")

    def generate_audio(self, text: str, output_path: Optional[str] = None) -> str:
        """Generate TTS audio and return path."""
        if output_path is None:
            output_path = str(OUTPUT_DIR / "narration.wav")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Route to appropriate provider
        if self.provider == "gemini":
            # Prefer .wav because Gemini returns PCM
            if not output_path.lower().endswith(".wav"):
                output_path = str(Path(output_path).with_suffix(".wav"))
            return self._generate_gemini_tts(text, output_path)
        elif self.provider == "edge-tts":
            # Edge-TTS can output MP3 or WAV, default to MP3
            if not output_path.lower().endswith((".mp3", ".wav")):
                output_path = str(Path(output_path).with_suffix(".mp3"))
            return self._generate_edge_tts(text, output_path)
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}")

    def _generate_gemini_tts(self, text: str, output_path: str) -> str:
        """Generate audio via Gemini native TTS (PCM -> WAV) with multiple API key fallback."""
        if not GEMINI_API_KEYS:
            raise ValueError("No Gemini API keys configured. Set GEMINI_API_KEY in .env file.")

        # Ensure WAV output (Gemini returns raw PCM 16-bit mono 24k)
        if not output_path.lower().endswith(".wav"):
            output_path = str(Path(output_path).with_suffix(".wav"))

        try:
            from google import genai
            from google.genai import types
        except ImportError as e:
            raise ImportError("google-genai not installed. Install with: pip install google-genai") from e

        # Try each API key until one works
        last_exception = None
        for i, api_key in enumerate(GEMINI_API_KEYS):
            try:
                # Add style note to reduce breathing and lower pitch
                styled_text = f"{GEMINI_TTS_STYLE_NOTE} {text}"

                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=GEMINI_TTS_MODEL,
                    contents=[{"parts": [{"text": styled_text}]}],
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=self.gemini_voice
                                )
                            )
                        ),
                    ),
                )

                # Extract PCM from inline_data
                audio_bytes = None
                cand = response.candidates[0] if response.candidates else None
                parts = cand.content.parts if cand and cand.content else []
                for part in parts:
                    inline_data = getattr(part, "inline_data", None)
                    if inline_data and inline_data.data:
                        audio_bytes = inline_data.data
                        break

                if not audio_bytes:
                    raise RuntimeError("No audio content returned from Gemini.")

                # Write WAV (PCM 16-bit mono, sample rate from config)
                with wave.open(output_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(GEMINI_TTS_SAMPLE_RATE)
                    wf.writeframes(audio_bytes)

                self.word_timings = []  # No timings available yet
                if i > 0:
                    print(f"✓ Generated audio with Gemini TTS (using key #{i+1}) to {output_path}")
                else:
                    print(f"✓ Generated audio with Gemini TTS to {output_path}")
                return output_path

            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()
                # Check if it's an API key related error
                if any(keyword in error_msg for keyword in ['api', 'key', 'auth', 'permission', 'quota', 'invalid', 'forbidden']):
                    if i < len(GEMINI_API_KEYS) - 1:
                        print(f"⚠️  Gemini API key #{i+1} failed: {e}")
                        print(f"   Trying next key...")
                        continue
                    else:
                        print(f"⚠️  Gemini API key #{i+1} failed: {e}")
                else:
                    # Not an API key error, might be a different issue
                    # But we'll still try other keys in case it's a quota/permission issue
                    if i < len(GEMINI_API_KEYS) - 1:
                        print(f"⚠️  Gemini API key #{i+1} failed: {e}")
                        print(f"   Trying next key...")
                        continue
                    else:
                        # Last key failed, re-raise
                        raise

        # All keys failed
        raise RuntimeError(f"All Gemini API keys failed. Last error: {last_exception}")

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
    Main function to generate narration
    
    Args:
        text: Script to narrate
        output_path: Path to save audio file
        voice: Voice ID/name to use (optional override)
        provider: TTS provider to use ("gemini" or "edge-tts"), defaults to config
    
    Returns:
        (audio_path, word_timings)
    """
    generator = TTSGenerator(provider=provider, voice=voice)
    print(f"🎤 Using TTS provider: {generator.provider}")
    if generator.provider == "edge-tts":
        print(f"   Voice: {generator.edge_voice}")
    elif generator.provider == "gemini":
        print(f"   Voice: {generator.gemini_voice}")
    audio_path = generator.generate_audio(text, output_path)
    return audio_path, getattr(generator, 'word_timings', [])

