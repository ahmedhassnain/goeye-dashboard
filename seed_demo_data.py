"""
Demo data seed script for portfolio deployment.

Run this instead of load_reference_data.py + pipeline when deploying the demo.
Populates 14 days of synthetic but realistic network metrics so the dashboard
is fully functional out of the box without any external data source.

Usage:
    python seed_demo_data.py

The script is idempotent - safe to run multiple times.
"""

import sys
import os
import random
from datetime import date, datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.units import Unit
from models.scopes import Scope
from models.scope_units import ScopeUnit
from models.applications import Application
from models.daily_aggregates import DailyAggregate
from models.hourly_aggregates import HourlyAggregate
from models.raw_game_latency import RawGameLatency
from models.raw_social_media import RawSocialMedia
from models.raw_video_conferencing import RawVideoConferencing
from models.raw_dns import RawDns
from models.users import User
from passlib.context import CryptContext

random.seed(42)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── DATE RANGE ────────────────────────────────────────────────────────────────
SEED_END   = date(2026, 4, 20)
SEED_DATES = [SEED_END - timedelta(days=i) for i in range(13, -1, -1)]  # Apr 7 → Apr 20

# ── REFERENCE DATA ────────────────────────────────────────────────────────────
# Fictional units - no real MAC addresses, no real employee names
GO_UNITS = [
    dict(unit_id=1001, mac="AA0000000001", unit_name="GO/FTTH/Node-A1", operator="GO",     technology="FTTH", identifier="Node-A1"),
    dict(unit_id=1002, mac="AA0000000002", unit_name="GO/FTTH/Node-A2", operator="GO",     technology="FTTH", identifier="Node-A2"),
    dict(unit_id=1003, mac="AA0000000003", unit_name="GO/FTTH/Node-B1", operator="GO",     technology="FTTH", identifier="Node-B1"),
    dict(unit_id=1004, mac="AA0000000004", unit_name="GO/FTTH/Node-B2", operator="GO",     technology="FTTH", identifier="Node-B2"),
    dict(unit_id=1005, mac="AA0000000005", unit_name="GO/FTTH/Node-C1", operator="GO",     technology="FTTH", identifier="Node-C1"),
]
STC_UNITS = [
    dict(unit_id=2001, mac="BB0000000001", unit_name="STC/FTTH/Node-S1",    operator="STC",    technology="FTTH", identifier="Node-S1"),
    dict(unit_id=2002, mac="BB0000000002", unit_name="STC/FTTH/Node-S2",    operator="STC",    technology="FTTH", identifier="Node-S2"),
    dict(unit_id=2003, mac="BB0000000003", unit_name="STC/FTTH/Node-S3",    operator="STC",    technology="FTTH", identifier="Node-S3"),
]
MOBILY_UNITS = [
    dict(unit_id=3001, mac="CC0000000001", unit_name="Mobily/FTTH/Node-M1", operator="Mobily", technology="FTTH", identifier="Node-M1"),
    dict(unit_id=3002, mac="CC0000000002", unit_name="Mobily/FTTH/Node-M2", operator="Mobily", technology="FTTH", identifier="Node-M2"),
    dict(unit_id=3003, mac="CC0000000003", unit_name="Mobily/FTTH/Node-M3", operator="Mobily", technology="FTTH", identifier="Node-M3"),
]
ALL_UNITS = GO_UNITS + STC_UNITS + MOBILY_UNITS

APPLICATIONS = [
    ("curr_among_us",            "Among Us",            "Games"),
    ("curr_apex_legends",        "Apex Legends",        "Games"),
    ("curr_cod",                 "Call of Duty",        "Games"),
    ("curr_counterstrike2",      "Counter Strike 2",    "Games"),
    ("curr_dota2",               "Dota 2",              "Games"),
    ("curr_fortnite",            "Fortnite",            "Games"),
    ("curr_league_of_legends",   "League of Legends",   "Games"),
    ("curr_pubg",                "PUBG",                "Games"),
    ("curr_pubg_mobile",         "PUBG Mobile",         "Games"),
    ("curr_valorant",            "Valorant",            "Games"),
    ("curr_roblox",              "Roblox",              "Games"),
    ("curr_social_media",        "Social Media",        "Social Media"),
    ("curr_video_conferencing",  "Video Conferencing",  "Video Conferencing"),
]

