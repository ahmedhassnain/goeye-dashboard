# run_pipeline.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import shutil
import argparse
from datetime import datetime
from pathlib import Path

from pipeline.downloader import download_latest, download_specific_date
from parsers.game_latency_parser import load_game_latency
from parsers.disconnection_parser import load_disconnection
from parsers.social_media_parser import load_social_media
from parsers.video_conferencing_parser import load_video_conferencing
from parsers.dns_parser import load_dns
from aggregations.daily_aggregator import run_daily_aggregation
from aggregations.hourly_aggregator import run_hourly_aggregation
from database import SessionLocal
from models.daily_aggregates import DailyAggregate
from models.hourly_aggregates import HourlyAggregate
from models.raw_game_latency import RawGameLatency
from models.raw_social_media import RawSocialMedia
from models.raw_video_conferencing import RawVideoConferencing
from models.raw_disconnection import RawDisconnection
from models.raw_dns import RawDns

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pipeline.log', encoding='utf-8'),
    ]
)
log = logging.getLogger(__name__)

STAGING_DIR = Path(__file__).parent.parent / "staging"


def is_already_processed(archive_date):
    session = SessionLocal()
    try:
        count = session.query(DailyAggregate).filter(
            DailyAggregate.agg_date == archive_date
        ).count()
        return count > 0
    finally:
        session.close()


def clear_existing_data(archive_date):
    session = SessionLocal()
    try:
        date_obj = datetime.strptime(archive_date, "%Y%m%d").date() if isinstance(archive_date, str) else archive_date
        deleted = {
            'game':   session.query(RawGameLatency).filter(RawGameLatency.archive_date == date_obj).delete(),
            'social': session.query(RawSocialMedia).filter(RawSocialMedia.archive_date == date_obj).delete(),
            'video':  session.query(RawVideoConferencing).filter(RawVideoConferencing.archive_date == date_obj).delete(),
            'disc':   session.query(RawDisconnection).filter(RawDisconnection.archive_date == date_obj).delete(),
            'dns':    session.query(RawDns).filter(RawDns.archive_date == date_obj).delete(),
            'daily':  session.query(DailyAggregate).filter(DailyAggregate.agg_date == date_obj).delete(),
            'hourly': session.query(HourlyAggregate).filter(HourlyAggregate.agg_date == date_obj).delete(),
        }
        session.commit()
        log.info(f"Cleared existing data: {deleted}")
    except Exception as e:
        session.rollback()
        log.error(f"Failed to clear data: {e}")
    finally:
        session.close()


def cleanup_staging(date_str):
    staging_path = STAGING_DIR / date_str
    if staging_path.exists():
        shutil.rmtree(staging_path)
        log.info(f"Cleaned up staging: {staging_path}")


def process_one_date(date_str, deltadata_path, reprocess=False):
    archive_date = datetime.strptime(date_str, "%Y%m%d").date()
    log.info(f"{'='*50}")
    log.info(f"Processing date: {date_str}")
    log.info(f"Deltadata path:  {deltadata_path}")

    if is_already_processed(archive_date) and not reprocess:
        log.info(f"Already processed - skipping. Use --reprocess to force.")
        return True

    if reprocess:
        clear_existing_data(date_str)

    steps = [
        ("Game Latency Parser",       lambda: load_game_latency(deltadata_path)),
        ("Disconnection Parser",       lambda: load_disconnection(deltadata_path)),
        ("Social Media Parser",        lambda: load_social_media(deltadata_path)),
        ("Video Conferencing Parser",  lambda: load_video_conferencing(deltadata_path)),
        ("DNS Parser",                 lambda: load_dns(deltadata_path)),
        ("Daily Aggregator",           lambda: run_daily_aggregation(archive_date)),
        ("Hourly Aggregator",          lambda: run_hourly_aggregation(archive_date)),
    ]

    for step_name, step_fn in steps:
        log.info(f"  Running: {step_name}")
        try:
            step_fn()
            log.info(f"  ✓ {step_name} complete")
        except Exception as e:
            log.error(f"  ✗ {step_name} FAILED: {e}")
            log.error(f"  Aborting pipeline for {date_str}")
            return False

    cleanup_staging(date_str)
    log.info(f"Pipeline complete for {date_str}")
    return True


def run_pipeline(days=1, reprocess=False, specific_date=None):
    log.info("SamKnows Pipeline Starting")
    log.info(f"Mode: {'specific date=' + specific_date if specific_date else 'latest ' + str(days) + ' day(s)'}")
    log.info(f"Reprocess: {reprocess}")

    start_time = datetime.now()

    if specific_date:
        result = download_specific_date(specific_date)
        if not result:
            log.error(f"Could not download archive for {specific_date}")
            return
        results = [result]
    else:
        results = download_latest()
        if days and days < len(results):
            results = results[-days:]

    if not results:
        log.info("No archives to process.")
        return

    success_count = 0
    fail_count    = 0

    for date_str, archive_path, deltadata_path in results:
        success = process_one_date(date_str, deltadata_path, reprocess=reprocess)
        if success:
            success_count += 1
        else:
            fail_count += 1

    elapsed = (datetime.now() - start_time).total_seconds()
    log.info(f"{'='*50}")
    log.info(f"Pipeline finished in {elapsed:.1f}s")
    log.info(f"  Successful: {success_count}")
    log.info(f"  Failed:     {fail_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SamKnows daily pipeline")
    parser.add_argument('--days',      type=int,  default=1,     help='Number of recent archives to process')
    parser.add_argument('--date',      type=str,  default=None,  help='Process a specific date e.g. 20260311')
    parser.add_argument('--reprocess', action='store_true',      help='Clear and reprocess existing data')
    args = parser.parse_args()

    run_pipeline(
        days=args.days,
        reprocess=args.reprocess,
        specific_date=args.date,
    )