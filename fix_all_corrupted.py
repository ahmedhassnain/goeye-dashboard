# fix_all_corrupted.py
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.raw_dns import RawDns
from models.daily_aggregates import DailyAggregate
from sqlalchemy import distinct
from aggregations.daily_aggregator import run_daily_aggregation


def fix_all_dates():
    session = SessionLocal()
    try:
        # Get all dates that have DNS data
        all_dates = [d[0] for d in session.query(distinct(RawDns.archive_date)).all()]
        print(f"Found {len(all_dates)} dates to process")

        success = 0
        failed = 0

        for date_obj in all_dates:
            date_str = date_obj.strftime("%Y-%m-%d")
            print(f"\nProcessing {date_str}...")

            # Delete existing daily aggregates
            deleted = session.query(DailyAggregate).filter(
                DailyAggregate.agg_date == date_obj
            ).delete()
            session.commit()
            print(f"  Deleted {deleted} existing records")

            # Re-run aggregation
            try:
                run_daily_aggregation(date_obj)
                print(f"  ✅ Success")
                success += 1
            except Exception as e:
                print(f"  ❌ Failed: {e}")
                failed += 1

        print(f"\n{'=' * 50}")
        print(f"Complete - {success} succeeded, {failed} failed")

    finally:
        session.close()


if __name__ == "__main__":
    print("This will delete and recreate daily aggregates for ALL dates!")
    confirm = input("Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        fix_all_dates()
    else:
        print("Cancelled.")