"""Skill 1: Find Songs + Add to Inventory.

Reads the SOTD song library CSV and taste-dna.md to discover new songs.
"""

import csv
import random
from collections import Counter
from datetime import datetime

import config


# ── CSV library loading ──────────────────────────────────────────────

def load_library_csv(csv_path: str = None) -> list[dict]:
    path = csv_path or config.SONG_LIBRARY_CSV
    tracks = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("Song Title", "").strip()
            artist = row.get("Singer/Band", "").strip()
            if not title:
                continue
            tracks.append({
                "name": title,
                "artist": artist,
                "genres": [g.strip().lower() for g in row.get("Genre/Moods", "").split(",") if g.strip()],
                "spotify_link": row.get("Spotify Link", "").strip(),
                "youtube_link": row.get("YouTube Link", "").strip(),
            })
    return tracks


def build_taste_profile(csv_path: str = None) -> dict:
    tracks = load_library_csv(csv_path)
    print(f"[Taste] Loaded {len(tracks)} songs from CSV.")

    artist_counter = Counter()
    for t in tracks:
        if t["artist"]:
            artist_counter[t["artist"]] += 1

    top_artists = [{"name": name, "count": count} for name, count in artist_counter.most_common(20)]

    genre_counter = Counter()
    for t in tracks:
        for g in t["genres"]:
            genre_counter[g] += 1
    top_genres = [g for g, _ in genre_counter.most_common(20)]

    return {
        "tracks": tracks,
        "top_artists": top_artists,
        "top_genres": top_genres,
        "track_count": len(tracks),
    }


# ── Search query generation ──────────────────────────────────────────

RADIO_SEEDS = [
    # Indie folk / stomp and holler
    ("Bloom", "The Paper Kites"),
    ("The Night We Met", "Lord Huron"),
    ("Sedona", "Houndmouth"),
    ("Awake My Soul", "Mumford And Sons"),
    ("Walls", "The Lumineers"),
    ("Hero", "Family of the Year"),
    # Atmospheric / cinematic
    ("Apocalypse", "Cigarettes After Sex"),
    ("Cold Little Heart", "Michael Kiwanuka"),
    ("My tears are becoming a sea", "M83"),
    ("On the Sea", "Beach House"),
    ("Your Hand in Mine", "Explosions in the Sky"),
    # Indian indie / sufi
    ("Baarishein", "Anuv Jain"),
    ("Husna", "Piyush Mishra"),
    ("Alag Aasmaan", "Anuv Jain"),
    ("Ghalat Fehmi", "Asim Azhar"),
    ("Ranjish Hi Sahi", "Ali Sethi"),
    # New wave hindi/urdu indie
    ("Bairan", "Banjaare"),
    ("Ji Huzoor", "Sparsh"),
    ("Ae Ajnabi", "Coke Studio Bharat"),
    ("Mere Ho Tum", "Prabhakar Raj"),
    # Small indie discoveries
    ("Hammer & Bones", "Beluga Lagoon"),
    ("Runaway", "Daniel Leggs"),
    ("Ordinary", "Alex Warren"),
    # Soulful / classic
    ("Mystery of Love", "Sufjan Stevens"),
    ("La Vie En Rose", "Emily Watts"),
    ("Wonderful Tonight", "Eric Clapton"),
    ("Norwegian Wood", "Beatles"),
    # Energetic / anthem
    ("Sweet Disposition", "The Temper Trap"),
    ("Sit Next to Me", "Foster The People"),
    ("Alive", "Empire of the Sun"),
    ("Burn The House Down", "AJR"),
]

VIBE_QUERIES = [
    "indie songs that feel like a road trip",
    "songs that feel like a warm hug",
    "underrated indie folk songs",
    "songs with beautiful build up",
    "melancholic indie songs late night",
    "stomp and clap indie anthems",
    "atmospheric dream pop songs",
    "soulful indie songs with raw vocals",
    "songs that give you chills",
    "hidden gem indie rock songs",
    "beautiful acoustic songs undiscovered",
    "songs like The Lumineers but less famous",
    "indian indie songs soulful",
    "sufi songs modern take",
    "songs that sound like a movie soundtrack",
    "indie songs with crescendo ending",
    "bittersweet love songs indie",
    "campfire songs indie folk",
    "chill songs with deep lyrics",
    "songs that make you feel nostalgic",
    "indie bands similar to Lord Huron",
    "artists like Anuv Jain hindi indie",
    "songs like Cigarettes After Sex dreamy",
    "folk rock songs with heart",
    "new indie discoveries this year",
    "raw hindi indie songs 2025 2026",
    "coke studio bharat best performances",
    "small indie artists emotional songs",
    "songs like Banjaare hindi indie",
    "irish indie folk bands undiscovered",
    "intimate acoustic hindi songs new",
    "songs that feel like coming home",
    "indie songs under 1 million views",
    "emotional storytelling pop songs",
]

ARTIST_VIBE_QUERIES = [
    "bands like Houndmouth folk rock",
    "artists similar to Rainbow Kitten Surprise",
    "music like Lord Huron western indie",
    "bands similar to Of Monsters and Men",
    "singers like Prateek Kuhad",
    "artists similar to WILD stomp and holler",
    "bands like The Paper Kites gentle indie",
    "music like Still Corners dreamy",
    "artists like Kodaline emotional rock",
    "singers like Anuv Jain hindi",
    "bands like Foster The People indie",
    "music similar to Beach House",
    "artists like Cage The Elephant",
    "indian bands like The Yellow Diary",
    "artists similar to Mumford and Sons",
    "artists like Banjaare hindi indie raw",
    "bands like Beluga Lagoon indie folk",
    "singers like Sparsh hindi acoustic",
    "music like Kingfishr irish indie",
    "artists like Daniel Leggs emotional indie",
    "bands like Seafret atmospheric indie",
    "singers like Alex Warren storytelling pop",
]

