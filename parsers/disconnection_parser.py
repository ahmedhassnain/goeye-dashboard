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

def parse_int(value):
    try:
        return int(value) if value and value.strip() != "" else None
    except ValueError:
        return None

def parse_float(value):
    try:
        return float(value) if value and value.strip() != "" else None
    except ValueError:
        return None

def load_disconnection(deltadata_path):
    archive_date = extract_archive_date(deltadata_path)
    print(f"Processing disconnections for archive date: {archive_date}")

    filepath = os.path.join(deltadata_path, "curr_disconnection.csv")

    if not os.path.exists(filepath):
        print("  curr_disconnection.csv not found - skipping.")
        return

    records = []

    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            duration_microseconds = parse_float(row.get("duration"))

            duration_seconds = (
                duration_microseconds / 1_000_000
                if duration_microseconds is not None
                else None
            )
            record = RawDisconnection(
                unit_id=parse_int(row.get("unit_id")),
                archive_date=archive_date,
                dtime=parse_timestamp(row.get("dtime")),
                end_dtime=parse_timestamp(row.get("end_dtime")),
                target=row.get("target", "").strip() or None,
                address=row.get("address", "").strip() or None,
                duration=duration_seconds,
            )
            records.append(record)

    if len(records) == 0:
        print("  curr_disconnection.csv is empty - skipping.")
        return

    session = SessionLocal()
    try:
        for record in records:
            session.add(record)
        session.commit()
        print(f"  curr_disconnection: {len(records)} rows loaded.")
    except Exception as e:
        session.rollback()
        print(f"  Error loading disconnections: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    load_disconnection(
        r"path\to\deltadata"  # replace with the actual extracted archive path
    )
