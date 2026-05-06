# daily_aggregator.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import date
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


def compute_reliability(df):
    if df.empty or "successes" not in df.columns or "failures" not in df.columns:
        return None, 0
    total_successes = df["successes"].sum()
    total_failures  = df["failures"].sum()
    total_tests     = total_successes + total_failures
    if total_tests == 0:
        return None, 0
    reliability = (total_successes / total_tests) * 100
    return round(float(reliability), 4), int(total_tests)


def compute_weighted_reliability(category_results):
    total_weight = 0
    weighted_sum = 0
    for category, (reliability, tests) in category_results.items():
        if reliability is not None and tests > 0:
            weighted_sum += reliability * tests
            total_weight += tests
    if total_weight == 0:
        return None
    return round(float(weighted_sum / total_weight), 4)


def compute_uptime(disconnection_df, archive_date):
    observation_seconds = 24 * 60 * 60
    if disconnection_df.empty:
        return 100.0, 0, None
    total_downtime = 0
    all_durations  = []
    total_merged   = 0
    for unit_id, group in disconnection_df.groupby("unit_id"):
        intervals = []
        for _, row in group.iterrows():
            if pd.notna(row["dtime"]) and pd.notna(row["end_dtime"]):
                start = row["dtime"].timestamp()
                end   = row["end_dtime"].timestamp()
                if end > start:
                    intervals.append((start, end))
        if not intervals:
            continue
        intervals.sort(key=lambda x: x[0])
        merged = [intervals[0]]
        for current_start, current_end in intervals[1:]:
            last_start, last_end = merged[-1]
            if current_start <= last_end:
                merged[-1] = (last_start, max(last_end, current_end))
            else:
                merged.append((current_start, current_end))
        for start, end in merged:
            duration = end - start
            total_downtime += duration
            all_durations.append(duration)
            total_merged += 1
    uptime_pct = ((observation_seconds - total_downtime) / observation_seconds) * 100
    uptime_pct = max(0.0, min(100.0, round(uptime_pct, 4)))
    median_duration = round(float(np.median(all_durations)), 2) if all_durations else None
    return uptime_pct, total_merged, median_duration

def compute_dns_metrics(dns_df, ip_version):
    # ip_version should be "4" or "6", not "v4" or "v6"
    subset = dns_df[dns_df["ip_version"] == ip_version] if not dns_df.empty else pd.DataFrame()
    if subset.empty:
        return None, None
    total_successes = subset["successes"].sum()
    total_failures  = subset["failures"].sum()
    total_tests     = total_successes + total_failures
    if total_tests == 0:
        return None, None
    reliability = round(float((total_successes / total_tests) * 100), 4)
    successful  = subset[subset["successes"] > 0]["rtt"].dropna()
    rtt_p50     = round(float(successful.quantile(0.5)), 4) if not successful.empty else None
    return reliability, rtt_p50

def run_daily_aggregation(archive_date):
    print(f"Running daily aggregation for {archive_date}")
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
                print(f"    No units found for scope {scope.scope_name} - skipping.")
                continue

                # DELETE EXISTING DATA FOR THIS DATE AND SCOPE
                deleted = session.query(DailyAggregate).filter(
                    DailyAggregate.scope_id == scope.id,
                    DailyAggregate.agg_date == archive_date
                ).delete()
                if deleted > 0:
                    print(f"    Deleted {deleted} existing records for this date")

            game_df   = load_raw_table_as_df(RawGameLatency,      archive_date, unit_ids)
            social_df = load_raw_table_as_df(RawSocialMedia,       archive_date, unit_ids)
            video_df  = load_raw_table_as_df(RawVideoConferencing, archive_date, unit_ids)
            disc_df   = load_raw_table_as_df(RawDisconnection,     archive_date, unit_ids)
            dns_df    = load_raw_table_as_df(RawDns,               archive_date, unit_ids)

            game_reliability,   game_tests   = compute_reliability(game_df)
            social_reliability, social_tests = compute_reliability(social_df)
            video_reliability,  video_tests  = compute_reliability(video_df)

            category_results = {
                "Games":              (game_reliability,   game_tests),
                "Social Media":       (social_reliability, social_tests),
                "Video Conferencing": (video_reliability,  video_tests),
            }
            weighted_reliability = compute_weighted_reliability(category_results)

            uptime_pct, total_disconnections, median_disc_sec = compute_uptime(
                disc_df, archive_date
            )

            # Change these lines:
            dns_v4_reliability, dns_v4_rtt_p50 = compute_dns_metrics(dns_df, "4")  # Changed from "v4" to "4"
            dns_v6_reliability, dns_v6_rtt_p50 = compute_dns_metrics(dns_df, "6")  # Changed from "v6" to "6"

            aggregate = DailyAggregate(
                scope_id                 = scope.id,
                agg_date                 = archive_date,
                category                 = "Combined",
                reliability_pct          = game_reliability,
                weighted_reliability_pct = weighted_reliability,
                uptime_pct               = uptime_pct,
                total_tests              = game_tests + social_tests + video_tests,
                total_disconnections     = total_disconnections,
                median_disconnection_sec = median_disc_sec,
                dns_v4_reliability       = dns_v4_reliability,
                dns_v6_reliability       = dns_v6_reliability,
                dns_v4_rtt_p50           = dns_v4_rtt_p50,
                dns_v6_rtt_p50           = dns_v6_rtt_p50,
            )
            session.add(aggregate)

            for category, (reliability, tests) in category_results.items():
                cat_aggregate = DailyAggregate(
                    scope_id                 = scope.id,
                    agg_date                 = archive_date,
                    category                 = category,
                    reliability_pct          = reliability,
                    weighted_reliability_pct = None,
                    uptime_pct               = None,
                    total_tests              = tests,
                    total_disconnections     = None,
                    median_disconnection_sec = None,
                    dns_v4_reliability       = None,
                    dns_v6_reliability       = None,
                    dns_v4_rtt_p50           = None,
                    dns_v6_rtt_p50           = None,
                )
                session.add(cat_aggregate)

            session.commit()
            print(f"    Done - uptime: {uptime_pct}%, weighted reliability: {weighted_reliability}%")

        except Exception as e:
            session.rollback()
            print(f"    Error processing scope {scope.scope_name}: {e}")
        finally:
            session.close()

    print(f"Daily aggregation complete for {archive_date}")


if __name__ == "__main__":
    run_daily_aggregation(date(2026, 3, 11))