ERA_QUERIES = [
    "best indie folk songs 2025 2026",
    "new stomp and holler songs",
    "underrated bollywood songs 2025",
    "indie hindi songs 2026 new releases",
    "dream pop songs 2025 2026",
    "modern folk rock gems",
    "new atmospheric indie 2026",
    "fresh indie pop discoveries 2026",
    "coke studio bharat season 2025 2026",
    "new hindi indie artists 2025",
    "best indie folk 2025 undiscovered",
    "irish folk indie new releases 2025 2026",
    "raw acoustic indie 2025",
]


def generate_search_queries(profile: dict) -> list[dict]:
    queries = []

    # Round 1: Radio seeds (8 per run for broader coverage)
    for name, artist in random.sample(RADIO_SEEDS, min(8, len(RADIO_SEEDS))):
        queries.append({"query": f"{name} {artist}", "source": "ytmusic_radio", "strategy": "radio_seed"})

    # Round 2: Vibe searches (8 per run)
    for vq in random.sample(VIBE_QUERIES, min(8, len(VIBE_QUERIES))):
        queries.append({"query": vq, "source": "ytmusic", "strategy": "vibe_search"})

    # Round 3: Artist vibe (5 per run)
    for aq in random.sample(ARTIST_VIBE_QUERIES, min(5, len(ARTIST_VIBE_QUERIES))):
        queries.append({"query": aq, "source": "ytmusic", "strategy": "artist_vibe"})

    # Round 4: Era searches (4 per run)
    for eq in random.sample(ERA_QUERIES, min(4, len(ERA_QUERIES))):
        queries.append({"query": eq, "source": "ytmusic", "strategy": "genre_era"})

    random.shuffle(queries)
    return queries


# ── Search execution ─────────────────────────────────────────────────

def search_all(queries: list[dict]) -> list[dict]:
    from sources import ytmusic
    raw = []
    for q in queries:
        try:
            if q["source"] == "ytmusic_radio":
                yt_results = ytmusic.search_songs(q["query"], limit=1)
                if yt_results and yt_results[0].get("yt_video_id"):
                    radio = ytmusic.get_watch_playlist(yt_results[0]["yt_video_id"])
                    raw += radio
                    print(f"  [Radio] {q['query'][:45]}: {len(radio)} songs")
            else:
                results = ytmusic.search_songs(q["query"], limit=20)
                raw += results
                print(f"  [Search] {q['query'][:45]}: {len(results)} songs")
        except Exception as e:
            print(f"  [error] {q['query'][:30]}: {e}")
    return raw


def deduplicate(raw: list[dict], known_keys: set) -> list[dict]:
    seen = set(known_keys)
    unique = []
    for c in raw:
        key = (c.get("name", "").lower().strip(), c.get("artist", "").lower().strip())
        if key not in seen and key[0] and key[1]:
            seen.add(key)
            unique.append(c)
    return unique


def discover(genre_override=None, artist_override=None, query_override=None, csv_path=None, listen=True, listen_count=15):
    """Run discovery pipeline. If listen=True, Gemini analyzes top candidates."""
    import inventory
    profile = build_taste_profile(csv_path)
    existing_keys = inventory.get_existing_keys()
    library_keys = {(t["name"].lower().strip(), t["artist"].lower().strip()) for t in profile["tracks"]}

    # Also exclude the reference songs
    ref_keys = {(name.lower(), artist.lower()) for name, artist in RADIO_SEEDS}
    known_keys = existing_keys | library_keys | ref_keys

    if query_override:
        queries = [{"query": query_override, "source": "ytmusic", "strategy": "manual"}]
    elif artist_override:
        queries = [{"query": f"artists similar to {artist_override}", "source": "ytmusic", "strategy": "manual"}]
    elif genre_override:
        queries = [{"query": f"best {genre_override} songs undiscovered", "source": "ytmusic", "strategy": "manual"}]
    else:
        queries = generate_search_queries(profile)

    print(f"\n[Discovery] Running {len(queries)} queries...")
    raw = search_all(queries)
    unique = deduplicate(raw, known_keys)
    print(f"\n[Discovery] {len(unique)} unique new songs (from {len(raw)} raw)")

    if not listen or not unique:
        return unique

    # MERT listens to a sample and scores by acoustic similarity to library
    from sources.mert_ear import analyze_batch, curate_top_picks

    sample = random.sample(unique, min(listen_count, len(unique)))
    print(f"\n[MERT] Analyzing {len(sample)} songs against your library...")
    analyzed = analyze_batch(sample, library_tracks=profile["tracks"], max_songs=listen_count)

    picks = curate_top_picks(analyzed, top_n=config.SONGS_PER_RUN)
    print(f"\n[Curated] Top {len(picks)} picks:")
    for i, p in enumerate(picks):
        m = p.get("mert", {})
        closest = m.get("closest_songs", [])
        print(f"  {i+1}. {p.get('name')} — {p.get('artist')}")
        print(f"     Similarity: {m.get('similarity_top5', '?')} (top5 avg) | {m.get('similarity_max', '?')} (max)")
        if closest:
            print(f"     Sounds like: {closest[0]['name']} — {closest[0]['artist']} ({closest[0]['similarity']})")
        print()

    return picks
