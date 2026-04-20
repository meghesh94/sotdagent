"""Sources package — shared utilities for yt-dlp and ffmpeg."""

import shutil
import sys


def yt_dlp_cmd():
    """Return the yt-dlp command as a list. Prefers binary on PATH, falls back to python -m."""
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    # Fallback: call as python module (works when installed via pip but not on PATH)
    return [sys.executable, "-m", "yt_dlp"]


def check_ffmpeg():
    """Check if ffmpeg is available. Prints a warning if not."""
    if not shutil.which("ffmpeg"):
        print(
            "\n[WARNING] ffmpeg not found on PATH.\n"
            "  Audio download/conversion will fail.\n"
            "  Install: brew install ffmpeg (macOS) or sudo apt install ffmpeg (Linux)\n"
        )
        return False
    return True
