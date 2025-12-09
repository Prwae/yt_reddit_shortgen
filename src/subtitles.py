"""
Subtitles Module - Generates word-timed subtitles with proper formatting
Uses audio analysis for accurate synchronization
"""
import re
import html
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from .config import (
    OUTPUT_DIR,
    SUBTITLE_WORDS_PER_LINE,
    SUBTITLE_LEAD_SECONDS,
    SUBTITLE_DURATION_SCALE,
    SUBTITLE_MIN_DURATION,
    ASSEMBLYAI_API_KEY,
)
import json
import numpy as np


class SubtitleGenerator:
    """Generates word-timed subtitles for videos"""
    
    def __init__(self):
        self.subtitle_segments = []
    
    def generate_from_script(self, 
                           script: str,
                           audio_duration: float,
                           subtitle_segments: Optional[List[str]] = None,
                           word_timings: Optional[List[Dict]] = None,
                           audio_path: Optional[str] = None) -> List[Dict]:
        """
        Generate word-timed subtitles from script using audio analysis for synchronization
        Args:
            script: Full narration script
            audio_duration: Duration of audio in seconds
            subtitle_segments: Pre-segmented subtitle chunks (optional)
            word_timings: Word-level timings from TTS (optional)
            audio_path: Path to audio file for analysis (optional, but recommended)
        Returns:
            List of subtitle dictionaries with timing
        """
        if subtitle_segments:
            # If provided segments, split them further to 1-3 words
            segments = []
            for segment in subtitle_segments:
                segments.extend(self._split_into_segments(segment, SUBTITLE_WORDS_PER_LINE))
        else:
            segments = self._split_into_segments(script, SUBTITLE_WORDS_PER_LINE)
        
        # Use word-level timing from TTS if available
        if word_timings and len(word_timings) > 0:
            subs = self._generate_from_word_timings(script, segments, word_timings, audio_duration)
        elif audio_path and Path(audio_path).exists():
            # Try AssemblyAI first for perfect synchronization
            if ASSEMBLYAI_API_KEY:
                try:
                    subs = self._generate_from_assemblyai(script, segments, audio_path, audio_duration)
                except Exception as e:
                    error_msg = str(e)
                    if "401" in error_msg or "unauthorized" in error_msg.lower():
                        print("⚠️  AssemblyAI API key invalid, falling back to audio analysis")
                    elif "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                        print("⚠️  AssemblyAI rate limit/quota exceeded, falling back to audio analysis")
                    else:
                        print(f"⚠️  AssemblyAI failed: {error_msg[:100]}, falling back to audio analysis")
                    # Fallback to audio analysis
                    subs = self._generate_from_audio_analysis(script, segments, audio_path, audio_duration)
            else:
                # No AssemblyAI key, use audio analysis
                subs = self._generate_from_audio_analysis(script, segments, audio_path, audio_duration)
        else:
            # Fallback: distribute timings proportionally across the full audio duration
            subs = self._generate_proportional_timings(script, segments, audio_duration)

        # Return subtitles directly without any timing manipulations
        return subs
    
    def _split_into_segments(self, script: str, max_words: int = 3) -> List[str]:
        """Split script into subtitle segments (1-3 words per segment)"""
        # Split by words
        words = script.split()
        segments = []
        
        current_segment = []
        for word in words:
            # Remove punctuation for counting, but keep it
            clean_word = re.sub(r'[^\w\s]', '', word)
            
            if len(current_segment) < max_words:
                current_segment.append(word)
            else:
                # Save current segment
                segments.append(' '.join(current_segment))
                current_segment = [word]
        
        # Add remaining words
        if current_segment:
            segments.append(' '.join(current_segment))
        
        return segments if segments else [script]
    
    def _normalize_word_for_matching(self, word: str) -> str:
        """Normalize word for matching by removing punctuation and converting to lowercase"""
        # Remove all punctuation and special characters
        normalized = re.sub(r'[^\w\s]', '', word.strip().lower())
        return normalized
    
    def _words_match(self, word1: str, word2: str) -> bool:
        """Check if two words match (with fuzzy matching for common variations)"""
        norm1 = self._normalize_word_for_matching(word1)
        norm2 = self._normalize_word_for_matching(word2)
        
        # Exact match
        if norm1 == norm2:
            return True
        
        # Check if one contains the other (for contractions: "don't" vs "dont")
        if norm1 and norm2:
            if norm1 in norm2 or norm2 in norm1:
                # Only match if lengths are similar (avoid false matches)
                if abs(len(norm1) - len(norm2)) <= 2:
                    return True
        
        # Check first 3 characters match (for slight variations)
        if len(norm1) >= 3 and len(norm2) >= 3:
            if norm1[:3] == norm2[:3]:
                return True
        
        return False
    
    def _generate_from_word_timings(self, script: str, segments: List[str], 
                                    word_timings: List[Dict], audio_duration: float) -> List[Dict]:
        """Generate subtitles synchronized with TTS word timings"""
        # Convert word timings to a map for quick lookup
        words = script.split()
        timing_map = {}
        word_idx = 0
        unmatched_words = []
        skipped_timings = []
        
        # Try to match each word timing to script words
        for timing_idx, timing in enumerate(word_timings):
            timing_text = timing.get('text', '').strip()
            
            # Try to find matching word in script (search ahead up to 5 words)
            matched = False
            search_range = min(5, len(words) - word_idx)
            
            for offset in range(search_range):
                if word_idx + offset >= len(words):
                    break
                
                script_word = words[word_idx + offset]
                
                if self._words_match(timing_text, script_word):
                    # Found match - use this word index
                    offset_sec = timing.get('offset', 0)
                    duration_sec = timing.get('duration', 0)
                    
                    # Convert to seconds if needed (AssemblyAI already in ms)
                    if offset_sec > 1000:  # Likely in milliseconds
                        offset_sec = offset_sec / 1000.0
                        duration_sec = duration_sec / 1000.0
                    
                    timing_map[word_idx + offset] = {
                        'start': offset_sec,
                        'end': offset_sec + duration_sec,
                        'text': script_word
                    }
                    
                    # Advance word_idx past matched words
                    if offset == 0:
                        word_idx += 1
                    else:
                        # Skip unmatched words between current and match
                        word_idx = word_idx + offset + 1
                    
                    matched = True
                    break
            
            if not matched:
                skipped_timings.append((timing_idx, timing_text))
                # Don't advance word_idx if no match found - try next timing
        
        # Log matching statistics
        matched_count = len(timing_map)
        total_words = len(words)
        match_rate = (matched_count / total_words * 100) if total_words > 0 else 0
        
        if skipped_timings:
            print(f"⚠️  {len(skipped_timings)} word timings couldn't be matched to script words")
            if len(skipped_timings) <= 5:
                print(f"   Unmatched timings: {[t[1] for t in skipped_timings]}")
        
        if match_rate < 80:
            print(f"⚠️  Low word matching rate: {match_rate:.1f}% ({matched_count}/{total_words} words matched)")
        
        print(f"✓ Matched {matched_count}/{total_words} words ({match_rate:.1f}%)")
        
        # Generate subtitles based on segments and their word timings
        subtitles = []
        script_words = script.split()
        word_idx = 0
        
        for seg_idx, segment in enumerate(segments):
            segment_words = segment.split()
            if not segment_words:
                continue
            
            # Find start and end times for this segment
            segment_start_idx = word_idx
            segment_end_idx = min(word_idx + len(segment_words), len(script_words))
            
            # Get timing from first and last word in segment
            start_time = None
            end_time = None
            matched_word_indices = []
            
            # Find all matched words in this segment
            for i in range(segment_start_idx, segment_end_idx):
                if i in timing_map:
                    matched_word_indices.append(i)
                    if start_time is None:
                        start_time = timing_map[i]['start']  # Start when first matched word begins
                    end_time = timing_map[i]['end']  # End when last matched word ends
            
            # Handle partial matches
            if start_time is None:
                # No words matched in this segment - use interpolation
                if subtitles:
                    # Use end of previous subtitle as start
                    start_time = subtitles[-1]['end']
                else:
                    # First subtitle - start from beginning
                    start_time = 0.0
                
                # Estimate duration based on word count
                estimated_duration = len(segment_words) / 2.5  # 2.5 words per second
                end_time = start_time + estimated_duration
                
                # Try to find next matched word to get better end time
                for i in range(segment_end_idx, min(segment_end_idx + 3, len(script_words))):
                    if i in timing_map:
                        # Use start of next matched word as end time
                        end_time = timing_map[i]['start']
                        break
            elif len(matched_word_indices) < len(segment_words):
                # Partial match - some words matched, some didn't
                # Use matched words for timing, but ensure minimum duration
                if end_time - start_time < SUBTITLE_MIN_DURATION:
                    end_time = start_time + SUBTITLE_MIN_DURATION
            
            # Ensure end doesn't exceed audio duration
            end_time = min(end_time, audio_duration)
            
            # Ensure start is valid
            start_time = max(0.0, start_time)
            
            subtitles.append({
                'start': start_time,
                'end': end_time,
                'text': segment.strip()
            })
            
            word_idx = segment_end_idx
        
        # Ensure last subtitle ends at audio duration
        if subtitles:
            subtitles[-1]['end'] = min(audio_duration, subtitles[-1]['end'])
        
        # Return timings directly from AssemblyAI without any adjustments
        return subtitles

    def _apply_lead(self, subtitles: List[Dict], audio_duration: float) -> List[Dict]:
        """Shift subtitles by lead/delay amount. Negative = delay (shift later), positive = lead (shift earlier)."""
        if SUBTITLE_LEAD_SECONDS == 0 or not subtitles:
            return subtitles
        offset = SUBTITLE_LEAD_SECONDS
        adjusted = []
        for sub in subtitles:
            # Subtract offset: if negative, this adds delay (shifts later)
            start = max(0.0, sub['start'] - offset)
            end = max(start, min(audio_duration, sub['end'] - offset))
            adjusted.append({
                'start': start,
                'end': end,
                'text': sub['text']
            })
        # Ensure last end is not beyond audio_duration
        if adjusted:
            adjusted[-1]['end'] = min(audio_duration, adjusted[-1]['end'])
        return adjusted

    def _shrink_durations(self, subtitles: List[Dict], audio_duration: float) -> List[Dict]:
        """Shorten each subtitle duration slightly to mitigate lag accumulation."""
        if SUBTITLE_DURATION_SCALE >= 0.999 or not subtitles:
            return subtitles
        scaled = []
        current = 0.0
        for sub in subtitles:
            raw_dur = max(0.0, sub['end'] - sub['start'])
            new_dur = max(SUBTITLE_MIN_DURATION, raw_dur * SUBTITLE_DURATION_SCALE)
            start = current
            end = start + new_dur
            scaled.append({'start': start, 'end': end, 'text': sub['text']})
            current = end

        # If we overshoot audio, clamp
        if scaled and scaled[-1]['end'] > audio_duration:
            trim = scaled[-1]['end'] - audio_duration
            # Reduce last duration but keep minimum
            last = scaled[-1]
            new_last_dur = max(SUBTITLE_MIN_DURATION, (last['end'] - last['start']) - trim)
            last['end'] = last['start'] + new_last_dur
        return scaled

    def _clean_script_for_assemblyai(self, script: str) -> str:
        """Clean script by removing HTML entities and service symbols that break AssemblyAI"""
        # Decode HTML entities (e.g., &amp; -> &, &lt; -> <, &gt; -> >, &quot; -> ")
        cleaned = html.unescape(script)
        
        # Remove other common service symbols that might break transcription
        # Remove zero-width characters
        cleaned = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f]', '', cleaned)
        
        # Remove other problematic Unicode symbols
        cleaned = re.sub(r'[\u00ad]', '', cleaned)  # Soft hyphen
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _generate_from_assemblyai(self, script: str, segments: List[str], 
                                  audio_path: str, audio_duration: float) -> List[Dict]:
        """
        Use AssemblyAI to transcribe audio and get word-level timestamps for perfect synchronization.
        This provides the most accurate subtitle timing by analyzing the actual spoken audio.
        """
        try:
            import assemblyai as aai
            
            if not ASSEMBLYAI_API_KEY:
                raise ValueError("ASSEMBLYAI_API_KEY not set")
            
            # Clean script before processing
            cleaned_script = self._clean_script_for_assemblyai(script)
            
            # Set API key
            aai.settings.api_key = ASSEMBLYAI_API_KEY
            
            # Create transcriber
            transcriber = aai.Transcriber()
            
            # Transcribe audio file
            print("📡 Transcribing audio with AssemblyAI...")
            transcript = transcriber.transcribe(audio_path)
            
            # Check if transcription completed successfully
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"AssemblyAI transcription failed: {transcript.error}")
            
            # Get word-level timings from transcript
            word_timings = []
            if transcript.words:
                for word in transcript.words:
                    word_timings.append({
                        'text': word.text,
                        'offset': word.start / 1000.0,  # Convert from ms to seconds
                        'duration': (word.end - word.start) / 1000.0  # Convert from ms to seconds
                    })
            
            if not word_timings:
                print("⚠️  AssemblyAI did not return word timings, falling back to audio analysis")
                return self._generate_from_audio_analysis(script, segments, audio_path, audio_duration)
            
            print(f"✓ Got {len(word_timings)} word timings from AssemblyAI")
            
            # Use word timings to generate subtitles (use cleaned script for matching)
            return self._generate_from_word_timings(cleaned_script, segments, word_timings, audio_duration)
            
        except ImportError:
            print("⚠️  assemblyai package not installed. Install with: pip install assemblyai")
            return self._generate_from_audio_analysis(script, segments, audio_path, audio_duration)
        except Exception as e:
            error_msg = str(e)
            # Re-raise quota/auth errors to be handled by caller
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise
            elif "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                raise
            # For other errors, fall back
            import traceback
            print(f"⚠️  AssemblyAI transcription failed: {error_msg[:200]}")
            traceback.print_exc()
            return self._generate_from_audio_analysis(script, segments, audio_path, audio_duration)
    
    def _generate_from_audio_analysis(self, script: str, segments: List[str], 
                                      audio_path: str, audio_duration: float) -> List[Dict]:
        """
        Analyze audio to detect speech segments and pauses, then map subtitles to actual speech timing.
        Accounts for intonation stops and natural pauses in TTS.
        """
        try:
            from moviepy.editor import AudioFileClip
            
            # Load audio at reasonable sample rate
            audio_clip = AudioFileClip(audio_path)
            sample_rate = 16000  # 16kHz is sufficient for speech detection
            audio_array = audio_clip.to_soundarray(fps=sample_rate)
            audio_clip.close()
            
            # Convert to mono if stereo
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            # Calculate energy in short windows to detect speech vs silence
            window_ms = 50  # 50ms windows
            window_samples = int(sample_rate * window_ms / 1000)
            hop_samples = window_samples // 2  # 50% overlap
            
            # Calculate RMS energy for each window
            energies = []
            for i in range(0, len(audio_array) - window_samples, hop_samples):
                window = audio_array[i:i + window_samples]
                rms = np.sqrt(np.mean(window ** 2))
                energies.append(rms)
            
            if not energies:
                print("⚠️  Could not analyze audio, using proportional timing")
                return self._generate_proportional_timings(script, segments, audio_duration)
            
            energies = np.array(energies)
            energy_times = np.arange(len(energies)) * (hop_samples / sample_rate)
            
            # Normalize energies
            if energies.max() > 0:
                energies = energies / energies.max()
            
            # Adaptive threshold: use percentile to find silence level
            silence_threshold = np.percentile(energies, 20)  # Bottom 20% is likely silence
            speech_threshold = max(0.1, silence_threshold * 2)  # Speech is at least 2x silence
            
            # Detect speech vs silence
            is_speech = energies > speech_threshold
            
            # Smooth: fill very short gaps (< 100ms) in speech
            min_gap_samples = int(0.1 * sample_rate / hop_samples)  # 100ms in energy samples
            is_speech_smooth = is_speech.copy()
            
            # Fill small gaps
            gap_start = None
            for i in range(len(is_speech_smooth)):
                if not is_speech_smooth[i] and gap_start is None:
                    gap_start = i
                elif is_speech_smooth[i] and gap_start is not None:
                    gap_length = i - gap_start
                    if gap_length < min_gap_samples:
                        # Fill this gap
                        is_speech_smooth[gap_start:i] = True
                    gap_start = None
            
            # Find continuous speech segments (where speech actually occurs)
            speech_segments = []
            in_speech = False
            seg_start = 0.0
            
            for i, speaking in enumerate(is_speech_smooth):
                time_pos = energy_times[i] if i < len(energy_times) else audio_duration
                
                if speaking and not in_speech:
                    seg_start = time_pos
                    in_speech = True
                elif not speaking and in_speech:
                    # End of speech segment
                    if time_pos - seg_start > 0.05:  # Only add segments > 50ms
                        speech_segments.append((seg_start, time_pos))
                    in_speech = False
            
            # Handle speech continuing to end
            if in_speech:
                speech_segments.append((seg_start, audio_duration))
            
            # If no speech detected, fall back
            if not speech_segments:
                print("⚠️  No speech segments detected, using proportional timing")
                return self._generate_proportional_timings(script, segments, audio_duration)
            
            # Calculate total speech time (excluding pauses)
            total_speech_time = sum(end - start for start, end in speech_segments)
            
            # Map subtitle segments to speech segments
            # Use character count weighted by word complexity
            script_words = script.split()
            word_weights = self._calculate_word_weights(script_words)
            total_weight = sum(word_weights) if word_weights else len(script_words)
            
            subtitles = []
            word_idx = 0
            cumulative_speech_time = 0.0
            
            for segment in segments:
                seg_words = segment.split()
                if not seg_words:
                    continue
                
                # Calculate weight for this segment
                seg_weight = sum(word_weights[word_idx:word_idx + len(seg_words)]) if word_idx < len(word_weights) else len(seg_words)
                word_idx += len(seg_words)
                
                # How much speech time this segment should occupy
                segment_speech_duration = total_speech_time * (seg_weight / total_weight) if total_weight > 0 else total_speech_time / len(segments)
                
                # Map speech time to actual audio time
                target_start_speech = cumulative_speech_time
                target_end_speech = cumulative_speech_time + segment_speech_duration
                
                start_time = self._map_speech_time_to_audio(target_start_speech, speech_segments, total_speech_time)
                end_time = self._map_speech_time_to_audio(target_end_speech, speech_segments, total_speech_time)
                
                # Ensure minimum duration
                if end_time - start_time < SUBTITLE_MIN_DURATION:
                    end_time = min(audio_duration, start_time + SUBTITLE_MIN_DURATION)
                
                subtitles.append({
                    'start': start_time,
                    'end': end_time,
                    'text': segment.strip()
                })
                
                cumulative_speech_time += segment_speech_duration
            
            # Ensure last subtitle ends at audio duration
            if subtitles:
                subtitles[-1]['end'] = audio_duration
            
            print(f"✓ Generated {len(subtitles)} subtitles using speech detection ({len(speech_segments)} speech segments, {total_speech_time:.2f}s speech time)")
            return subtitles
            
        except Exception as e:
            import traceback
            print(f"⚠️  Audio analysis failed: {e}")
            traceback.print_exc()
            return self._generate_proportional_timings(script, segments, audio_duration)
    
    def _map_speech_time_to_audio(self, speech_time: float, speech_segments: List[Tuple[float, float]], 
                                  total_speech_time: float) -> float:
        """Map proportional speech time (excluding pauses) to actual audio timestamp"""
        if not speech_segments or total_speech_time <= 0:
            return speech_time
        
        # Clamp speech_time to valid range
        speech_time = max(0.0, min(speech_time, total_speech_time))
        
        # Find which speech segment contains this time
        cumulative_speech = 0.0
        for seg_start, seg_end in speech_segments:
            seg_duration = seg_end - seg_start
            
            if cumulative_speech + seg_duration >= speech_time:
                # This segment contains the target time
                local_time = speech_time - cumulative_speech
                progress = local_time / seg_duration if seg_duration > 0 else 0
                return seg_start + (seg_duration * progress)
            
            cumulative_speech += seg_duration
        
        # Fallback: return end of last segment
        return speech_segments[-1][1] if speech_segments else 0.0
    
    def _calculate_word_weights(self, words: List[str]) -> List[float]:
        """Calculate timing weights for words based on length and punctuation"""
        weights = []
        for word in words:
            base = 1.0 + len(word) / 10.0  # Longer words get more time
            if word.endswith(('.', '!', '?')):
                base += 0.5  # Pause after sentence end
            elif word.endswith((',', ';', ':')):
                base += 0.2  # Brief pause
            weights.append(base)
        return weights
    
    def _generate_proportional_timings(self, script: str, segments: List[str], audio_duration: float) -> List[Dict]:
        """
        Distribute subtitle timings across the actual audio duration using word-level weights.
        This avoids fixed words-per-second guesses and keeps total time aligned to the audio length.
        """
        script_words = script.split()
        if not script_words or audio_duration <= 0:
            return []

        def word_weight(word: str) -> float:
            base = 1.0 + len(word) / 8.0  # longer words get slightly more time
            if word.endswith(('.', '!', '?')):
                base += 0.6  # pause after sentence end
            elif word.endswith((',', ';', ':')):
                base += 0.3  # brief pause
            return base

        weights = [word_weight(w) for w in script_words]
        total_weight = sum(weights) if weights else 1.0

        min_dur = 0.35
        max_dur = min(3.0, audio_duration)

        durations = []
        word_idx = 0
        for segment in segments:
            seg_words = segment.split()
            seg_len = len(seg_words)
            if seg_len == 0:
                continue

            seg_weight = sum(weights[word_idx:word_idx + seg_len])
            word_idx += seg_len

            raw_duration = audio_duration * (seg_weight / total_weight) if total_weight > 0 else audio_duration / len(segments)
            durations.append(max(min_dur, min(max_dur, raw_duration)))

        # Scale durations to exactly match audio duration
        total_dur = sum(durations)
        if total_dur > 0:
            scale = audio_duration / total_dur
            durations = [max(0.2, d * scale) for d in durations]

        subtitles = []
        current_time = 0.0
        for segment, dur in zip(segments, durations):
            start = current_time
            end = min(audio_duration, start + dur)
            subtitles.append({
                'start': start,
                'end': end,
                'text': segment.strip()
            })
            current_time = end

        # Ensure last subtitle ends exactly at audio duration
        if subtitles:
            subtitles[-1]['end'] = audio_duration

        return subtitles
    
    def save_srt(self, subtitles: List[Dict], output_path: str):
        """Save subtitles in SRT format"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, subtitle in enumerate(subtitles, 1):
                start_time = self._format_srt_time(subtitle['start'])
                end_time = self._format_srt_time(subtitle['end'])
                text = subtitle['text']
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
    
    def save_json(self, subtitles: List[Dict], output_path: str):
        """Save subtitles in JSON format"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(subtitles, f, indent=2, ensure_ascii=False)
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds to SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_subtitles(script: str,
                      audio_duration: float,
                      subtitle_segments: Optional[List[str]] = None,
                      output_path: Optional[str] = None,
                      format: str = 'json',
                      word_timings: Optional[List[Dict]] = None,
                      audio_path: Optional[str] = None) -> List[Dict]:
    """
    Main function to generate subtitles
    Args:
        script: Full narration script
        audio_duration: Duration of audio in seconds
        subtitle_segments: Pre-segmented subtitle chunks
        output_path: Path to save subtitle file
        format: 'srt' or 'json'
    Returns:
        List of subtitle dictionaries
    """
    generator = SubtitleGenerator()
    subtitles = generator.generate_from_script(script, audio_duration, subtitle_segments, word_timings, audio_path)
    
    if output_path:
        if format.lower() == 'srt':
            generator.save_srt(subtitles, output_path)
        else:
            generator.save_json(subtitles, output_path)
    
    return subtitles

