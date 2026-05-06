import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

from database import SessionLocal
from models.daily_aggregates import DailyAggregate
from models.raw_dns import RawDns
from sqlalchemy import distinct
from datetime import datetime

# Get missing dates
session = SessionLocal()
loaded_dates = [str(d[0]) for d in session.query(distinct(DailyAggregate.agg_date)).order_by(DailyAggregate.agg_date).all()]
dns_dates    = [str(d[0]) for d in session.query(distinct(RawDns.archive_date)).all()]
session.close()

missing = [d for d in loaded_dates if d not in dns_dates]
log.info(f"Dates missing DNS data: {len(missing)}")

from pipeline.downloader import download_specific_date
from parsers.dns_parser import load_dns
from aggregations.daily_aggregator import run_daily_aggregation

success = 0
failed  = 0

for date_str in missing:
    date_key     = date_str.replace("-", "")
    archive_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    log.info(f"[{date_str}] Downloading archive...")
    try:
        result = download_specific_date(date_key)
        if not result:
            log.warning(f"[{date_str}] Download returned nothing - skipping")
            failed += 1
            continue

        _, archive_path, deltadata_path = result
        log.info(f"[{date_str}] Parsing DNS from {deltadata_path}")
        load_dns(deltadata_path)

        log.info(f"[{date_str}] Re-running daily aggregation")
        run_daily_aggregation(archive_date)

        log.info(f"[{date_str}] Done ✓")
        success += 1

    except Exception as e:
        log.error(f"[{date_str}] Failed: {e}")
        failed += 1

log.info(f"Complete - {success} succeeded, {failed} failed")