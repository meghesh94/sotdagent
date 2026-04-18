"""Gemini-powered song listener — analyzes actual audio from YouTube videos."""

import os
import json
from typing import Optional, List, Dict
from google import genai
from google.genai import types


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

ANALYSIS_PROMPT = """You are a music curator for SOTD (Song of the Day), a service that shares one carefully curated song daily. The goal is DISCOVERY — songs people haven't heard but SHOULD hear. We are NOT a mainstream playlist. You are listening to a song. Analyze the ACTUAL AUDIO:

1. **Song identity**: Confirm the song title and artist from what you hear.
2. **Mood**: The dominant emotional feel (e.g., tender melancholy, anthemic joy, quiet vulnerability). Be specific — not just "sad" or "happy."
3. **Emotional arc**: How does the feeling shift from start to finish? Does it build? Does it have a "moment"?
4. **Vocal quality**: Describe the singer's voice — tone, warmth, texture, technique. Is it raw? Polished? Breathy? Powerful?
5. **Production**: Instruments, arrangement style, mix quality. Is it stripped-down acoustic? Layered and cinematic? Electronic?
6. **The hook**: What would make someone stop scrolling and listen? A lyric, a melody turn, a build-up, a vocal crack?
7. **Vibe in 3 words**: Three words that capture the song's essence.
8. **Popularity estimate**: How well-known is this song? Rate 1-5: 1=virtually unknown (<100K views), 2=niche indie (<1M), 3=moderately known (1-10M), 4=popular (10-100M), 5=mainstream hit (100M+, most people have heard it). Consider the artist's fame too — a lesser-known track by a huge artist is still "known."
9. **SOTD score (1-10)**: Would you text this to a friend unprompted? 1=forgettable, 5=nice but generic, 7=really good, 9=exceptional, 10=life-changing. IMPORTANT: A song that is genuinely exceptional but already widely known should score LOWER (cap at 5) because SOTD is about discovery. The sweet spot is high quality + low popularity.
10. **Similar to**: Name 2-3 artists or songs this reminds you of.
11. **Language**: What language are the lyrics in?

Respond in valid JSON with these exact keys: song_title, artist, mood, emotional_arc, vocal_quality, production, the_hook, vibe_words, popularity, sotd_score, similar_to, language.

Be honest and specific. If the song is mediocre, say so. If the song is a well-known classic or mainstream hit, say so clearly and score it low — we need hidden gems, not greatest hits."""


def _get_client():
    return genai.Client(api_key=GEMINI_API_KEY)


def analyze_song(yt_video_id: str, song_name: str = "", artist: str = "") -> Optional[Dict]:
    """Send a YouTube video to Gemini for audio analysis.

    Returns a dict with mood, vocal_quality, production, etc. or None on failure.
    """
    client = _get_client()
    yt_url = f"https://www.youtube.com/watch?v={yt_video_id}"

    context = ""
    if song_name and artist:
        context = f"\n\nExpected: \"{song_name}\" by {artist}. Confirm if this matches what you hear."

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part(
                            file_data=types.FileData(
                                file_uri=yt_url,
                                mime_type="video/mp4",
                            )
                        ),
                        types.Part(text=ANALYSIS_PROMPT + context),
                    ]
                )
            ],
        )

        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
            elif "```" in text:
                text = text[:text.rfind("```")]
            text = text.strip()

        return json.loads(text)

    except json.JSONDecodeError as e:
        print(f"  [Gemini] JSON parse error for {yt_url}: {e}")
        print(f"  [Gemini] Raw response: {response.text[:300]}")
        return None
    except Exception as e:
        print(f"  [Gemini] Error analyzing {yt_url}: {e}")
        return None


def analyze_batch(songs: List[Dict], max_songs: int = 10) -> List[Dict]:
    """Analyze a batch of songs, adding Gemini analysis to each.

    Each song dict must have 'yt_video_id'. Returns songs with 'gemini' key added.
    """
    # Pre-filter: skip obvious non-songs (instrumentals, backing tracks, compilations)
    skip_words = ["instrumental", "backing track", "karaoke", "compilation", "mix", "playlist", "8d audio", "slowed", "reverb"]
    filtered = []
    for s in songs[:max_songs]:
        title = (s.get("name", "") + " " + s.get("artist", "")).lower()
        if any(w in title for w in skip_words):
            print(f"  [Skip] {s.get('name', '?')} — {s.get('artist', '?')} (non-song)")
            continue
        filtered.append(s)

    analyzed = []
    for i, song in enumerate(filtered):
        vid = song.get("yt_video_id")
        if not vid:
            continue
        print(f"  [Gemini] ({i+1}/{len(filtered)}) Listening to: {song.get('name', '?')} — {song.get('artist', '?')}")
        result = analyze_song(vid, song.get("name", ""), song.get("artist", ""))
        if result:
            song["gemini"] = result
            score = result.get("sotd_score", 0)
            print(f"    → Score: {score}/10 | Mood: {result.get('mood', '?')} | Vibe: {result.get('vibe_words', '?')}")
        else:
            print(f"    → Analysis failed, skipping")
        analyzed.append(song)
    return analyzed


def curate_top_picks(analyzed_songs: List[Dict], top_n: int = 5) -> List[Dict]:
    """From analyzed songs, pick the top N diverse candidates.

    Prioritizes: high SOTD score, mood diversity, artist diversity.
    """
    # Filter to songs that have Gemini analysis and score >= 6
    scored = [s for s in analyzed_songs if s.get("gemini", {}).get("sotd_score", 0) >= 6]
    scored.sort(key=lambda s: s["gemini"]["sotd_score"], reverse=True)

    if not scored:
        print("  [Curate] No songs scored 6+. Returning top by score anyway.")
        scored = [s for s in analyzed_songs if s.get("gemini")]
        scored.sort(key=lambda s: s["gemini"]["sotd_score"], reverse=True)

    # Ensure mood diversity — don't pick two songs with same mood
    picks = []
    seen_moods = set()
    seen_artists = set()

    for s in scored:
        mood = s["gemini"].get("mood", "").lower()
        artist = s.get("artist", "").lower()

        # Skip if we already have a very similar mood (first word match)
        mood_key = mood.split()[0] if mood else ""
        if mood_key in seen_moods and len(picks) < top_n:
            # Allow it if we don't have enough picks, but deprioritize
            continue

        # Skip same artist
        if artist in seen_artists:
            continue

        picks.append(s)
        if mood_key:
            seen_moods.add(mood_key)
        if artist:
            seen_artists.add(artist)

        if len(picks) >= top_n:
            break

    # If we don't have enough, fill from remaining
    if len(picks) < top_n:
        for s in scored:
            if s not in picks:
                picks.append(s)
            if len(picks) >= top_n:
                break

    return picks
