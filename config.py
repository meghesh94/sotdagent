import os
from dotenv import load_dotenv

load_dotenv()

# Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
SPOTIFY_PLAYLIST_ID = os.getenv("SPOTIFY_PLAYLIST_ID")  # playlist to publish TO
SPOTIFY_SOURCE_PLAYLIST_ID = os.getenv("SPOTIFY_SOURCE_PLAYLIST_ID")  # optional, if you want to pull from Spotify directly
SPOTIFY_SCOPE = "playlist-modify-public playlist-modify-private playlist-read-private"

# Song library CSV (your existing curated library)
SONG_LIBRARY_CSV = os.getenv("SONG_LIBRARY_CSV", os.path.expanduser("~/Downloads/SOTD Song Bank - Song Bank.csv"))

# Google Sheets
GOOGLE_SHEETS_CREDS_FILE = os.getenv("GOOGLE_SHEETS_CREDS_FILE", "credentials.json")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Song Inventory")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# YT Music
YTMUSIC_AUTH_FILE = os.getenv("YTMUSIC_AUTH_FILE", "oauth.json")
YTMUSIC_PLAYLIST_ID = os.getenv("YTMUSIC_PLAYLIST_ID")

# Gemini (audio analysis)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Defaults
SONGS_PER_RUN = 5
VALID_GENRES = [
    "pop", "rock", "hip-hop", "r&b", "jazz", "classical", "electronic",
    "indie", "folk", "country", "latin", "bollywood", "punjabi", "lo-fi",
    "soul", "funk", "reggae", "metal", "blues", "ambient"
]
VALID_MOODS = [
    "happy", "sad", "energetic", "chill", "romantic", "melancholic",
    "upbeat", "dark", "dreamy", "nostalgic", "motivational", "peaceful"
]
