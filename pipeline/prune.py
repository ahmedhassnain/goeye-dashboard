# prune.py
"""
Raw-data retention.

Raw measurement rows are only needed for the per-date breakdown views
(gaming, social, video, DNS); daily and hourly aggregates are tiny and kept
forever. Deleting raw rows older than RAW_RETENTION_DAYS keeps the database
inside the Neon free-tier storage limit while the daily pipeline keeps adding
data.

Usage:
    python pipeline/prune.py                 # uses RAW_RETENTION_DAYS (default 90)
    python pipeline/prune.py --days 30
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
from datetime import date, timedelta

from database import SessionLocal
from models.raw_game_latency import RawGameLatency
from models.raw_social_media import RawSocialMedia
from models.raw_video_conferencing import RawVideoConferencing
from models.raw_disconnection import RawDisconnection
from models.raw_dns import RawDns

log = logging.getLogger(__name__)

RAW_TABLES = [RawGameLatency, RawSocialMedia, RawVideoConferencing, RawDisconnection, RawDns]
DEFAULT_RETENTION_DAYS = int(os.getenv("RAW_RETENTION_DAYS", "90"))


def prune_raw_data(retention_days=DEFAULT_RETENTION_DAYS, today=None):
    """Delete raw rows whose archive_date is older than the retention window."""
    if retention_days <= 0:
        log.info("Raw-data pruning disabled (retention_days <= 0).")
        return {}

    cutoff = (today or date.today()) - timedelta(days=retention_days)
    session = SessionLocal()
    try:
        deleted = {
            table.__tablename__: session.query(table)
                .filter(table.archive_date < cutoff)
                .delete(synchronize_session=False)
            for table in RAW_TABLES
        }
        session.commit()
        log.info(f"Pruned raw rows older than {cutoff}: {deleted}")
        return deleted
    except Exception as e:
        session.rollback()
        log.error(f"Raw-data pruning failed: {e}")
        return {}
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    parser = argparse.ArgumentParser(description="Delete raw measurement rows past the retention window")
    parser.add_argument('--days', type=int, default=DEFAULT_RETENTION_DAYS, help='Days of raw data to keep')
    args = parser.parse_args()
    prune_raw_data(args.days)
