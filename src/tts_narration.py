"""
TTS Narration Module - Gemini native TTS (preview) with HuggingFace fallback
"""
from pathlib import Path
from typing import Optional
import random
import base64
import wave
import requests

from .config import (
    TTS_PROVIDER, TTS_VOICE, TTS_RATE, TTS_PITCH, OUTPUT_DIR,
    GEMINI_API_KEY, GEMINI_API_KEYS, GEMINI_TTS_MODEL, GEMINI_TTS_VOICE_NAME, GEMINI_TTS_VOICES,
    GEMINI_TTS_RANDOMIZE, GEMINI_TTS_SAMPLE_RATE, GEMINI_TTS_STYLE_NOTE,
    HUGGINGFACE_TTS_URL
)


class TTSGenerator:
    """Generates text-to-speech narration using Gemini (default) or HuggingFace fallback."""

    def __init__(self, 
                 provider: Optional[str] = None,
                 voice: Optional[str] = None,
                 use_elevenlabs: Optional[bool] = None):
        # Gemini/HF do not return word timings; keep for API compatibility
        self.word_timings = []
        self.provider = provider or TTS_PROVIDER
        self.voice = voice or TTS_VOICE  # not used by Gemini/HF, but kept

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

        # Provider availability checks and fallbacks
        if self.provider == "gemini" and not GEMINI_API_KEYS:
            print("⚠️  No Gemini API keys set. Falling back to HuggingFace TTS.")
            self.provider = "huggingface"
        if self.provider == "huggingface" and not HUGGINGFACE_TTS_URL:
            raise ValueError("HUGGINGFACE_TTS_URL not configured.")

    def generate_audio(self, text: str, output_path: Optional[str] = None) -> str:
        """Generate TTS audio and return path."""
        if output_path is None:
            output_path = str(OUTPUT_DIR / "narration.wav")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        # Prefer .wav because Gemini returns PCM
        if not output_path.lower().endswith(".wav"):
            output_path = str(Path(output_path).with_suffix(".wav"))

        if self.provider == "gemini":
            return self._generate_gemini_tts(text, output_path)
        if self.provider == "huggingface":
            return self._generate_huggingface_tts(text, output_path)

        # Default to Gemini if an unknown provider is passed
        return self._generate_gemini_tts(text, output_path)

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
        print(f"⚠️  All Gemini API keys failed. Last error: {last_exception}")
        print("   Falling back to HuggingFace TTS.")
        self.provider = "huggingface"
        return self._generate_huggingface_tts(text, output_path)

    def _extract_audio_bytes_from_hf(self, data_item):
        """Attempt to extract audio bytes from a HuggingFace Space response item."""
        content = None
        if isinstance(data_item, dict):
            content = data_item.get("data") or data_item.get("url")
        elif isinstance(data_item, str):
            content = data_item

        if not content:
            return None

        # data:audio/wav;base64,...
        if isinstance(content, str) and content.startswith("data:audio"):
            try:
                b64_part = content.split(",", 1)[1]
                return base64.b64decode(b64_part)
            except Exception:
                return None

        # raw base64
        if isinstance(content, str):
            try:
                return base64.b64decode(content)
            except Exception:
                return None

        return None

    def _generate_huggingface_tts(self, text: str, output_path: str) -> str:
        """Generate audio via HuggingFace Space fallback."""
        if not HUGGINGFACE_TTS_URL:
            raise ValueError("HUGGINGFACE_TTS_URL not configured.")

        api_url = HUGGINGFACE_TTS_URL.rstrip("/") + "/api/predict"
        payload = {"data": [text]}

        try:
            resp = requests.post(api_url, json=payload, timeout=180)
            resp.raise_for_status()
            resp_json = resp.json()

            audio_bytes = None
            if isinstance(resp_json, dict) and "data" in resp_json:
                for item in resp_json["data"]:
                    audio_bytes = self._extract_audio_bytes_from_hf(item)
                    if audio_bytes:
                        break

            if not audio_bytes:
                raise RuntimeError(f"HuggingFace TTS returned no audio. Response keys: {list(resp_json.keys())}")

            with open(output_path, "wb") as f:
                f.write(audio_bytes)

            self.word_timings = []  # No timings available
            print("✓ Generated audio with HuggingFace TTS (no word timings provided)")
            return output_path

        except Exception as e:
            raise RuntimeError(f"HuggingFace TTS failed: {e}")


def generate_narration(text: str, 
                      output_path: Optional[str] = None, 
                      voice: Optional[str] = None,
                      provider: Optional[str] = None) -> tuple:
    """
    Main function to generate narration
    
    Args:
        text: Script to narrate
        output_path: Path to save audio file
        voice: Voice ID/name to use (unused, kept for compatibility)
        provider: "gemini" or "huggingface" (defaults to config)
    
    Returns:
        (audio_path, word_timings)
    """
    generator = TTSGenerator(provider=provider, voice=voice)
    print(f"🎤 Using TTS provider: {generator.provider}")
    audio_path = generator.generate_audio(text, output_path)
    return audio_path, getattr(generator, 'word_timings', [])

