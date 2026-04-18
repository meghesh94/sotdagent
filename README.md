# SOTD Music Agent

A music discovery agent that learns your taste from playlists and finds songs you haven't heard yet.

**How it works:**
1. Add your Spotify or YouTube Music playlists
2. Your taste profile builds automatically — artists, songs, acoustic DNA
3. Hit "Run Discovery" — the agent searches for new music, filters by view count and release year, then scores candidates by how they *sound* compared to your library
4. Rate songs 1-5 stars — high-rated songs feed back into your profile, sharpening future discovery

## Quick Start

```bash
# Clone
git clone https://github.com/meghesh94/sotdagent.git
cd sotdagent

# Install dependencies
pip3 install -r requirements.txt

# Install yt-dlp (for audio downloads + playlist import)
brew install yt-dlp   # macOS
# or: pip3 install yt-dlp

# Install ffmpeg (for audio processing)
brew install ffmpeg   # macOS

# Copy env file and fill in your keys (optional — discovery works without these)
cp .env.example .env

# Start the web UI
python3 -m web.app
```

Open **http://localhost:5555** and paste a playlist URL to get started.

## What You Need

**Required:**
- Python 3.9+
- `yt-dlp` and `ffmpeg` installed and on PATH

**Optional (for full features):**
- Spotify API credentials → enables popularity filter + publish to Spotify
- Google Sheets service account → enables inventory tracking
- Telegram bot token → enables song notifications
- YT Music OAuth → enables publish to YT Music playlist

Without these, the core discovery loop (import playlist → discover → rate) works fine.

## Tech Stack

- **MERT-v1-95M** — music audio understanding model (380MB, runs on CPU, no GPU needed). Embeds songs as 768-dim vectors for acoustic similarity scoring
- **yt-dlp** — downloads 60-second audio clips + fetches view counts and release dates
- **Flask** — web server
- **Alpine.js** — reactive UI (loaded from CDN, no build step)

## CLI (legacy)

```bash
python3 agent.py find              # Discover new songs
python3 agent.py find --no-listen  # Search only, skip MERT analysis
python3 agent.py index             # Build MERT library index
python3 agent.py index --force     # Rebuild index from scratch
python3 agent.py publish           # Publish candidates to playlists + Telegram
python3 agent.py candidates        # List current candidates
python3 agent.py profile           # Print taste profile
```
