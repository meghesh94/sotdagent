"""Skill 2: Publish / Update Playlists + Send Message.

Takes approved songs from inventory and:
- Adds to Spotify playlist
- Adds to YT Music playlist
- Sends formatted message to Telegram
- Updates inventory status
"""

import inventory
import telegram_bot
from sources import spotify, ytmusic


def _extract_spotify_uri(link: str) -> str | None:
    """Extract Spotify track URI from a Spotify link."""
    # e.g. https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6
    if "open.spotify.com/track/" in link:
        track_id = link.split("/track/")[-1].split("?")[0]
        return f"spotify:track:{track_id}"
    return None


def _extract_yt_video_id(link: str) -> str | None:
    """Extract video ID from a YT Music link."""
    if "watch?v=" in link:
        return link.split("watch?v=")[-1].split("&")[0]
    return None


def publish_song(song: dict) -> dict:
    """Publish a single song to all platforms.

    Args:
        song: A dict with inventory fields (Song Name, Artist, Spotify Link, etc.)

    Returns:
        dict with results for each platform.
    """
    name = song.get("Song Name", "")
    artist = song.get("Artist", "")
    results = {"song": f"{name} — {artist}", "spotify": False, "ytmusic": False, "telegram": False, "inventory": False}

    # 1. Add to Spotify playlist
    spotify_link = song.get("Spotify Link", "")
    spotify_uri = _extract_spotify_uri(spotify_link)
    if spotify_uri:
        try:
            spotify.add_to_playlist([spotify_uri])
            results["spotify"] = True
            print(f"  [Spotify] Added: {name}")
        except Exception as e:
            print(f"  [Spotify] Failed: {e}")
    else:
        print(f"  [Spotify] No link available for: {name}")

    # 2. Add to YT Music playlist
    yt_link = song.get("YT Music Link", "")
    video_id = _extract_yt_video_id(yt_link)
    if video_id:
        try:
            ytmusic.add_to_playlist([video_id])
            results["ytmusic"] = True
            print(f"  [YT Music] Added: {name}")
        except Exception as e:
            print(f"  [YT Music] Failed: {e}")
    else:
        print(f"  [YT Music] No link available for: {name}")

    # 3. Send Telegram message
    try:
        msg = telegram_bot.format_song_message(song)
        telegram_bot.send_message(msg)
        results["telegram"] = True
        print(f"  [Telegram] Sent: {name}")
    except Exception as e:
        print(f"  [Telegram] Failed: {e}")

    # 4. Update inventory
    try:
        inventory.mark_as_published(name, artist)
        results["inventory"] = True
        print(f"  [Inventory] Marked as sent: {name}")
    except Exception as e:
        print(f"  [Inventory] Failed: {e}")

    return results


def publish_candidates(limit: int = 5) -> list[dict]:
    """Publish all current candidates (or up to limit).

    This is the main entry for Skill 2 — it grabs candidates from the
    inventory and publishes each one.
    """
    candidates = inventory.get_candidates()
    if not candidates:
        print("[Skill 2] No candidates found in inventory.")
        return []

    to_publish = candidates[:limit]
    print(f"[Skill 2] Publishing {len(to_publish)} songs...")

    all_results = []
    for song in to_publish:
        result = publish_song(song)
        all_results.append(result)

    # Print summary
    print(f"\n[Skill 2] Done. Results:")
    for r in all_results:
        status = []
        if r["spotify"]:
            status.append("Spotify")
        if r["ytmusic"]:
            status.append("YT Music")
        if r["telegram"]:
            status.append("Telegram")
        if r["inventory"]:
            status.append("Inventory")
        print(f"  {r['song']}: {', '.join(status) or 'all failed'}")

    return all_results


def publish_specific(song_name: str, artist: str) -> dict:
    """Publish a specific song by name and artist."""
    songs = inventory.get_all_songs()
    match = None
    for s in songs:
        if s["Song Name"].lower().strip() == song_name.lower().strip() and \
           s["Artist"].lower().strip() == artist.lower().strip():
            match = s
            break

    if not match:
        print(f"[Skill 2] Song not found: {song_name} — {artist}")
        return {}

    return publish_song(match)
