"""Sources package — shared utilities for yt-dlp and ffmpeg."""

import os
import shutil
import sys


def _ffmpeg_dir():
    """Return the directory containing the ffmpeg binary from imageio-ffmpeg, or None."""
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        return os.path.dirname(get_ffmpeg_exe())
    except ImportError:
        return None


def yt_dlp_cmd():
    """Return the yt-dlp command as a list. Prefers binary on PATH, falls back to python -m."""
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    return [sys.executable, "-m", "yt_dlp"]


def ffmpeg_env():
    """Return an env dict that ensures yt-dlp can find ffmpeg.

    Prepends the imageio-ffmpeg binary dir to PATH so yt-dlp's subprocess
    calls to ffmpeg just work, even without a system install.
    """
    env = os.environ.copy()
    ffdir = _ffmpeg_dir()
    if ffdir:
        env["PATH"] = ffdir + os.pathsep + env.get("PATH", "")
    return env


def check_ffmpeg():
    """Check if ffmpeg is available (system or imageio-ffmpeg). Warns if not."""
    if shutil.which("ffmpeg"):
        return True
    if _ffmpeg_dir():
        return True
    print(
        "\n[WARNING] ffmpeg not found.\n"
        "  Audio download/conversion will fail.\n"
        "  It should have been installed via: pip install imageio-ffmpeg\n"
    )
    return False
