# generate_archive.py
"""
Synthetic SamKnows archive generator.

Produces daily archives in the same shape the real SamKnows export uses:

    YYYYMMDD-goeye-demo.tar.gz
    └── deltadata/
        ├── curr_<game>.csv            (one per game in GAME_FILES)
        ├── curr_social_media.csv
        ├── curr_video_conferencing.csv
        ├── curr_dns.csv / curr_dns6.csv
        └── curr_disconnection.csv

Column headers and units match the real export (all RTTs in microseconds,
timestamps as "YYYY-MM-DD HH:MM:SS"), so the unmodified pipeline parsers can
ingest them. Output is deterministic per date: regenerating a date gives a
byte-identical archive.

Stdlib only, so it runs in CI without installing the backend requirements.

Usage:
    python samknows_sim/generate_archive.py                      # yesterday (KSA time)
    python samknows_sim/generate_archive.py --date 2026-10-18
    python samknows_sim/generate_archive.py --date 2026-10-18 --days 30   # backfill 30 days ending on --date
"""

import argparse
import csv
import gzip
import io
import math
import random
import tarfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ARCHIVE_SUFFIX = "goeye-demo"
KSA_UTC_OFFSET = timedelta(hours=3)

# ── REFERENCE DATA ────────────────────────────────────────────────────────────
# Keep in sync with parsers/game_latency_parser.py GAME_FILES (not imported:
# that module pulls in the database layer).
GAME_FILES = [
    "curr_among_us", "curr_apex_legends", "curr_bfv", "curr_cod", "curr_counterstrike2",
    "curr_diablo3", "curr_diablo4", "curr_dota2", "curr_efootball_2024", "curr_fc24",
    "curr_fifa21", "curr_fortnite", "curr_free_fire_max", "curr_gears5", "curr_halo_infinite",
    "curr_hearthstone", "curr_heroes_of_the_storm", "curr_honor_of_kings",
    "curr_league_of_legends", "curr_mobile_legends_bang_bang", "curr_overwatch", "curr_pubg",
    "curr_pubg_mobile", "curr_rainbow_six_siege", "curr_roblox", "curr_rocket_league",
    "curr_starcraft2", "curr_valorant", "curr_world_of_warcraft",
]

# Must match the units seeded by seed_demo_data.py - raw rows reference
# units.unit_id through a foreign key.
UNITS = {
    1001: "GO", 1002: "GO", 1003: "GO", 1004: "GO", 1005: "GO",
    2001: "STC", 2002: "STC", 2003: "STC",
    3001: "Mobily", 3002: "Mobily", 3003: "Mobily",
}

# Per-operator quality profile: latency multiplier, base failure probability,
# expected disconnections per unit per day.
OPERATOR_PROFILE = {
    "GO":     dict(rtt_mult=1.00, fail_p=0.008, disc_rate=0.25),
    "STC":    dict(rtt_mult=1.25, fail_p=0.022, disc_rate=0.80),
    "Mobily": dict(rtt_mult=1.35, fail_p=0.028, disc_rate=1.00),
}

GAME_PROVIDERS = [
    ("Valve",       "EU-West",      "Frankfurt"),
    ("Riot Games",  "ME-South",     "Dubai"),
    ("Activision",  "EU-West",      "London"),
    ("Epic Games",  "AS-Southeast", "Singapore"),
    ("Microsoft",   "ME-North",     "UAE North"),
    ("Tencent",     "ME-South",     "Bahrain"),
]

# Same catalogue as seed_demo_data.py so seeded and pipeline-loaded dates look alike.
SOCIAL_SERVICES = [
    ("Instagram", "photo", "download", "instagram.com"),
    ("Instagram", "video", "download", "instagram.com"),
    ("Twitter",   "text",  "upload",   "twitter.com"),
    ("YouTube",   "video", "download", "youtube.com"),
    ("TikTok",    "video", "download", "tiktok.com"),
    ("Snapchat",  "photo", "download", "snapchat.com"),
    ("Instagram", "photo", "download", "instagram-cdn.net"),
    ("YouTube",   "video", "download", "yt-edge.net"),
    ("Twitter",   "image", "download", "twitter-cdn.net"),
    ("TikTok",    "video", "download", "tiktok-cdn.net"),
]

VIDEO_SERVICES = [
    ("Zoom",            "us-west",    "zoom.us"),
    ("Microsoft Teams", "eastus",     "teams.microsoft.com"),
    ("Google Meet",     "us-central", "meet.google.com"),
    ("Webex",           "us-east",    "webex.com"),
]

