"""
Script to list available TTS voices
Run this to see available voices and their IDs
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("Available TTS Voices")
print("=" * 60)

# Check Gemini voices
from src.config import GEMINI_TTS_VOICES, GEMINI_API_KEYS
if GEMINI_API_KEYS:
    print("\n[Gemini TTS Voices]")
    print("-" * 60)
    print("Available Gemini voices:")
    for i, voice in enumerate(GEMINI_TTS_VOICES, 1):
        print(f"   {i}. {voice}")
    print("\n💡 To use a specific voice, set in .env:")
    print("   GEMINI_TTS_VOICE_NAME=Kore")
    print("   GEMINI_TTS_RANDOMIZE=false  # Set to false to use specific voice")
else:
    print("\n[Gemini TTS]")
    print("⚠️  GEMINI_API_KEY not set. Skipping Gemini voices.")

# Check Edge TTS voices
print("\n[Edge-TTS Voices]")
print("-" * 60)
print("Popular voices (configured in code):")
from src.config import EDGE_TTS_VOICES
for i, voice in enumerate(EDGE_TTS_VOICES, 1):
    print(f"   {i}. {voice}")

print("\n💡 Popular natural female voices:")
print("   - en-US-AriaNeural (clear, professional)")
print("   - en-US-JennyNeural (very natural, recommended)")
print("   - en-GB-SoniaNeural (British, natural)")
print("   - en-AU-NatashaNeural (Australian, natural)")

print("\n💡 Popular male voices:")
print("   - en-US-GuyNeural (US English, male)")
print("   - en-GB-RyanNeural (British, male)")
print("   - en-AU-WilliamNeural (Australian, male)")

print("\n📋 To see ALL available Edge-TTS voices, run:")
print("   python -c \"import edge_tts; import asyncio; voices = asyncio.run(edge_tts.list_voices()); [print(f'{v['ShortName']} - {v['Gender']} - {v['Locale']}') for v in voices if 'en' in v['Locale']]\"")
print("   Or visit: https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/voices")

print("\n" + "=" * 60)
print("To change voice, set in .env file:")
print("   TTS_PROVIDER=edge-tts  # or 'gemini'")
print("   EDGE_TTS_VOICE_NAME=en-US-JennyNeural  # For Edge-TTS")
print("   GEMINI_TTS_VOICE_NAME=Kore  # For Gemini")
print("   EDGE_TTS_RANDOMIZE=false  # Set to false to use specific voice")
print("=" * 60)





