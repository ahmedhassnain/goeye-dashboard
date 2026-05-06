# social_media_parser.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
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

def extract_archive_date(deltadata_path):
    folder_name = os.path.basename(os.path.dirname(deltadata_path))
    date_part = folder_name.split("-")[0]
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

def load_social_media(deltadata_path):
    archive_date = extract_archive_date(deltadata_path)
    print(f"Processing social media for archive date: {archive_date}")

    filepath = os.path.join(deltadata_path, "curr_social_media.csv")

    if not os.path.exists(filepath):
        print("  curr_social_media.csv not found - skipping.")
        return

    records = []

    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rtt_avg_raw = parse_float(row.get("rtt_avg"))
            rtt_min_raw = parse_float(row.get("rtt_min"))
            rtt_max_raw = parse_float(row.get("rtt_max"))
            rtt_median_raw = parse_float(row.get("rtt_median"))
            rtt_std_raw = parse_float(row.get("rtt_std"))
            record = RawSocialMedia(
                unit_id=parse_int(row.get("unit_id")),
                archive_date=archive_date,
                dtime_local=parse_timestamp(row.get("dtime_local")),
                dtime_utc=parse_timestamp(row.get("dtime_utc")),
                error_code=row.get("error_code", "").strip() or None,
                service=row.get("service", "").strip() or None,
                media=row.get("media", "").strip() or None,
                direction=row.get("direction", "").strip() or None,
                target=row.get("target", "").strip() or None,
                address=row.get("address", "").strip() or None,
                rtt_avg=rtt_avg_raw / 1000 if rtt_avg_raw is not None else None,
                rtt_min=rtt_min_raw / 1000 if rtt_min_raw is not None else None,
                rtt_max=rtt_max_raw / 1000 if rtt_max_raw is not None else None,
                rtt_median=rtt_median_raw / 1000 if rtt_median_raw is not None else None,
                rtt_std=rtt_std_raw / 1000 if rtt_std_raw is not None else None,
                successes=parse_int(row.get("successes")),
                failures=parse_int(row.get("failures")),
            )
            records.append(record)
    if len(records) == 0:
        print("  curr_social_media.csv is empty - skipping.")
        return
    session = SessionLocal()
    try:
        for record in records:
            session.add(record)
        session.commit()
        print(f"  curr_social_media: {len(records)} rows loaded.")
    except Exception as e:
        session.rollback()
        print(f"  Error loading social media: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    load_social_media(
        r"path\to\deltadata"  # replace with the actual extracted archive path
    )