SOCIAL_SERVICES = [
    # Standard endpoints
    ("Instagram",  "photo",  "download", "instagram.com"),
    ("Instagram",  "video",  "download", "instagram.com"),
    ("Twitter",    "text",   "upload",   "twitter.com"),
    ("YouTube",    "video",  "download", "youtube.com"),
    ("TikTok",     "video",  "download", "tiktok.com"),
    ("Snapchat",   "photo",  "download", "snapchat.com"),
    # CDN-optimised endpoints (target contains 'cdn'/'edge' -> is_cdn=True in API)
    ("Instagram",  "photo",  "download", "instagram-cdn.net"),
    ("YouTube",    "video",  "download", "yt-edge.net"),
    ("Twitter",    "image",  "download", "twitter-cdn.net"),
    ("TikTok",     "video",  "download", "tiktok-cdn.net"),
]

VIDEO_SERVICES = [
    ("Zoom",             "us-west",    "zoom.us"),
    ("Microsoft Teams",  "eastus",     "teams.microsoft.com"),
    ("Google Meet",      "us-central", "meet.google.com"),
    ("Webex",            "us-east",    "webex.com"),
]

DNS_NAMESERVERS = {
    "4": ["8.8.8.8", "8.8.4.4", "1.1.1.1", "208.67.222.222"],
    "6": ["2001:4860:4860::8888", "2606:4700:4700::1111"],
}
DNS_HOSTS = ["google.com", "youtube.com", "facebook.com", "twitter.com", "amazon.com"]

GAME_PROVIDERS = [
    ("Valve",       "Frankfurt",  "EU-West"),
    ("Riot Games",  "Dubai",      "ME-South"),
    ("Activision",  "London",     "EU-West"),
    ("Epic Games",  "Singapore",  "AS-Southeast"),
    ("Microsoft",   "UAE North",  "ME-North"),
]

CATEGORIES = ["Combined", "Games", "Social Media", "Video Conferencing", "Disconnection"]

# ── HELPERS ───────────────────────────────────────────────────────────────────
def rnd(lo, hi):
    return round(random.uniform(lo, hi), 4)

def rnd2(lo, hi):
    return round(random.uniform(lo, hi), 2)

def rnd_int(lo, hi):
    return random.randint(lo, hi)

# ── SEEDERS ───────────────────────────────────────────────────────────────────
def seed_units(session):
    existing = {u.unit_id for u in session.query(Unit).all()}
    added = 0
    for u in ALL_UNITS:
        if u["unit_id"] not in existing:
            session.add(Unit(**u, is_active=True))
            added += 1
    session.flush()
    print(f"  Units: {added} added ({len(existing)} already existed)")


def seed_scopes(session):
    scope_defs = [
        ("GO/FTTH",     "GO",          "FTTH"),
        ("KSA Average", "STC,Mobily",  "FTTH"),
    ]
    scopes = {}
    for name, op_filter, tech_filter in scope_defs:
        scope = session.query(Scope).filter(Scope.scope_name == name).first()
        if not scope:
            scope = Scope(scope_name=name, operator_filter=op_filter, technology_filter=tech_filter)
            session.add(scope)
            session.flush()
            print(f"  Scope '{name}' created")
        else:
            print(f"  Scope '{name}' already exists")
        scopes[name] = scope

    # scope_units
    for scope_name, scope in scopes.items():
        existing_links = {su.unit_id for su in session.query(ScopeUnit).filter(ScopeUnit.scope_id == scope.id).all()}
        operators = [o.strip() for o in scope.operator_filter.split(",")]
        matching = session.query(Unit).filter(
            Unit.operator.in_(operators),
            Unit.technology == scope.technology_filter,
            Unit.is_active == True
        ).all()
        added = 0
        for unit in matching:
            if unit.unit_id not in existing_links:
                session.add(ScopeUnit(scope_id=scope.id, unit_id=unit.unit_id))
                added += 1
        print(f"  Scope '{scope_name}': {added} unit mappings added ({len(matching)} units total)")

    session.flush()
    return scopes