DNS_NAMESERVERS = {
    "4": ["8.8.8.8", "8.8.4.4", "1.1.1.1", "208.67.222.222"],
    "6": ["2001:4860:4860::8888", "2606:4700:4700::1111"],
}
DNS_HOSTS = ["google.com", "youtube.com", "facebook.com", "twitter.com", "amazon.com"]

# Test cadence (hours between runs of the same test on the same unit). Each
# unit starts at a different offset so every hour of the day gets samples.
GAME_EVERY_H   = 3
SOCIAL_EVERY_H = 2
VIDEO_EVERY_H  = 2
DNS_EVERY_H    = 2

# Real-export headers, verbatim.
GAME_HEADER = ["unit_id", "dtime_local", "dtime_utc", "error_code", "error_details", "provider",
               "region", "datacenter", "address", "rtt_avg", "rtt_min", "rtt_max", "rtt_std",
               "hop_count", "num_successes", "num_failures", "successes", "failures", "base"]
SOCIAL_HEADER = ["unit_id", "dtime_local", "dtime_utc", "error_code", "error_details", "service",
                 "media", "direction", "target", "name_resolution_protocol", "dns_server_address",
                 "dns_server_url", "address", "rtt_min", "rtt_avg", "rtt_median", "rtt_max",
                 "rtt_std", "hop_count", "successes", "failures", "base"]
VIDEO_HEADER = ["unit_id", "dtime", "error_code", "error_details", "service", "region", "target",
                "name_resolution_protocol", "dns_server_address", "dns_server_url", "address",
                "rtt_avg", "rtt_min", "rtt_median", "rtt_max", "rtt_std", "successes", "failures",
                "location_id"]
DNS_HEADER = ["unit_id", "dtime", "nameserver", "lookup_host", "response_ip", "rtt", "successes",
              "failures", "location_id"]
DISC_HEADER = ["unit_id", "dtime", "end_dtime", "target", "address", "duration", "packets"]


# ── DAY-LEVEL CONDITIONS ──────────────────────────────────────────────────────
def hour_load(hour):
    """Evening peak (KSA): latency and failures climb from 18:00 to midnight."""
    return 1.0 + 0.6 * math.exp(-((hour - 21) ** 2) / 8.0)


def day_conditions(rng):
    """Roughly one day in eight has an incident: one operator degrades for a few hours."""
    if rng.random() < 0.125:
        start = rng.randint(6, 20)
        return dict(
            operator=rng.choice(list(OPERATOR_PROFILE)),
            hours=set(range(start, min(24, start + rng.randint(2, 5)))),
            severity=rng.uniform(3.0, 6.0),
        )
    return None


def conditions_at(unit_id, hour, incident):
    op = UNITS[unit_id]
    profile = OPERATOR_PROFILE[op]
    load = hour_load(hour)
    fail_p = profile["fail_p"] * load
    rtt_mult = profile["rtt_mult"] * (1 + (load - 1) * 0.5)
    if incident and incident["operator"] == op and hour in incident["hours"]:
        fail_p *= incident["severity"]
        rtt_mult *= 1 + incident["severity"] / 6
    return min(fail_p, 0.6), rtt_mult


# ── HELPERS ───────────────────────────────────────────────────────────────────
def fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def test_time(rng, day, hour):
    """Local and UTC timestamps for a test run at a random minute within the hour."""
    local = datetime.combine(day, datetime.min.time()) + timedelta(
        hours=hour, minutes=rng.randint(0, 59), seconds=rng.randint(0, 59))
    return local, local - KSA_UTC_OFFSET


def rtt_stats(rng, mean_us):
    """avg/min/median/max/std in integer microseconds around a target mean."""
    avg = max(1000, rng.gauss(mean_us, mean_us * 0.12))
    return dict(
        rtt_avg=int(avg),
        rtt_min=int(avg * rng.uniform(0.60, 0.85)),
        rtt_median=int(avg * rng.uniform(0.92, 1.00)),
        rtt_max=int(avg * rng.uniform(1.15, 1.70)),
        rtt_std=int(avg * rng.uniform(0.04, 0.15)),
    )


def schedule(unit_id, every_h, salt):
    """Hours of the day at which a unit runs a test, staggered per unit."""
    offset = (unit_id + salt) % every_h
    return range(offset, 24, every_h)


