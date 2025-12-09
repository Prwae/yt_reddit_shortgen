You are an AI system architect. Your task is to design a complete automated project that produces short-form YouTube videos in the style of Reddit Reads.



The system will create:

\- Reddit-based rewritten stories  

\- TTS narration  

\- Automated subtitles  

\- An intro card (using a user-provided static image with only a title overlay)  

\- Final video assembled with \*\*user-provided background footage\*\*



The system must \*not\* generate background footage.  

It must \*use only the videos the user provides\* as background loops.

Use Gemini API for text-based manipulations



---



\## 1. System Overview

Build a fully automated pipeline that:

1\. Fetches stories  

2\. Rewrites them  

3\. Generates narration  

4\. Generates subtitles  

5\. Places title text onto the intro image  

6\. Uses \*\*user-provided background video files\*\*  

6.1 Adds user-provided music

7\. Exports vertically in 9:16  

8\. Prepares completed files for uploading  



No uploading required — the user handles that separately.



---



\## 2. Story Sourcing Module

System must be able to:

\- Fetch public Reddit posts from allowed subreddits (AITA, AskReddit, Confessions, etc.)  

\- Filter by upvotes, emotional intensity, and readability  

\- Clean formatting  

\- Identify the hook  

\- Pass cleaned text to the rewrite module  

\- NOT use API key



---



\## 3. Story Rewrite Module

The system must produce a transformed short-form script:

\- 25–50 seconds  

\- Strong hook in first 3–4 seconds  

\- Clear story structure (beginning → conflict → climax → resolution)  

\- No policy-violating content  

\- Output:  

&nbsp; - Final narration script  

&nbsp; - Subtitle content with timing instructions  



---



\## 4. Intro Card Module (IMPORTANT)

Procedurally generate one: rounded corner rectangle, avatar cropped into circle in top left of it, nickname to the right of the avatar, post title under both.



---



\## 5. Narration (TTS) Module

System must describe how to generate:

\- A natural human-like voice  

\- Calm but engaging pacing  

\- Proper timing for short-form viewing  

\- Export audio file (WAV/MP3) ready for syncing  



---



\## 6. Subtitles Module

System must generate:

\- Word-timed subtitles (SRT or JSON)  

\- High-contrast, readable, safe-zone placement  

\- 1–2 lines max  

\- Auto-split long sentences  

\- Clean font with strong outlines or shadows  



---



\## 7. Visual Assembly Module



\### Intro sequence

\- Show intro card image with overlaid title until TTS completes reading the title.



\### Main content

\- Import \*\*user-provided background footage\*\* from a folder (e.g., `/videos/backgrounds/`)  

\- Use these clips as loop or continuous background  

\- Fit/crop to 9:16  

\- Apply subtitles  

\- Sync subtitles with TTS  

\- Add user-provided music

\- Maintain visual consistency  



\### Rules

\- Do NOT generate background visuals  

\- Do NOT add watermarks  

\- Do NOT add extra UI elements  

\- Do NOT add transitions unless specified  



Final output: MP4, 9:16, optimized for YouTube Shorts.



---



\## 8. Metadata Generator

System must generate:

\- A short viral title  

\- Hashtags/keywords for story genre  

\- A clean description including disclaimer:  

&nbsp; “Stories are sourced from public online forums and rewritten for entertainment.”



---



\## 9. Compliance Module

Ensure:

\- Transformative content that avoids “reused content” flags  

\- No real identifying details  

\- No harmful content  

\- Only user-provided background footage  

\- Only user-provided intro image  



---



\## 10. Scaling \& Automation

Design instructions for:

\- Batch processing  

\- Automatic story selection  

\- Multiple versions  

\- Multi-language pipeline  

\- Background footage rotation  

\- Error handling (missing files, broken TTS, etc.)



---



\## Final line (important):

“Generate the complete automated project blueprint now.”