def seed_applications(session):
    existing = {a.file_key for a in session.query(Application).all()}
    added = 0
    for file_key, app_name, category in APPLICATIONS:
        if file_key not in existing:
            session.add(Application(file_key=file_key, app_name=app_name, category=category))
            added += 1
    session.flush()
    print(f"  Applications: {added} added ({len(existing)} already existed)")


def seed_daily_aggregates(session, scopes):
    for d in SEED_DATES:
        for scope_name, scope in scopes.items():
            already = session.query(DailyAggregate).filter(
                DailyAggregate.scope_id == scope.id,
                DailyAggregate.agg_date == d
            ).count()
            if already:
                continue

            is_go = scope_name == "GO/FTTH"
            base_rel     = rnd(97.5, 99.5) if is_go else rnd(94.0, 97.5)
            base_uptime  = rnd(98.5, 99.9) if is_go else rnd(96.0, 98.5)
            base_disconn = rnd_int(0, 3)    if is_go else rnd_int(2, 8)

            cat_offsets = {
                "Combined":           0.0,
                "Games":              rnd(-0.5, 0.3),
                "Social Media":       rnd(-0.3, 0.5),
                "Video Conferencing": rnd(-0.8, 0.2),
                "Disconnection":      0.0,
            }

            for category in CATEGORIES:
                rel = min(100.0, base_rel + cat_offsets[category])
                session.add(DailyAggregate(
                    scope_id                 = scope.id,
                    agg_date                 = d,
                    category                 = category,
                    reliability_pct          = round(rel, 4),
                    weighted_reliability_pct = round(min(100.0, rel + rnd(-0.3, 0.3)), 4),
                    uptime_pct               = round(min(100.0, base_uptime + rnd(-0.2, 0.2)), 4),
                    total_tests              = rnd_int(800, 2000),
                    total_disconnections     = base_disconn,
                    median_disconnection_sec = rnd2(5, 30) if is_go else rnd2(10, 60),
                    dns_v4_reliability       = round(rnd(98.5, 99.9) if is_go else rnd(96.0, 99.0), 4),
                    dns_v6_reliability       = round(rnd(97.0, 99.5) if is_go else rnd(93.0, 97.5), 4),
                    dns_v4_rtt_p50           = rnd2(5, 15)  if is_go else rnd2(8, 25),
                    dns_v6_rtt_p50           = rnd2(6, 18)  if is_go else rnd2(10, 30),
                ))
    print(f"  Daily aggregates: {len(SEED_DATES)} dates × {len(scopes)} scopes")


def seed_hourly_aggregates(session, scopes):
    for d in SEED_DATES:
        for scope_name, scope in scopes.items():
            already = session.query(HourlyAggregate).filter(
                HourlyAggregate.scope_id == scope.id,
                HourlyAggregate.agg_date == d
            ).count()
            if already:
                continue

            is_go = scope_name == "GO/FTTH"
            for category in ["Games", "Social Media", "Video Conferencing", "Disconnection"]:
                for hour in range(24):
                    peak = 1.6 if 18 <= hour <= 23 else 1.0  # evening peak
                    base_fail = rnd(0.2, 1.5) if is_go else rnd(0.8, 3.5)
                    session.add(HourlyAggregate(
                        scope_id             = scope.id,
                        agg_date             = d,
                        hour                 = hour,
                        category             = category,
                        fail_rate_pct        = round(min(100.0, base_fail * peak), 4),
                        disconnection_minutes= round(rnd(0, 1.5) * peak, 2),
                    ))
    print(f"  Hourly aggregates: {len(SEED_DATES)} dates × {len(scopes)} scopes × 24 hours")


