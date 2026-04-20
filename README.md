# SOTD Music Agent

A music discovery agent that learns your taste from playlists and finds songs you haven't heard yet.

**How it works:**
1. Add your Spotify or YouTube Music playlists
2. Your taste profile builds automatically — artists, songs, acoustic DNA
3. Hit "Run Discovery" — the agent searches for new music, filters by view count and release year, then scores candidates by how they *sound* compared to your library
4. Rate songs 1–5 stars — high-rated songs feed back into your profile, sharpening future discovery

## Quick Start

```bash
git clone https://github.com/meghesh94/sotdagent.git
cd sotdagent

pip install -r requirements.txt

# Optional: add Spotify / YT Music credentials
cp .env.example .env

python -m web.app
```

> If `pip install` complains about `externally-managed-environment` (newer macOS/Linux), use a venv:
> `python -m venv venv && source venv/bin/activate` (Windows: `venv\Scripts\activate`), then re-run `pip install`.

Open **http://localhost:5555** and paste a playlist URL to get started.

## Requirements

- **Python 3.9+**
- Everything else (`yt-dlp`, `ffmpeg`, `torch`, `torchcodec`, MERT) is installed via `pip install -r requirements.txt`. No system packages needed.

### Optional integrations

Edit `.env` to unlock:

- **Spotify** (`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_PLAYLIST_ID`) — popularity filter + publish to a Spotify playlist. Get keys at https://developer.spotify.com/dashboard
- **YT Music** (`YTMUSIC_AUTH_FILE`, `YTMUSIC_PLAYLIST_ID`) — publish to a YT Music playlist. Run `ytmusicapi oauth` to generate the auth file.

Without these, the core loop (import → discover → rate) works fine.

## Tech Stack

- **MERT-v1-95M** — music audio-understanding model (~380 MB, CPU-only). Embeds clips as 768-dim vectors for acoustic similarity scoring.
- **yt-dlp** — playlist import + 60-second audio clips + view counts / release dates.
- **Flask** — web server. **Alpine.js** (CDN) — reactive UI, no build step.
- **SQLite** — local store for ratings and song metadata.

## Troubleshooting

**MERT model download is slow** — first run pulls ~380 MB from Hugging Face into `~/.cache/huggingface/`. Subsequent runs use the cache.

**`ImportError: TorchCodec is required`** — your `pip install` predates `torchcodec` being added. Run `pip install -r requirements.txt` again.

**yt-dlp "No supported JavaScript runtime" warning** — harmless; YouTube downloads still work. For best reliability install [Deno](https://deno.land) or Node.js and make sure it's on `PATH`.

**Windows encoding errors on startup** — already handled: the app forces UTF-8 stdout/stderr. If you still see `UnicodeEncodeError`, set `PYTHONUTF8=1` before running.
