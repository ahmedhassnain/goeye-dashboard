# generate_ksa_combined.py
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.scopes import Scope
from models.daily_aggregates import DailyAggregate
from aggregations.daily_aggregator import run_daily_aggregation
from datetime import datetime


def generate_ksa_combined():
    session = SessionLocal()
    try:
        # Get KSA Average scope
        ksa_scope = session.query(Scope).filter(Scope.scope_name == 'KSA Average').first()
        if not ksa_scope:
            print("❌ KSA Average scope not found")
            return

        # Get all distinct dates that have ANY KSA Average data
        existing_dates = session.query(DailyAggregate.agg_date).filter(
            DailyAggregate.scope_id == ksa_scope.id
        ).distinct().order_by(DailyAggregate.agg_date.desc()).all()

        dates_to_process = [d[0] for d in existing_dates]
        print(f"Found {len(dates_to_process)} dates with KSA Average data")

        success = 0
        failed = 0

        for date_obj in dates_to_process:
            date_str = date_obj.strftime("%Y-%m-%d")
            print(f"\nProcessing {date_str}...")

            # Check if Combined record already exists
            existing_combined = session.query(DailyAggregate).filter(
                DailyAggregate.scope_id == ksa_scope.id,
                DailyAggregate.agg_date == date_obj,
                DailyAggregate.category == 'Combined'
            ).first()

            if existing_combined:
                print(f"  ✅ Combined record already exists")
                success += 1
                continue

            # Run the daily aggregation for this date
            # This will create all records including Combined for KSA Average
            try:
                print(f"  🔄 Running daily aggregation for {date_str}...")
                run_daily_aggregation(date_obj)
                print(f"  ✅ Successfully created Combined record")
                success += 1
            except Exception as e:
                print(f"  ❌ Failed: {e}")
                import traceback
                traceback.print_exc()
                failed += 1

        print(f"\n{'=' * 50}")
        print(f"Complete - {success} succeeded, {failed} failed")
        print(f"{'=' * 50}")

        # Verify the results
        print("\n✅ Verifying KSA Average Combined records:")
        new_records = session.query(DailyAggregate).filter(
            DailyAggregate.scope_id == ksa_scope.id,
            DailyAggregate.category == 'Combined'
        ).order_by(DailyAggregate.agg_date.desc()).limit(10).all()

        if new_records:
            for record in new_records:
                print(f"  {record.agg_date}: uptime={record.uptime_pct}%, reliability={record.reliability_pct}%")
        else:
            print("  ❌ No Combined records found after processing!")

    finally:
        session.close()


if __name__ == "__main__":
    generate_ksa_combined()