def seed_raw_gaming(session, scopes):
    game_keys = [fk for fk, _, cat in APPLICATIONS if cat == "Games"]
    go_scope  = scopes.get("GO/FTTH")
    if not go_scope:
        return

    unit_ids = [su.unit_id for su in session.query(ScopeUnit).filter(ScopeUnit.scope_id == go_scope.id).all()]

    for d in SEED_DATES:
        already = session.query(RawGameLatency).filter(
            RawGameLatency.archive_date == d,
            RawGameLatency.unit_id.in_(unit_ids)
        ).count()
        if already:
            continue

        for uid in unit_ids:
            for game_key in game_keys:
                provider, datacenter, region = random.choice(GAME_PROVIDERS)
                rtt_avg = rnd_int(25000, 75000)  # stored in µs; API divides by 1000 → ms
                rtt_min = int(rtt_avg * rnd(0.6, 0.85))
                rtt_max = int(rtt_avg * rnd(1.15, 1.6))
                rtt_std = int(rtt_avg * rnd(0.05, 0.15))
                succ    = rnd_int(80, 200)
                fail    = rnd_int(0, 5)
                session.add(RawGameLatency(
                    unit_id     = uid,
                    app_key     = game_key,
                    archive_date= d,
                    dtime_local = datetime.combine(d, datetime.min.time()),
                    dtime_utc   = datetime.combine(d, datetime.min.time()),
                    provider    = provider,
                    region      = region,
                    datacenter  = datacenter,
                    address     = f"gs-{random.randint(1, 9)}.demo.net",
                    rtt_avg     = rtt_avg,
                    rtt_min     = rtt_min,
                    rtt_max     = rtt_max,
                    rtt_std     = rtt_std,
                    hop_count   = rnd_int(8, 18),
                    num_successes= succ,
                    num_failures = fail,
                    successes   = succ,
                    failures    = fail,
                ))
    print(f"  Raw gaming: {len(SEED_DATES)} dates × {len(unit_ids)} units × {len(game_keys)} games")


def seed_raw_social(session, scopes):
    total_units = 0
    for scope_name, scope in scopes.items():
        unit_ids = [su.unit_id for su in session.query(ScopeUnit).filter(ScopeUnit.scope_id == scope.id).all()]
        total_units += len(unit_ids)
        is_go = scope_name == "GO/FTTH"

        for d in SEED_DATES:
            already = session.query(RawSocialMedia).filter(
                RawSocialMedia.archive_date == d,
                RawSocialMedia.unit_id.in_(unit_ids)
            ).count()
            if already:
                continue

            for uid in unit_ids:
                for service, media, direction, target in SOCIAL_SERVICES:
                    rtt_avg = rnd_int(25000, 60000) if is_go else rnd_int(35000, 90000)  # µs; API divides by 1000
                    succ    = rnd_int(50, 150)
                    fail    = rnd_int(0, 3)
                    session.add(RawSocialMedia(
                        unit_id    = uid,
                        archive_date= d,
                        dtime_local= datetime.combine(d, datetime.min.time()),
                        dtime_utc  = datetime.combine(d, datetime.min.time()),
                        service    = service,
                        media      = media,
                        direction  = direction,
                        target     = target,
                        address    = target,
                        rtt_avg    = rtt_avg,
                        rtt_median = int(rtt_avg * rnd(0.90, 1.00)),
                        rtt_min    = int(rtt_avg * rnd(0.60, 0.80)),
                        rtt_max    = int(rtt_avg * rnd(1.20, 1.80)),
                        rtt_std    = int(rtt_avg * rnd(0.05, 0.15)),
                        successes  = succ,
                        failures   = fail,
                    ))
    print(f"  Raw social: {len(SEED_DATES)} dates × {total_units} units × {len(SOCIAL_SERVICES)} services")


