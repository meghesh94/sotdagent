"""Telegram messaging for song notifications."""

import requests

import config

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def send_message(text: str, parse_mode: str = "HTML"):
    """Send a message to the configured Telegram chat."""
    resp = requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    })
    resp.raise_for_status()
    return resp.json()


def format_song_message(song: dict) -> str:
    """Format a song dict into a clean Telegram message."""
    name = song.get("Song Name") or song.get("name", "Unknown")
    artist = song.get("Artist") or song.get("artist", "Unknown")
    album = song.get("Album") or song.get("album", "")
    genre = song.get("Genre") or song.get("genre", "")
    mood = song.get("Mood") or song.get("mood", "")
    spotify = song.get("Spotify Link") or song.get("spotify_link", "")
    yt = song.get("YT Music Link") or song.get("yt_link", "")

    lines = [
        f"<b>🎵 Song of the Day</b>",
        f"",
        f"<b>{name}</b> — {artist}",
    ]
    if album:
        lines.append(f"💿 {album}")
    if genre:
        lines.append(f"🏷 {genre}")
    if mood:
        lines.append(f"🎭 {mood}")
    lines.append("")
    if spotify:
        lines.append(f"▶️ <a href=\"{spotify}\">Spotify</a>")
    if yt:
        lines.append(f"▶️ <a href=\"{yt}\">YouTube Music</a>")

    return "\n".join(lines)
