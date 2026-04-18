"""Flask web app for SOTD Music Agent."""

import json
import os
import sys
import threading
import uuid
import webbrowser
from collections import Counter
from datetime import datetime
from queue import Empty

from flask import Flask, Response, jsonify, render_template, request, send_from_directory

# Add parent dir to path so we can import the existing modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from web.discovery_runner import RunConfig, get_event_queue, is_running, start_discovery, force_reset

app = Flask(__name__, template_folder="templates", static_folder="static")

# ── In-memory state ─────────────────────────────────────────────

_discovered_songs = {}

# Playlist-based library: list of {url, platform, playlist_id, title, track_count, tracks}
_playlists = []
_playlist_lock = threading.Lock()

# Background indexing state
_indexing = False
_index_progress = {"done": 0, "total": 0, "current_song": ""}


def _get_all_tracks() -> list[dict]:
    """Get all tracks across all imported playlists (deduped)."""
    seen = set()
    tracks = []
    with _playlist_lock:
        for pl in _playlists:
            for t in pl.get("tracks", []):
                key = (t.get("name", "").lower().strip(), t.get("artist", "").lower().strip())
                if key not in seen and key[0]:
                    seen.add(key)
                    tracks.append(t)
    return tracks


def _build_profile_from_tracks(tracks: list[dict]) -> dict:
    """Build a taste profile from a list of track dicts."""
    artist_counter = Counter()
    genre_counter = Counter()
    for t in tracks:
        if t.get("artist"):
            artist_counter[t["artist"]] += 1
        for g in t.get("genres", []):
            genre_counter[g] += 1

    return {
        "tracks": tracks,
        "track_count": len(tracks),
        "top_artists": [{"name": n, "count": c} for n, c in artist_counter.most_common(20)],
        "top_genres": [g for g, _ in genre_counter.most_common(20)],
    }


# ── Pages ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── API: Audio playback ─────────────────────────────────────────

AUDIO_CACHE_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audio_cache"))

@app.route("/audio/<video_id>.wav")
def serve_audio(video_id):
    return send_from_directory(AUDIO_CACHE_DIR, f"{video_id}.wav", mimetype="audio/wav")


# ── API: Profile ────────────────────────────────────────────────────

@app.route("/api/profile")
def api_profile():
    tracks = _get_all_tracks()
    if not tracks:
        return jsonify({
            "track_count": 0,
            "top_artists": [],
            "top_genres": [],
            "source": "none",
        })
    profile = _build_profile_from_tracks(tracks)
    # Include songs with video IDs for the vinyl grid
    songs_for_grid = [
        {"name": t["name"], "artist": t["artist"], "yt_video_id": t["yt_video_id"]}
        for t in tracks if t.get("yt_video_id")
    ]
    return jsonify({
        "track_count": profile["track_count"],
        "top_artists": profile["top_artists"][:15],
        "top_genres": profile["top_genres"][:15],
        "songs": songs_for_grid,
        "source": "playlists",
    })


# ── API: Playlists ──────────────────────────────────────────────────

@app.route("/api/playlists")
def api_playlists():
    with _playlist_lock:
        return jsonify([{
            "url": pl["url"],
            "platform": pl["platform"],
            "title": pl["title"],
            "track_count": pl["track_count"],
            "playlist_id": pl["playlist_id"],
        } for pl in _playlists])


@app.route("/api/playlists", methods=["POST"])
def api_add_playlist():
    body = request.get_json(silent=True) or {}
    url = body.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    from sources.playlist_import import parse_playlist_url
    parsed = parse_playlist_url(url)
    if not parsed:
        return jsonify({"error": "Unrecognized playlist URL. Supports Spotify and YT Music playlists."}), 400

    # Check for duplicates
    with _playlist_lock:
        for pl in _playlists:
            if pl["playlist_id"] == parsed["playlist_id"]:
                return jsonify({"error": f"Playlist already added: {pl['title']}"}), 409

    # Fetch in background to not block the UI
    def _fetch():
        try:
            from sources.playlist_import import fetch_playlist
            result = fetch_playlist(url)
            with _playlist_lock:
                _playlists.append(result)
            print(f"[Playlist] Added: {result['title']} ({result['track_count']} tracks)")
        except Exception as e:
            print(f"[Playlist] Failed to fetch {url}: {e}")

    thread = threading.Thread(target=_fetch, daemon=True)
    thread.start()

    return jsonify({"ok": True, "message": "Importing playlist...", "playlist_id": parsed["playlist_id"]})