def seed_raw_video(session, scopes):
    total_units = 0
    for scope_name, scope in scopes.items():
        unit_ids = [su.unit_id for su in session.query(ScopeUnit).filter(ScopeUnit.scope_id == scope.id).all()]
        total_units += len(unit_ids)
        is_go = scope_name == "GO/FTTH"

        for d in SEED_DATES:
            already = session.query(RawVideoConferencing).filter(
                RawVideoConferencing.archive_date == d,
                RawVideoConferencing.unit_id.in_(unit_ids)
            ).count()
            if already:
                continue

            for uid in unit_ids:
                for service, region, target in VIDEO_SERVICES:
                    rtt_avg = rnd_int(20000, 50000) if is_go else rnd_int(30000, 75000)  # µs; API divides by 1000
                    succ    = rnd_int(40, 120)
                    fail    = rnd_int(0, 3)
                    session.add(RawVideoConferencing(
                        unit_id    = uid,
                        archive_date= d,
                        dtime_local= datetime.combine(d, datetime.min.time()),
                        dtime_utc  = datetime.combine(d, datetime.min.time()),
                        service    = service,
                        region     = region,
                        target     = target,
                        address    = target,
                        rtt_avg    = rtt_avg,
                        rtt_median = int(rtt_avg * rnd(0.90, 1.00)),
                        rtt_min    = int(rtt_avg * rnd(0.60, 0.80)),
                        rtt_max    = int(rtt_avg * rnd(1.20, 1.80)),
                        rtt_std    = int(rtt_avg * rnd(0.05, 0.15)),
                        successes  = succ,
                        failures   = fail,
                    ))
    print(f"  Raw video: {len(SEED_DATES)} dates × {total_units} units × {len(VIDEO_SERVICES)} services")


def seed_raw_dns(session, scopes):
    total_units = 0
    for scope_name, scope in scopes.items():
        unit_ids = [su.unit_id for su in session.query(ScopeUnit).filter(ScopeUnit.scope_id == scope.id).all()]
        total_units += len(unit_ids)
        is_go = scope_name == "GO/FTTH"

        for d in SEED_DATES:
            already = session.query(RawDns).filter(
                RawDns.archive_date == d,
                RawDns.unit_id.in_(unit_ids)
            ).count()
            if already:
                continue

            for uid in unit_ids:
                for ip_ver, nameservers in DNS_NAMESERVERS.items():
                    for ns in nameservers:
                        for host in DNS_HOSTS:
                            rtt  = rnd2(4, 15) if is_go else rnd2(6, 25)  # in ms
                            succ = rnd_int(50, 200)
                            fail = rnd_int(0, 2)
                            session.add(RawDns(
                                unit_id    = uid,
                                archive_date= d,
                                ip_version = ip_ver,
                                dtime      = datetime.combine(d, datetime.min.time()),
                                nameserver = ns,
                                lookup_host= host,
                                response_ip= f"93.184.{random.randint(1, 254)}.{random.randint(1, 254)}",
                                rtt        = rtt,
                                successes  = succ,
                                failures   = fail,
                            ))
    ns_count = sum(len(v) for v in DNS_NAMESERVERS.values())
    print(f"  Raw DNS: {len(SEED_DATES)} dates × {total_units} units × {ns_count} nameservers × {len(DNS_HOSTS)} hosts")


def seed_demo_user(session):
    existing = session.query(User).filter(User.username == "demo").first()
    if not existing:
        session.add(User(
            username       = "demo",
            email          = "demo@example.com",
            full_name      = "Demo User",
            hashed_password= pwd_context.hash("demo1234"),
            role           = "analyst",
            is_active      = True,
        ))
        print("  Demo user created  →  username: demo  |  password: demo1234")
    else:
        print("  Demo user already exists")


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Seeding demo data for {len(SEED_DATES)} dates ({SEED_DATES[0]} → {SEED_DATES[-1]})...\n")
    session = SessionLocal()
    try:
        print("[1/8] Units")
        seed_units(session)

        print("[2/8] Scopes & unit mappings")
        scopes = seed_scopes(session)

        print("[3/8] Applications")
        seed_applications(session)

        print("[4/8] Daily aggregates")
        seed_daily_aggregates(session, scopes)

        print("[5/8] Hourly aggregates")
        seed_hourly_aggregates(session, scopes)

        print("[6/8] Raw gaming data")
        seed_raw_gaming(session, scopes)

        print("[7/8] Raw social & video conferencing")
        seed_raw_social(session, scopes)
        seed_raw_video(session, scopes)

        print("[8/8] Raw DNS & demo user")
        seed_raw_dns(session, scopes)
        seed_demo_user(session)

        session.commit()
        print(f"\nDone. Dashboard is ready - log in with  demo / demo1234")

    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        print(f"\nFailed: {e}")
    finally:
        session.close()
