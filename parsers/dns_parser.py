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

def parse_dns_file(filepath, ip_version, archive_date, session):
    if not os.path.exists(filepath):
        print(f"  {os.path.basename(filepath)} not found - skipping.")
        return 0

    records = []

    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            successes = parse_int(row.get("successes"))
            rtt_raw   = parse_float(row.get("rtt"))

            rtt_ms = None
            if rtt_raw is not None and successes and successes > 0:
                rtt_ms = rtt_raw / 1000

            record = RawDns(
                unit_id     = parse_int(row.get("unit_id")),
                archive_date= archive_date,
                ip_version  = ip_version,
                dtime       = parse_timestamp(row.get("dtime")),
                nameserver  = row.get("nameserver", "").strip() or None,
                lookup_host = row.get("lookup_host", "").strip() or None,
                response_ip = row.get("response_ip", "").strip() or None,
                rtt         = rtt_ms,
                successes   = successes,
                failures    = parse_int(row.get("failures")),
            )
            records.append(record)

    if len(records) == 0:
        print(f"  {os.path.basename(filepath)} is empty - skipping.")
        return 0

    for record in records:
        session.add(record)

    return len(records)


def load_dns(deltadata_path):
    archive_date = extract_archive_date(deltadata_path)
    print(f"Processing DNS for archive date: {archive_date}")

    session = SessionLocal()
    total_rows = 0

    try:
        for filename, ip_version in [("curr_dns.csv", "4"), ("curr_dns6.csv", "6")]:
            filepath = os.path.join(deltadata_path, filename)
            rows = parse_dns_file(filepath, ip_version, archive_date, session)
            total_rows += rows
            if rows > 0:
                print(f"  {filename} (v{ip_version}): {rows} rows loaded.")

        session.commit()
        print(f"DNS loading complete. Total rows: {total_rows}")

    except Exception as e:
        session.rollback()
        print(f"  Error loading DNS: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    load_dns(
        r"path\to\deltadata"  # replace with the actual extracted archive path
    )