def to_csv(header, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in header})
    return buf.getvalue().encode("utf-8")


# ── FILE GENERATORS ───────────────────────────────────────────────────────────
def gen_games(rng, day, incident):
    files = {}
    for g_idx, app_key in enumerate(GAME_FILES):
        game_rng = random.Random(f"{day}-{app_key}")
        provider, region, datacenter = GAME_PROVIDERS[g_idx % len(GAME_PROVIDERS)]
        base_rtt = game_rng.uniform(18_000, 70_000)
        rows = []
        for unit_id in UNITS:
            for hour in schedule(unit_id, GAME_EVERY_H, g_idx):
                fail_p, mult = conditions_at(unit_id, hour, incident)
                local, utc = test_time(rng, day, hour)
                failed = rng.random() < fail_p
                packets_failed = 10 if failed else (1 if rng.random() < fail_p * 3 else 0)
                row = dict(
                    unit_id=unit_id, dtime_local=fmt(local), dtime_utc=fmt(utc),
                    provider=provider, region=region, datacenter=datacenter,
                    address=f"gs-{(unit_id + g_idx) % 9 + 1}.demo.net",
                    hop_count=rng.randint(8, 18),
                    num_successes=10 - packets_failed, num_failures=packets_failed,
                    successes=0 if failed else 1, failures=1 if failed else 0, base=1,
                )
                if failed:
                    row["error_code"] = "TIMEOUT"
                else:
                    stats = rtt_stats(rng, base_rtt * mult)
                    stats.pop("rtt_median")
                    row.update(stats)
                rows.append(row)
        files[f"{app_key}.csv"] = to_csv(GAME_HEADER, rows)
    return files


def gen_social(rng, day, incident):
    rows = []
    for s_idx, (service, media, direction, target) in enumerate(SOCIAL_SERVICES):
        is_cdn = "cdn" in target or "edge" in target
        base_rtt = rng.uniform(18_000, 30_000) if is_cdn else rng.uniform(32_000, 55_000)
        for unit_id in UNITS:
            for hour in schedule(unit_id, SOCIAL_EVERY_H, s_idx):
                fail_p, mult = conditions_at(unit_id, hour, incident)
                local, utc = test_time(rng, day, hour)
                failures = sum(rng.random() < fail_p for _ in range(10))
                row = dict(
                    unit_id=unit_id, dtime_local=fmt(local), dtime_utc=fmt(utc),
                    service=service, media=media, direction=direction, target=target,
                    name_resolution_protocol="udp", address=target,
                    hop_count=rng.randint(6, 14), successes=10 - failures, failures=failures, base=1,
                )
                if failures < 10:
                    row.update(rtt_stats(rng, base_rtt * mult))
                rows.append(row)
    return to_csv(SOCIAL_HEADER, rows)


def gen_video(rng, day, incident):
    rows = []
    for v_idx, (service, region, target) in enumerate(VIDEO_SERVICES):
        base_rtt = rng.uniform(22_000, 48_000)
        for unit_id in UNITS:
            for hour in schedule(unit_id, VIDEO_EVERY_H, v_idx):
                fail_p, mult = conditions_at(unit_id, hour, incident)
                local, _ = test_time(rng, day, hour)
                failures = sum(rng.random() < fail_p * 1.2 for _ in range(10))
                row = dict(
                    unit_id=unit_id, dtime=fmt(local), service=service, region=region,
                    target=target, name_resolution_protocol="udp", address=target,
                    successes=10 - failures, failures=failures, location_id=1,
                )
                if failures < 10:
                    row.update(rtt_stats(rng, base_rtt * mult))
                rows.append(row)
    return to_csv(VIDEO_HEADER, rows)


def gen_dns(rng, day, incident, ip_version):
    rows = []
    for n_idx, nameserver in enumerate(DNS_NAMESERVERS[ip_version]):
        base_rtt = rng.uniform(4_000, 9_000) * (1.3 if ip_version == "6" else 1.0)
        for unit_id in UNITS:
            for h_idx, hour in enumerate(schedule(unit_id, DNS_EVERY_H, n_idx)):
                fail_p, mult = conditions_at(unit_id, hour, incident)
                local, _ = test_time(rng, day, hour)
                failed = rng.random() < fail_p * 0.5
                host = DNS_HOSTS[(h_idx + n_idx) % len(DNS_HOSTS)]
                rows.append(dict(
                    unit_id=unit_id, dtime=fmt(local), nameserver=nameserver, lookup_host=host,
                    response_ip="" if failed else f"198.51.100.{rng.randint(1, 254)}",
                    rtt="" if failed else int(max(500, rng.gauss(base_rtt * mult, base_rtt * 0.2))),
                    successes=0 if failed else 1, failures=1 if failed else 0, location_id=1,
                ))
    return to_csv(DNS_HEADER, rows)


