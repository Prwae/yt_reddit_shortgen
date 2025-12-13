"""
TTS Narration Module - Supports Gemini and Edge-TTS
"""
from pathlib import Path
from typing import Optional, List, Tuple
import random
import wave
import asyncio
import json
import html

from .config import (
    TTS_PROVIDER, TTS_VOICE, TTS_RATE, TTS_PITCH, OUTPUT_DIR,
    GEMINI_API_KEY, GEMINI_API_KEYS, GEMINI_TTS_MODEL, GEMINI_TTS_VOICE_NAME, GEMINI_TTS_VOICES,
    GEMINI_TTS_RANDOMIZE, GEMINI_TTS_SAMPLE_RATE, GEMINI_TTS_STYLE_NOTE,
    EDGE_TTS_VOICE, EDGE_TTS_RANDOMIZE, EDGE_TTS_RATE, EDGE_TTS_PITCH
)


class TTSGenerator:
    """Generates text-to-speech narration using Gemini or Edge-TTS."""

    def __init__(self, 
                 provider: Optional[str] = None,
                 voice: Optional[str] = None,
                 use_elevenlabs: Optional[bool] = None):
        self.word_timings = []
        self.provider = (provider or TTS_PROVIDER).lower()
        self.voice = voice or TTS_VOICE  # kept for compatibility

        # Validate provider
        if self.provider not in ["gemini", "edge-tts"]:
            raise ValueError(f"Unsupported TTS provider: {self.provider}. Use 'gemini' or 'edge-tts'.")

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
            
            # Provider availability checks for Gemini
            if not GEMINI_API_KEYS:
                raise ValueError("No Gemini API keys set. Set GEMINI_API_KEY in .env or switch to edge-tts.")
        
        # Edge-TTS voice selection (will be done when needed)
        self.edge_tts_voice = None

    def generate_audio(self, text: str, output_path: Optional[str] = None) -> str:
        """Generate TTS audio and return path."""
        if output_path is None:
            output_path = str(OUTPUT_DIR / "narration.wav")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        # Prefer .wav for compatibility
        if not output_path.lower().endswith(".wav"):
            output_path = str(Path(output_path).with_suffix(".wav"))

        # Route to appropriate provider
        if self.provider == "gemini":
            return self._generate_gemini_tts(text, output_path)
        elif self.provider == "edge-tts":
            return self._generate_edge_tts(text, output_path)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

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
        """Generate audio via Edge-TTS (Microsoft Edge TTS) with retry logic."""
        try:
            import edge_tts
        except ImportError as e:
            raise ImportError("edge-tts not installed. Install with: pip install edge-tts") from e
        
        # Import aiohttp for error handling (it's a dependency of edge-tts)
        try:
            import aiohttp
        except ImportError:
            aiohttp = None  # Will handle errors generically if aiohttp not available

        # Ensure WAV output (edge-tts outputs as MP3 by default, but we'll convert)
        if not output_path.lower().endswith(".wav"):
            output_path = str(Path(output_path).with_suffix(".wav"))

        max_retries = 3
        retry_delays = [2, 5, 10]  # Exponential backoff delays in seconds
        
        async def generate():
            # Select voice (cache it to avoid re-fetching on retries)
            voice = self.voice or EDGE_TTS_VOICE
            if not voice:
                # Get available voices and filter for English
                try:
                    voices = await edge_tts.list_voices()
                    english_voices = [v for v in voices if v["Locale"].startswith("en-")]
                    
                    if EDGE_TTS_RANDOMIZE and english_voices:
                        voice = random.choice(english_voices)["Name"]
                    elif english_voices:
                        # Prefer US English, then any English
                        us_voices = [v for v in english_voices if v["Locale"].startswith("en-US")]
                        if us_voices:
                            voice = us_voices[0]["Name"]
                        else:
                            voice = english_voices[0]["Name"]
                    else:
                        raise RuntimeError("No English voices found in Edge-TTS")
                except Exception as e:
                    raise RuntimeError(f"Failed to fetch Edge-TTS voices: {e}")
            
            self.edge_tts_voice = voice
            print(f"🎤 Using Edge-TTS voice: {voice}")

            # Generate audio with SSML for rate and pitch control
            rate = EDGE_TTS_RATE if EDGE_TTS_RATE else "+0%"
            pitch = EDGE_TTS_PITCH if EDGE_TTS_PITCH else "+0Hz"
            
            # Create SSML with rate and pitch adjustments
            # Escape XML special characters in text
            escaped_text = html.escape(text)
            ssml_text = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US"><prosody rate="{rate}" pitch="{pitch}">{escaped_text}</prosody></speak>'
            
            # Retry logic for Edge-TTS generation
            last_exception = None
            for attempt in range(max_retries):
                try:
                    # Generate audio and collect word timings
                    communicate = edge_tts.Communicate(ssml_text, voice)
                    
                    # Collect word timings while generating
                    word_timings = []
                    audio_data = b""
                    
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_data += chunk["data"]
                        elif chunk["type"] == "WordBoundary":
                            # Edge-TTS provides word boundaries with offset in 100-nanosecond units
                            offset = chunk.get("offset", 0) / 10_000_000  # Convert to seconds
                            duration = chunk.get("duration", 0) / 10_000_000  # Convert to seconds
                            word_text = chunk.get("text", "").strip()
                            if word_text:
                                word_timings.append({
                                    "word": word_text,
                                    "start": offset,
                                    "end": offset + duration
                                })
                    
                    # Check if we got audio data
                    if not audio_data:
                        raise RuntimeError("No audio data received from Edge-TTS")
                    
                    # Save audio data
                    temp_mp3 = output_path.replace(".wav", ".mp3")
                    with open(temp_mp3, "wb") as f:
                        f.write(audio_data)
                    
                    # Convert MP3 to WAV using pydub or moviepy
                    try:
                        from pydub import AudioSegment
                        audio = AudioSegment.from_mp3(temp_mp3)
                        audio.export(output_path, format="wav")
                        Path(temp_mp3).unlink()  # Delete temp MP3
                    except ImportError:
                        # Fallback: use moviepy if pydub not available
                        try:
                            from moviepy.editor import AudioFileClip
                            audio = AudioFileClip(temp_mp3)
                            audio.write_audiofile(output_path, logger=None)
                            audio.close()
                            Path(temp_mp3).unlink()  # Delete temp MP3
                        except Exception as e:
                            # If conversion fails, just rename MP3 to WAV (not ideal but works)
                            print(f"⚠️  Could not convert MP3 to WAV: {e}")
                            print(f"   Using MP3 file instead. Install pydub for better compatibility.")
                            Path(temp_mp3).rename(output_path.replace(".wav", ".mp3"))
                            output_path = output_path.replace(".wav", ".mp3")
                    
                    self.word_timings = word_timings
                    return  # Success!
                    
                except Exception as e:
                    # Check if it's an aiohttp error (network/WebSocket issues)
                    is_network_error = False
                    if aiohttp:
                        is_network_error = isinstance(e, (aiohttp.ClientError, aiohttp.WSServerHandshakeError))
                    else:
                        # Check error message for network/WebSocket indicators
                        error_msg = str(e).lower()
                        is_network_error = any(indicator in error_msg for indicator in [
                            '403', 'forbidden', 'wsserverhandshake', 'websocket', 
                            'connection', 'network', 'invalid response status'
                        ])
                    
                    if is_network_error:
                        # Network/WebSocket errors - retry with backoff
                        last_exception = e
                        error_msg = str(e).lower()
                        
                        # Check if it's a 403 or rate limit error
                        if "403" in str(e) or "forbidden" in error_msg or "rate limit" in error_msg:
                            if attempt < max_retries - 1:
                                delay = retry_delays[attempt]
                                print(f"⚠️  Edge-TTS request failed (403/rate limit): {e}")
                                print(f"   Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                                await asyncio.sleep(delay)
                                continue
                            else:
                                raise RuntimeError(f"Edge-TTS failed after {max_retries} attempts (403/rate limit). Last error: {e}")
                        else:
                            # Other network errors - retry once
                            if attempt < max_retries - 1:
                                delay = retry_delays[attempt]
                                print(f"⚠️  Edge-TTS network error: {e}")
                                print(f"   Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                                await asyncio.sleep(delay)
                                continue
                            else:
                                raise
                    else:
                        # Other errors - don't retry
                        raise RuntimeError(f"Edge-TTS generation failed: {e}") from e
            
            # All retries exhausted
            raise RuntimeError(f"Edge-TTS failed after {max_retries} attempts. Last error: {last_exception}")
        
        # Run async generation
        asyncio.run(generate())
        
        print(f"✓ Generated audio with Edge-TTS to {output_path}")
        if self.word_timings:
            print(f"   Collected {len(self.word_timings)} word timings")
        return output_path


def generate_narration(text: str, 
                      output_path: Optional[str] = None, 
                      voice: Optional[str] = None,
                      provider: Optional[str] = None) -> tuple:
    """
    Main function to generate narration
    
    Args:
        text: Script to narrate
        output_path: Path to save audio file
        voice: Voice ID/name to use (for edge-tts: voice name like "en-US-AriaNeural")
        provider: TTS provider ("gemini" or "edge-tts")
    
    Returns:
        (audio_path, word_timings)
    """
    generator = TTSGenerator(provider=provider, voice=voice)
    print(f"🎤 Using TTS provider: {generator.provider}")
    audio_path = generator.generate_audio(text, output_path)
    return audio_path, getattr(generator, 'word_timings', [])