@app.route("/api/playlists/<playlist_id>", methods=["DELETE"])
def api_remove_playlist(playlist_id):
    with _playlist_lock:
        _playlists[:] = [pl for pl in _playlists if pl["playlist_id"] != playlist_id]
    return jsonify({"ok": True})


@app.route("/api/playlists/index", methods=["POST"])
def api_index_playlists():
    """Build MERT index from all imported playlist tracks."""
    global _indexing
    if _indexing:
        return jsonify({"error": "Indexing already in progress"}), 409

    tracks = _get_all_tracks()
    if not tracks:
        return jsonify({"error": "No tracks to index. Add playlists first."}), 400

    _indexing = True

    def _do_index():
        global _indexing
        try:
            from sources.mert_ear import build_library_index
            for t in tracks:
                if not t.get("youtube_link") and t.get("yt_video_id"):
                    t["youtube_link"] = f"https://www.youtube.com/watch?v={t['yt_video_id']}"

            def _on_progress(done, total, song_name):
                _index_progress["done"] = done
                _index_progress["total"] = total
                _index_progress["current_song"] = song_name

            _index_progress["total"] = len(tracks)
            build_library_index(tracks, force=True, on_progress=_on_progress)
            print(f"[MERT] Index rebuilt with {len(tracks)} tracks")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[MERT] Indexing failed: {e}")
        finally:
            _indexing = False

    thread = threading.Thread(target=_do_index, daemon=True)
    thread.start()

    return jsonify({"ok": True, "track_count": len(tracks), "message": "Indexing started..."})


@app.route("/api/playlists/index-status")
def api_index_status():
    if _indexing:
        return jsonify({
            "indexing": True,
            "indexed_count": _index_progress["done"],
            "total": _index_progress["total"],
            "current_song": _index_progress["current_song"],
        })

    from sources.mert_ear import LIBRARY_INDEX_PATH
    import numpy as np
    indexed_count = 0
    if LIBRARY_INDEX_PATH.exists():
        data = np.load(LIBRARY_INDEX_PATH, allow_pickle=True)
        songs = json.loads(str(data["songs"]))
        indexed_count = len(songs)
    return jsonify({
        "indexing": False,
        "indexed_count": indexed_count,
        "total": indexed_count,
        "current_song": "",
    })


# ── API: Queries ────────────────────────────────────────────────────

@app.route("/api/queries")
def api_queries():
    tracks = _get_all_tracks()

    # Radio seeds: actual songs from playlists
    seeds = [{"query": f"{t['name']} {t['artist']}", "name": t["name"], "artist": t["artist"]}
             for t in tracks if t.get("name") and t.get("artist")]

    # Artist exploration: unique artists from playlists
    seen = set()
    artists = []
    for t in tracks:
        a = t.get("artist", "").strip()
        if a and a not in seen:
            artists.append(f"artists similar to {a}")
            seen.add(a)

    return jsonify({
        "radio_seeds": seeds,
        "vibe_queries": [],
        "artist_vibe_queries": artists,
        "era_queries": [],
    })


# ── API: Discovery ──────────────────────────────────────────────────

@app.route("/api/discover/reset", methods=["POST"])
def api_discover_reset():
    force_reset()
    return jsonify({"ok": True})


@app.route("/api/discover", methods=["POST"])
def api_discover():
    if is_running():
        return jsonify({"error": "A discovery run is already active."}), 409

    _discovered_songs.clear()
    body = request.get_json(silent=True) or {}

    config = RunConfig(
        radio_seeds_count=body.get("radio_seeds_count", 8),
        vibe_queries_count=body.get("vibe_queries_count", 8),
        artist_vibe_count=body.get("artist_vibe_count", 5),
        era_queries_count=body.get("era_queries_count", 4),
        listen_count=body.get("listen_count", 15),
        final_picks=body.get("final_picks", 5),
        popularity_min=body.get("popularity_min", 0),
        popularity_max=body.get("popularity_max", 5_000_000),
        year_min=body.get("year_min", 0),
        year_max=body.get("year_max", 2026),
        disabled_queries=body.get("disabled_queries", []),
        skip_words=body.get("skip_words", RunConfig().skip_words),
    )

    # Pass playlist tracks to the runner so it uses them instead of CSV
    tracks = _get_all_tracks()
    run_id = start_discovery(config, library_tracks=tracks if tracks else None)
    return jsonify({"run_id": run_id})


