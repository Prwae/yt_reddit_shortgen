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

# Check ElevenLabs voices
elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
if elevenlabs_key:
    print("\n[ElevenLabs Voices]")
    print("-" * 60)
    try:
        from .tts_narration import TTSGenerator
        voices = TTSGenerator.list_elevenlabs_voices()
        
        if voices:
            print(f"Found {len(voices)} voices:\n")
            for i, voice in enumerate(voices[:20], 1):  # Show first 20
                print(f"{i}. {voice['name']}")
                print(f"   ID: {voice['voice_id']}")
                print(f"   Category: {voice.get('category', 'unknown')}")
                print()
            
            if len(voices) > 20:
                print(f"... and {len(voices) - 20} more voices")
            
            print("\n💡 Popular natural female voices:")
            print("   - Bella: EXAVITQu4vr4xnSDxMaL (very natural)")
            print("   - Domi: ThT5KcBeYPX3keUQqHPh (expressive)")
            print("   - Rachel: 21m00Tcm4TlvDq8ikWAM (original)")
        else:
            print("No voices found. Check your API key.")
    except Exception as e:
        print(f"Error listing ElevenLabs voices: {e}")
        print("Make sure ELEVENLABS_API_KEY is set in .env")
else:
    print("\n[ElevenLabs]")
    print("⚠️  ELEVENLABS_API_KEY not set. Skipping ElevenLabs voices.")

# Check Edge TTS voices
print("\n[Edge TTS Voices]")
print("-" * 60)
print("Popular natural female voices:")
print("   - en-US-JennyNeural (very natural, recommended)")
print("   - en-US-AriaNeural (clear, professional)")
print("   - en-GB-SoniaNeural (British, natural)")
print("   - en-AU-NatashaNeural (Australian, natural)")
print("\nTo see all Edge TTS voices, run:")
print("   python -c \"import edge_tts; import asyncio; asyncio.run(edge_tts.list_voices())\"")

print("\n" + "=" * 60)
print("To change voice, set in .env file:")
print("   ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL  # For ElevenLabs")
print("   EDGE_TTS_VOICE=en-US-JennyNeural  # For Edge TTS")
print("=" * 60)





