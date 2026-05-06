#game_latency_parser.py
import sys
import os
# Cannot run python file inside subfolder without having this approach.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
from datetime import datetime, date
from database import SessionLocal
from datetime import datetime
from database import SessionLocal, engine
from models.base import Base
from models.units import Unit
from models.applications import Application
from models.scopes import Scope
from models.scope_units import ScopeUnit
from models.raw_game_latency import RawGameLatency
from models.raw_social_media import RawSocialMedia
from models.raw_video_conferencing import RawVideoConferencing
from models.raw_disconnection import RawDisconnection
from models.raw_dns import RawDns
from models.daily_aggregates import DailyAggregate
from models.hourly_aggregates import HourlyAggregate

GAME_FILES = [
    "curr_among_us",
    "curr_apex_legends",
    "curr_bfv",
    "curr_cod",
    "curr_counterstrike2",
    "curr_diablo3",
    "curr_diablo4",
    "curr_dota2",
    "curr_efootball_2024",
    "curr_fc24",
    "curr_fifa21",
    "curr_fortnite",
    "curr_free_fire_max",
    "curr_gears5",
    "curr_halo_infinite",
    "curr_hearthstone",
    "curr_heroes_of_the_storm",
    "curr_honor_of_kings",
    "curr_league_of_legends",
    "curr_mobile_legends_bang_bang",
    "curr_overwatch",
    "curr_pubg",
    "curr_pubg_mobile",
    "curr_rainbow_six_siege",
    "curr_roblox",
    "curr_rocket_league",
    "curr_starcraft2",
    "curr_valorant",
    "curr_world_of_warcraft",
]

# We will be extracting time from this function.
def extract_archive_date(deltadata_path):
    # os.path.dirname = gets parent folder of the directory.
    # os.path.basename = gets folder name without the full path.
    folder_name = os.path.basename(os.path.dirname(deltadata_path))
    date_part = folder_name.split("-")[0]
    # Ex: 20260311 from folder name => date(2026, 3, 11)
    return datetime.strptime(date_part, "%Y%m%d").date()

def parse_timestamp(value):
    if not value or value.strip() == "":
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

def parse_float(value):
    try:
        return float(value) if value and value.strip() != "" else None
    except ValueError:
        return None

def parse_int(value):
    try:
        return int(value) if value and value.strip() != "" else None
    except ValueError:
        return None

def parse_game_file(filepath, app_key, archive_date, session):
    if not os.path.exists(filepath):
        print(f"  Skipping {app_key} - file not found.")
        return 0

    records = []
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = RawGameLatency(
                unit_id=parse_int(row.get("unit_id")),
                app_key=app_key,
                archive_date=archive_date,
                dtime_local=parse_timestamp(row.get("dtime_local") or row.get("dtime")),
                dtime_utc=parse_timestamp(row.get("dtime_utc")),
                error_code=row.get("error_code", "").strip() or None,
                provider=row.get("provider", "").strip() or None,
                region=row.get("region", "").strip() or None,
                datacenter=row.get("datacenter", "").strip() or None,
                address=row.get("address", "").strip() or None,
                rtt_avg=parse_float(row.get("rtt_avg")),
                rtt_min=parse_float(row.get("rtt_min")),
                rtt_max=parse_float(row.get("rtt_max")),
                rtt_std=parse_float(row.get("rtt_std")),
                hop_count=parse_int(row.get("hop_count")),
                num_successes=parse_int(row.get("num_successes")),
                num_failures=parse_int(row.get("num_failures")),
                successes=parse_int(row.get("successes")),
                failures=parse_int(row.get("failures")),
            )
            records.append(record)

    if len(records) == 0:
        print(f"  Skipping {app_key} - file empty.")
        return 0

    for record in records:
        session.add(record)

    return len(records)

def load_game_latency(deltadata_path):
    archive_date = extract_archive_date(deltadata_path)
    print(f"Processing game latency for archive date: {archive_date}")
    session = SessionLocal()
    total_rows = 0

    try:
        for app_key in GAME_FILES:
            filepath = os.path.join(deltadata_path, f"{app_key}.csv")
            rows = parse_game_file(filepath, app_key, archive_date, session)
            total_rows += rows
            if rows > 0:
                print(f"  {app_key}: {rows} rows loaded.")
        session.commit()
        print(f"Game latency loading complete. Total rows: {total_rows}")
    except Exception as e:
        session.rollback()
        print(f"Error loading game latency: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    load_game_latency(
        r"path\to\deltadata"  # replace with the actual extracted archive path
    )