@app.route("/api/discover/stream")
def api_discover_stream():
    def event_stream():
        queue = get_event_queue()
        while True:
            try:
                event = queue.get(timeout=30)
            except Empty:
                yield ":\n\n"  # SSE keepalive
                continue

            # Store discovered songs in memory for approve/skip
            if event.get("type") == "result" and "song" in event:
                song = event["song"]
                _discovered_songs[song["_id"]] = song

            yield f"data: {json.dumps(event)}\n\n"

            if event.get("type") in ("complete", "error"):
                break

    return Response(event_stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── API: Song actions ───────────────────────────────────────────────

@app.route("/api/songs/<song_id>/approve", methods=["POST"])
def api_approve(song_id):
    song = _discovered_songs.get(song_id)
    if not song:
        return jsonify({"error": "Song not found"}), 404

    import inventory
    inventory.add_song({
        "Song Name": song["name"],
        "Artist": song["artist"],
        "Album": song.get("album", ""),
        "Genre": "",
        "Mood": "",
        "Tempo": "",
        "Language": "",
        "Release Year": "",
        "Spotify Link": song.get("spotify_link", ""),
        "YT Music Link": song.get("yt_link", ""),
        "MusicBrainz ID": "",
        "Date Added": datetime.now().strftime("%Y-%m-%d"),
        "Status": "candidate",
        "Date Published": "",
    })

    # Feed back into taste library — add as a track to the "approved" playlist
    approved_track = {
        "name": song["name"],
        "artist": song["artist"],
        "album": song.get("album", ""),
        "yt_video_id": song.get("yt_video_id", ""),
        "yt_link": song.get("yt_link", ""),
        "youtube_link": f"https://www.youtube.com/watch?v={song.get('yt_video_id', '')}",
        "spotify_link": song.get("spotify_link", ""),
    }
    with _playlist_lock:
        # Find or create the "Approved Songs" playlist
        approved_pl = None
        for pl in _playlists:
            if pl.get("playlist_id") == "_approved":
                approved_pl = pl
                break
        if not approved_pl:
            approved_pl = {
                "url": "",
                "platform": "sotd",
                "playlist_id": "_approved",
                "title": "Approved Songs",
                "track_count": 0,
                "tracks": [],
            }
            _playlists.append(approved_pl)
        approved_pl["tracks"].append(approved_track)
        approved_pl["track_count"] = len(approved_pl["tracks"])

    return jsonify({"ok": True, "song": song["name"]})


@app.route("/api/songs/<song_id>/rate", methods=["POST"])
def api_rate(song_id):
    song = _discovered_songs.get(song_id)
    if not song:
        return jsonify({"error": "Song not found"}), 404

    body = request.get_json(silent=True) or {}
    rating = body.get("rating", 0)
    song["rating"] = rating

    # Songs rated 4+ automatically feed into the taste library
    if rating >= 4:
        approved_track = {
            "name": song["name"],
            "artist": song["artist"],
            "album": song.get("album", ""),
            "yt_video_id": song.get("yt_video_id", ""),
            "yt_link": song.get("yt_link", ""),
            "youtube_link": f"https://www.youtube.com/watch?v={song.get('yt_video_id', '')}",
            "spotify_link": song.get("spotify_link", ""),
            "rating": rating,
        }
        with _playlist_lock:
            approved_pl = None
            for pl in _playlists:
                if pl.get("playlist_id") == "_approved":
                    approved_pl = pl
                    break
            if not approved_pl:
                approved_pl = {
                    "url": "",
                    "platform": "sotd",
                    "playlist_id": "_approved",
                    "title": "Approved Songs",
                    "track_count": 0,
                    "tracks": [],
                }
                _playlists.append(approved_pl)
            # Don't double-add
            existing_ids = {t.get("yt_video_id") for t in approved_pl["tracks"]}
            if approved_track["yt_video_id"] not in existing_ids:
                approved_pl["tracks"].append(approved_track)
                approved_pl["track_count"] = len(approved_pl["tracks"])

        # Also write to inventory
        import inventory
        inventory.add_song({
            "Song Name": song["name"],
            "Artist": song["artist"],
            "Album": song.get("album", ""),
            "Genre": "",
            "Mood": "",
            "Tempo": "",
            "Language": "",
            "Release Year": "",
            "Spotify Link": song.get("spotify_link", ""),
            "YT Music Link": song.get("yt_link", ""),
            "MusicBrainz ID": "",
            "Date Added": datetime.now().strftime("%Y-%m-%d"),
            "Status": "candidate",
            "Date Published": "",
        })

    return jsonify({"ok": True, "song": song["name"], "rating": rating})


@app.route("/api/songs/<song_id>/skip", methods=["POST"])
def api_skip(song_id):
    if song_id in _discovered_songs:
        del _discovered_songs[song_id]
    return jsonify({"ok": True})


# ── Run ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = 5555
    print(f"\n  SOTD Music Agent → http://localhost:{port}\n")
    webbrowser.open(f"http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
