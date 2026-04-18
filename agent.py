#!/usr/bin/env python3
"""Music Agent CLI — two skills, one agent.

Usage:
    python agent.py find                     # Skill 1: discover songs from taste profile
    python agent.py find --query "lo-fi jazz" # Skill 1: manual search
    python agent.py find --artist "Tame Impala"
    python agent.py find --genre "indie"
    python agent.py find --no-listen          # Skip MERT analysis, just search
    python agent.py profile                  # Just print taste profile (no discovery)
    python agent.py index                    # Build MERT library index (one-time setup)
    python agent.py index --force            # Rebuild index from scratch
    python agent.py publish                  # Skill 2: publish all candidates
    python agent.py publish --song "Song" --artist "Artist"  # publish one specific song
    python agent.py candidates               # List current candidates in inventory
"""

import argparse
import sys


def cmd_find(args):
    from skills.find_songs import discover
    songs = discover(
        genre_override=args.genre,
        artist_override=args.artist,
        query_override=args.query,
        listen=not args.no_listen,
        listen_count=args.listen_count,
    )
    if not songs:
        print("No new songs found. Try a different query or check your playlist.")
    return songs


def cmd_profile(args):
    from skills.find_songs import build_taste_profile
    profile = build_taste_profile()
    print(f"\n{'='*60}")
    print("TASTE PROFILE SUMMARY")
    print(f"{'='*60}")
    print(f"Total songs in library: {profile['track_count']}")
    print(f"\nTop 15 Artists:")
    for a in profile["top_artists"][:15]:
        print(f"  {a['count']:3d}x  {a['name']}")
    print(f"\nTop 15 Genres/Moods:")
    for g in profile["top_genres"][:15]:
        print(f"  - {g}")
    return profile


def cmd_publish(args):
    from skills.publish import publish_candidates, publish_specific
    if args.song and args.artist:
        return publish_specific(args.song, args.artist)
    else:
        return publish_candidates(limit=args.limit)


def cmd_index(args):
    from skills.find_songs import build_taste_profile
    from sources.mert_ear import build_library_index
    profile = build_taste_profile()
    build_library_index(profile["tracks"], force=args.force)


def cmd_candidates(args):
    import inventory
    candidates = inventory.get_candidates()
    if not candidates:
        print("No candidates in inventory. Run 'find' first.")
        return
    print(f"\n{'='*60}")
    print(f"CANDIDATES ({len(candidates)} songs)")
    print(f"{'='*60}")
    for i, s in enumerate(candidates, 1):
        print(f"\n{i}. {s['Song Name']} — {s['Artist']}")
        if s.get("Genre"):
            print(f"   Genre: {s['Genre']}")
        if s.get("Mood"):
            print(f"   Mood: {s['Mood']}")
        if s.get("Spotify Link"):
            print(f"   Spotify: {s['Spotify Link']}")
        if s.get("YT Music Link"):
            print(f"   YT Music: {s['YT Music Link']}")


def main():
    parser = argparse.ArgumentParser(description="Music Agent — Find and publish songs")
    sub = parser.add_subparsers(dest="command")

    # find
    p_find = sub.add_parser("find", help="Skill 1: Discover new songs")
    p_find.add_argument("--query", "-q", help="Free-text search query")
    p_find.add_argument("--artist", "-a", help="Search for a specific artist")
    p_find.add_argument("--genre", "-g", help="Search for a specific genre")
    p_find.add_argument("--no-listen", action="store_true", help="Skip Gemini audio analysis")
    p_find.add_argument("--listen-count", type=int, default=15, help="Number of songs for Gemini to listen to (default 15)")
    p_find.set_defaults(func=cmd_find)

    # profile
    p_profile = sub.add_parser("profile", help="Print taste profile from your playlist")
    p_profile.set_defaults(func=cmd_profile)

    # publish
    p_pub = sub.add_parser("publish", help="Skill 2: Publish songs to playlists + Telegram")
    p_pub.add_argument("--song", "-s", help="Specific song name to publish")
    p_pub.add_argument("--artist", "-a", help="Artist of the specific song")
    p_pub.add_argument("--limit", "-l", type=int, default=5, help="Max songs to publish")
    p_pub.set_defaults(func=cmd_publish)

    # index
    p_idx = sub.add_parser("index", help="Build MERT library index (one-time)")
    p_idx.add_argument("--force", action="store_true", help="Rebuild even if index exists")
    p_idx.set_defaults(func=cmd_index)

    # candidates
    p_cand = sub.add_parser("candidates", help="List candidate songs in inventory")
    p_cand.set_defaults(func=cmd_candidates)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
