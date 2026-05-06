# hourly_aggregator.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import date
from database import SessionLocal
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


def get_scope_unit_ids(session, scope_name):
    result = (
        session.query(ScopeUnit.unit_id)
        .join(Scope, Scope.id == ScopeUnit.scope_id)
        .filter(Scope.scope_name == scope_name)
        .all()
    )
    return [row.unit_id for row in result]


def load_raw_table_as_df(table_class, archive_date, unit_ids):
    session = SessionLocal()
    try:
        rows = (
            session.query(table_class)
            .filter(
                table_class.archive_date == archive_date,
                table_class.unit_id.in_(unit_ids)
            )
            .all()
        )
        if not rows:
            return pd.DataFrame()
        data = [row.__dict__ for row in rows]
        df = pd.DataFrame(data)
        df = df.drop(columns=["_sa_instance_state"], errors="ignore")
        return df
    finally:
        session.close()


def compute_hourly_fail_rates(df, timestamp_col):
    if df.empty or "successes" not in df.columns or "failures" not in df.columns:
        return {}
    df = df.copy()
    df["hour"] = pd.to_datetime(df[timestamp_col]).dt.hour
    results = {}
    for hour in range(24):
        hour_df = df[df["hour"] == hour]
        if hour_df.empty:
            results[hour] = None
            continue
        total_successes = hour_df["successes"].sum()
        total_failures  = hour_df["failures"].sum()
        total_tests     = total_successes + total_failures
        if total_tests == 0:
            results[hour] = None
            continue
        fail_rate = float((total_failures / total_tests) * 100)
        results[hour] = round(fail_rate, 4)
    return results


def compute_hourly_disconnection_minutes(disc_df, archive_date):
    if disc_df.empty:
        return {hour: 0.0 for hour in range(24)}
    results = {hour: 0.0 for hour in range(24)}
    num_units = disc_df["unit_id"].nunique()
    if num_units == 0:
        return results
    for _, row in disc_df.iterrows():
        if pd.isna(row["dtime"]) or pd.isna(row["end_dtime"]):
            continue
        start_dt = pd.to_datetime(row["dtime"])
        end_dt   = pd.to_datetime(row["end_dtime"])
        if end_dt <= start_dt:
            continue
        current = start_dt
        while current < end_dt:
            hour        = current.hour
            hour_end    = current.replace(minute=0, second=0, microsecond=0) + pd.Timedelta(hours=1)
            overlap_end = min(end_dt, hour_end)
            overlap_minutes = (overlap_end - current).total_seconds() / 60
            results[hour] += overlap_minutes
            current = hour_end
    for hour in results:
        results[hour] = round(results[hour] / num_units, 4)
    return results


def run_hourly_aggregation(archive_date):
    print(f"Running hourly aggregation for {archive_date}")
    session = SessionLocal()
    try:
        scopes = session.query(Scope).all()
    finally:
        session.close()

    for scope in scopes:
        print(f"  Processing scope: {scope.scope_name}")
        session = SessionLocal()
        try:
            unit_ids = get_scope_unit_ids(session, scope.scope_name)
            if not unit_ids:
                continue

            game_df   = load_raw_table_as_df(RawGameLatency,      archive_date, unit_ids)
            social_df = load_raw_table_as_df(RawSocialMedia,       archive_date, unit_ids)
            video_df  = load_raw_table_as_df(RawVideoConferencing, archive_date, unit_ids)
            disc_df   = load_raw_table_as_df(RawDisconnection,     archive_date, unit_ids)

            game_fail_rates   = compute_hourly_fail_rates(game_df,   "dtime_local")
            social_fail_rates = compute_hourly_fail_rates(social_df,  "dtime_local")
            video_fail_rates  = compute_hourly_fail_rates(video_df,   "dtime_local")
            disc_minutes      = compute_hourly_disconnection_minutes(disc_df, archive_date)

            records = []
            category_map = {
                "Games":              game_fail_rates,
                "Social Media":       social_fail_rates,
                "Video Conferencing": video_fail_rates,
                "Disconnection":      {h: disc_minutes.get(h) for h in range(24)},
            }

            for category, hourly_data in category_map.items():
                for hour, value in hourly_data.items():
                    record = HourlyAggregate(
                        scope_id              = scope.id,
                        agg_date              = archive_date,
                        hour                  = hour,
                        category              = category,
                        fail_rate_pct         = value if category != "Disconnection" else None,
                        disconnection_minutes = value if category == "Disconnection" else None,
                    )
                    records.append(record)

            for record in records:
                session.add(record)

            session.commit()
            print(f"    Done - {len(records)} hourly records written.")

        except Exception as e:
            session.rollback()
            print(f"    Error processing scope {scope.scope_name}: {e}")
        finally:
            session.close()

    print(f"Hourly aggregation complete for {archive_date}")


if __name__ == "__main__":
    run_hourly_aggregation(date(2026, 3, 11))