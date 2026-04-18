"""Google Sheets inventory — the central database for both skills."""

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

HEADERS = [
    "Song Name", "Artist", "Album", "Genre", "Mood", "Tempo",
    "Language", "Release Year", "Spotify Link", "YT Music Link",
    "MusicBrainz ID", "Date Added", "Status", "Date Published"
]


def _get_sheet():
    creds = Credentials.from_service_account_file(config.GOOGLE_SHEETS_CREDS_FILE, scopes=SCOPES)
    gc = gspread.authorize(creds)
    try:
        sh = gc.open(config.GOOGLE_SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(config.GOOGLE_SHEET_NAME)
        sh.share("", perm_type="anyone", role="writer")  # adjust sharing as needed
    ws = sh.sheet1
    # Ensure headers exist
    if not ws.row_values(1):
        ws.append_row(HEADERS)
    return ws


def get_all_songs():
    """Return all rows as list of dicts."""
    ws = _get_sheet()
    records = ws.get_all_records()
    return records


def get_existing_keys():
    """Return a set of (song_name_lower, artist_lower) for dedup."""
    songs = get_all_songs()
    return {(s["Song Name"].lower().strip(), s["Artist"].lower().strip()) for s in songs}


def add_song(song: dict):
    """Append a song row. song dict should have keys matching HEADERS."""
    ws = _get_sheet()
    row = [song.get(h, "") for h in HEADERS]
    ws.append_row(row)
    return row


def mark_as_published(song_name: str, artist: str):
    """Find the row by song+artist and set Status=sent, Date Published=today."""
    ws = _get_sheet()
    records = ws.get_all_records()
    for i, r in enumerate(records):
        if r["Song Name"].lower().strip() == song_name.lower().strip() and \
           r["Artist"].lower().strip() == artist.lower().strip():
            row_num = i + 2  # +1 for header, +1 for 1-indexed
            status_col = HEADERS.index("Status") + 1
            date_col = HEADERS.index("Date Published") + 1
            ws.update_cell(row_num, status_col, "sent")
            ws.update_cell(row_num, date_col, datetime.now().strftime("%Y-%m-%d"))
            return True
    return False


def get_candidates():
    """Return songs with Status == 'candidate'."""
    songs = get_all_songs()
    return [s for s in songs if s.get("Status", "").lower() == "candidate"]
