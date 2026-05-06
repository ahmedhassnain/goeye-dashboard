# fix_mar23.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from aggregations.daily_aggregator import run_daily_aggregation

date_obj = datetime.strptime("2026-03-23", "%Y-%m-%d").date()
print(f"Re-running aggregation for 2026-03-23")
run_daily_aggregation(date_obj)
print("Done!")