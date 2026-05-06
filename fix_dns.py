import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from database import SessionLocal
from models.daily_aggregates import DailyAggregate
from models.raw_dns import RawDns
from sqlalchemy import distinct
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

# Find dates with daily aggregates but no DNS data
session = SessionLocal()
loaded_dates = [str(d[0]) for d in
                session.query(distinct(DailyAggregate.agg_date)).order_by(DailyAggregate.agg_date).all()]
dns_dates = [str(d[0]) for d in session.query(distinct(RawDns.archive_date)).all()]
session.close()

missing = [d for d in loaded_dates if d not in dns_dates]
log.info(f"Dates missing DNS data: {len(missing)}")
for d in missing:
    log.info(f"  {d}")

if not missing:
    log.info("All dates already have DNS data.")
    sys.exit(0)

from parsers.dns_parser import load_dns
from aggregations.daily_aggregator import run_daily_aggregation

success = 0
failed = 0

for date_str in missing:
    archive_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    date_key = date_str.replace("-", "")

    log.info(f"\nProcessing {date_str}...")

    # Check both raw and staging folders
    possible_paths = [
        Path("raw") / date_key,
        Path("staging") / date_key,
    ]

    deltadata_path = None
    for path in possible_paths:
        if path.exists():
            log.info(f"  Found folder: {path}")
            # Look for deltadata subfolder or DNS files directly
            dns_files = list(path.rglob("curr_dns*.csv"))
            if dns_files:
                deltadata_path = dns_files[0].parent
                log.info(f"  Found DNS files in: {deltadata_path}")
                break

    if not deltadata_path:
        log.error(f"  No DNS files found for {date_str} - skipping")
        failed += 1
        continue

    try:
        log.info(f"  Loading DNS data...")
        load_dns(str(deltadata_path))

        log.info(f"  Re-running daily aggregation...")
        run_daily_aggregation(archive_date)

        log.info(f"  ✅ {date_str} completed successfully")
        success += 1

    except Exception as e:
        log.error(f"  ❌ {date_str} failed: {e}")
        import traceback

        traceback.print_exc()
        failed += 1

log.info(f"\n{'=' * 50}")
log.info(f"Complete - {success} succeeded, {failed} failed")
log.info(f"{'=' * 50}")

# Verify the fix for the first few dates
if success > 0:
    log.info("\nVerifying results...")
    session = SessionLocal()
    try:
        for date_str in missing[:5]:
            archive_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            daily = session.query(DailyAggregate).filter(
                DailyAggregate.agg_date == archive_date,
                DailyAggregate.category == 'Combined'
            ).first()
            if daily:
                log.info(f"  {date_str}: DNS v4 = {daily.dns_v4_reliability}%, v6 = {daily.dns_v6_reliability}%")
            else:
                log.info(f"  {date_str}: No Combined record found")
    finally:
        session.close()