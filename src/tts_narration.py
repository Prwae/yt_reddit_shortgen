"""
TTS Narration Module - Gemini native TTS (no fallbacks)
"""
from pathlib import Path
from typing import Optional
import random
import wave
import numpy as np

from .config import (
    TTS_PROVIDER, TTS_VOICE, TTS_RATE, TTS_PITCH, OUTPUT_DIR,
    GEMINI_API_KEY, GEMINI_API_KEYS, GEMINI_TTS_MODEL, GEMINI_TTS_VOICE_NAME, GEMINI_TTS_VOICES,
    GEMINI_TTS_RANDOMIZE, GEMINI_TTS_SAMPLE_RATE, GEMINI_TTS_STYLE_NOTE
)


class TTSGenerator:
    """Generates text-to-speech narration using Gemini only."""

    def __init__(self, 
                 provider: Optional[str] = None,
                 voice: Optional[str] = None,
                 use_elevenlabs: Optional[bool] = None):
        # Gemini/HF do not return word timings; keep for API compatibility
        self.word_timings = []
        self.provider = provider or TTS_PROVIDER
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

        # Provider availability checks
        if not GEMINI_API_KEYS:
            raise ValueError("No Gemini API keys set. Set GEMINI_API_KEY in .env.")
        # Force provider to gemini
        self.provider = "gemini"

    def generate_audio(self, text: str, output_path: Optional[str] = None) -> str:
        """Generate TTS audio and return path."""
        if output_path is None:
            output_path = str(OUTPUT_DIR / "narration.wav")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        # Prefer .wav because Gemini returns PCM
        if not output_path.lower().endswith(".wav"):
            output_path = str(Path(output_path).with_suffix(".wav"))

        # Only Gemini is supported
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

                # Post-process: tame harsh peaks, normalize, and remove background noise
                pcm = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
                if pcm.size > 0:
                    # Gentle soft clip to reduce screechy highs
                    pcm = np.tanh(pcm / 32768.0 * 1.3) * 32767.0
                    
                    # Noise reduction: remove background noise
                    pcm = self._reduce_noise(pcm)
                    
                    # Peak normalize to about -3 dBFS
                    peak = np.max(np.abs(pcm))
                    if peak > 0:
                        target = 32767.0 * 0.707  # -3 dB
                        gain = min(1.0, target / peak)
                        pcm *= gain
                pcm_int16 = pcm.astype(np.int16).tobytes()

                # Write WAV (PCM 16-bit mono, sample rate from config)
                with wave.open(output_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(GEMINI_TTS_SAMPLE_RATE)
                    wf.writeframes(pcm_int16)

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
    
    def _reduce_noise(self, audio: np.ndarray) -> np.ndarray:
        """
        Reduce background noise from audio using spectral subtraction and noise gate.
        
        Args:
            audio: Audio signal as float32 array
        
        Returns:
            Denoised audio signal
        """
        try:
            from scipy import signal
        except ImportError:
            # Fallback: simple noise gate if scipy not available
            return self._simple_noise_gate(audio)
        
        # Convert to normalized float
        audio_norm = audio / 32768.0
        
        # High-pass filter to remove low-frequency noise (below 80 Hz)
        # This removes rumble, hum, and other low-frequency background noise
        nyquist = GEMINI_TTS_SAMPLE_RATE / 2
        high_cutoff = 80.0 / nyquist
        b, a = signal.butter(4, high_cutoff, btype='high')
        audio_norm = signal.filtfilt(b, a, audio_norm)
        
        # Noise gate: remove very quiet sections (likely background noise)
        # Calculate RMS energy in small windows
        window_size = int(GEMINI_TTS_SAMPLE_RATE * 0.05)  # 50ms windows
        if window_size < len(audio_norm):
            # Estimate noise floor from first 200ms (typically quiet)
            noise_sample_size = min(int(GEMINI_TTS_SAMPLE_RATE * 0.2), len(audio_norm) // 4)
            noise_floor = np.std(audio_norm[:noise_sample_size])
            threshold = noise_floor * 2.5  # Gate threshold
            
            # Apply noise gate: attenuate sections below threshold
            for i in range(0, len(audio_norm), window_size):
                window = audio_norm[i:i+window_size]
                if len(window) > 0:
                    rms = np.sqrt(np.mean(window ** 2))
                    if rms < threshold:
                        # Gradually fade out quiet sections
                        fade_factor = max(0.0, (rms / threshold) ** 2)
                        audio_norm[i:i+len(window)] *= fade_factor
        
        # Convert back to int16 range
        return audio_norm * 32768.0
    
    def _simple_noise_gate(self, audio: np.ndarray) -> np.ndarray:
        """Simple noise gate fallback if scipy not available."""
        # Estimate noise floor from first 200ms
        noise_sample_size = min(int(GEMINI_TTS_SAMPLE_RATE * 0.2), len(audio) // 4)
        if noise_sample_size > 0:
            noise_floor = np.std(audio[:noise_sample_size])
            threshold = noise_floor * 2.5
            
            # Simple gate: zero out samples below threshold
            mask = np.abs(audio) > threshold
            audio = audio * mask
        
        return audio


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
        provider: (ignored, Gemini only)
    
    Returns:
        (audio_path, word_timings)
    """
    generator = TTSGenerator(provider="gemini", voice=voice)
    print(f"🎤 Using TTS provider: {generator.provider}")
    audio_path = generator.generate_audio(text, output_path)
    return audio_path, getattr(generator, 'word_timings', [])