def gen_disconnections(rng, day, incident):
    rows = []
    for unit_id, op in UNITS.items():
        rate = OPERATOR_PROFILE[op]["disc_rate"]
        if incident and incident["operator"] == op:
            rate += len(incident["hours"]) * 0.5
        # Poisson draw via Knuth (rates are small)
        n, p, limit = 0, 1.0, math.exp(-rate)
        while True:
            p *= rng.random()
            if p <= limit:
                break
            n += 1
        for _ in range(n):
            if incident and incident["operator"] == op and rng.random() < 0.7:
                hour = rng.choice(sorted(incident["hours"]))
            else:
                hour = rng.randint(0, 23)
            start, _ = test_time(rng, day, hour)
            seconds = max(2, int(rng.lognormvariate(math.log(20), 1.1)))
            end = min(start + timedelta(seconds=seconds),
                      datetime.combine(day, datetime.max.time()).replace(microsecond=0))
            rows.append(dict(
                unit_id=unit_id, dtime=fmt(start), end_dtime=fmt(end),
                target="disconnect.demo.net", address="203.0.113.10",
                duration=int((end - start).total_seconds() * 1_000_000),  # µs, as the parser expects
                packets=max(1, int(seconds / 2)),
            ))
    rows.sort(key=lambda r: r["dtime"])
    return to_csv(DISC_HEADER, rows)


# ── ARCHIVE ───────────────────────────────────────────────────────────────────
def archive_name(day):
    return f"{day:%Y%m%d}-{ARCHIVE_SUFFIX}.tar.gz"


def build_files(day):
    rng = random.Random(f"goeye-samknows-{day}")
    incident = day_conditions(rng)
    files = gen_games(rng, day, incident)
    files["curr_social_media.csv"] = gen_social(rng, day, incident)
    files["curr_video_conferencing.csv"] = gen_video(rng, day, incident)
    files["curr_dns.csv"] = gen_dns(rng, day, incident, "4")
    files["curr_dns6.csv"] = gen_dns(rng, day, incident, "6")
    files["curr_disconnection.csv"] = gen_disconnections(rng, day, incident)
    return files, incident


def write_archive(day, out_dir):
    """Write one archive; byte-identical across runs (fixed mtimes, sorted entries)."""
    files, incident = build_files(day)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / archive_name(day)
    mtime = int(datetime.combine(day + timedelta(days=1), datetime.min.time(),
                                 tzinfo=timezone.utc).timestamp())

    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        dir_info = tarfile.TarInfo("deltadata")
        dir_info.type, dir_info.mode, dir_info.mtime = tarfile.DIRTYPE, 0o755, mtime
        tar.addfile(dir_info)
        for name in sorted(files):
            data = files[name]
            info = tarfile.TarInfo(f"deltadata/{name}")
            info.size, info.mode, info.mtime = len(data), 0o644, mtime
            tar.addfile(info, io.BytesIO(data))

    with open(path, "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=mtime, filename="") as gz:
        gz.write(tar_buf.getvalue())

    rows = sum(data.count(b"\n") - 1 for data in files.values())
    note = f" incident: {incident['operator']} hours {min(incident['hours'])}-{max(incident['hours'])}" if incident else ""
    print(f"{path}  ({path.stat().st_size / 1024:.0f} KB, {rows} rows){note}")
    return path


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic SamKnows archives")
    yesterday_ksa = (datetime.now(timezone.utc) + KSA_UTC_OFFSET).date() - timedelta(days=1)
    parser.add_argument("--date", type=date.fromisoformat, default=yesterday_ksa,
                        help="Archive date (YYYY-MM-DD). Default: yesterday in KSA time.")
    parser.add_argument("--days", type=int, default=1, help="Number of days ending on --date")
    parser.add_argument("--out", default="samknows_sim/archives", help="Output directory")
    args = parser.parse_args()

    for i in range(args.days - 1, -1, -1):
        write_archive(args.date - timedelta(days=i), args.out)


if __name__ == "__main__":
    main()
