#main.py
import sys
import os
import threading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from database import SessionLocal
from models.scopes import Scope
from models.units import Unit
from models.daily_aggregates import DailyAggregate
from models.hourly_aggregates import HourlyAggregate
from datetime import date, datetime, timedelta
from pipeline.downloader import get_session, list_archives, parse_date_from_filename
from models.users import User
from sqlalchemy import func, case
from models.raw_game_latency import RawGameLatency
from models.raw_social_media import RawSocialMedia
from models.raw_video_conferencing import RawVideoConferencing
from models.raw_dns import RawDns
from models.applications import Application
from models.scope_units import ScopeUnit

JWT_SECRET      = os.getenv("JWT_SECRET", "fallback-dev-secret-change-in-production")
JWT_ALGORITHM   = "HS256"
JWT_EXPIRE_MINS = 480  # 8 hours - one working day

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme  = OAuth2PasswordBearer(tokenUrl="/auth/login")

app = FastAPI(title="GoEye Network Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    full_name: str
    role: str

class UserInfo(BaseModel):
    username:  str
    email:     str
    full_name: str
    role:      str

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINS)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload  = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == username).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return user
    finally:
        session.close()

# ── GAMING BREAKDOWN ──────────────────────────────────────────
@app.get("/api/gaming/breakdown")
def get_gaming_breakdown(
    scope_name: str = Query(...),
    agg_date: date = Query(...),
    current_user: User = Depends(get_current_user)
):
    session = SessionLocal()
    try:
        # Get unit_ids for this scope
        scope = session.query(Scope).filter(Scope.scope_name == scope_name).first()
        if not scope:
            raise HTTPException(status_code=404, detail="Scope not found")
        unit_ids_int = [su.unit_id for su in session.query(ScopeUnit).filter(ScopeUnit.scope_id == scope.id).all()]
        unit_ids = [str(u) for u in unit_ids_int]

        rows = session.query(
            RawGameLatency.app_key,
            func.avg(RawGameLatency.rtt_avg).label('rtt_avg'),
            func.min(RawGameLatency.rtt_min).label('rtt_min'),
            func.max(RawGameLatency.rtt_max).label('rtt_max'),
            func.avg(RawGameLatency.rtt_std).label('rtt_std'),
            func.sum(RawGameLatency.successes).label('successes'),
            func.sum(RawGameLatency.failures).label('failures'),
            func.avg(RawGameLatency.hop_count).label('avg_hops'),
            func.count(RawGameLatency.id).label('total_sessions'),
        ).filter(
            RawGameLatency.archive_date == agg_date,
            RawGameLatency.unit_id.in_(unit_ids)
        ).group_by(RawGameLatency.app_key).all()

        # Also get provider/datacenter breakdown
        provider_rows = session.query(
            RawGameLatency.provider,
            RawGameLatency.datacenter,
            RawGameLatency.region,
            func.avg(RawGameLatency.rtt_avg).label('rtt_avg'),
            func.sum(RawGameLatency.successes).label('successes'),
            func.sum(RawGameLatency.failures).label('failures'),
        ).filter(
            RawGameLatency.archive_date == agg_date,
            RawGameLatency.unit_id.in_(unit_ids),
            RawGameLatency.provider.isnot(None),
            RawGameLatency.provider != ''
        ).group_by(
            RawGameLatency.provider,
            RawGameLatency.datacenter,
            RawGameLatency.region
        ).order_by(func.avg(RawGameLatency.rtt_avg)).limit(20).all()

        games = []
        for r in rows:
            total = (r.successes or 0) + (r.failures or 0)
            reliability = round(r.successes / total * 100, 4) if total > 0 else None
            app = session.query(Application).filter(Application.file_key == r.app_key).first()
            games.append({
                'app_key':      r.app_key,
                'app_name':     app.app_name if app else r.app_key,
                'rtt_avg_ms':   round(r.rtt_avg / 1000, 2) if r.rtt_avg else None,
                'rtt_min_ms':   round(r.rtt_min / 1000, 2) if r.rtt_min else None,
                'rtt_max_ms':   round(r.rtt_max / 1000, 2) if r.rtt_max else None,
                'rtt_std_ms':   round(r.rtt_std / 1000, 2) if r.rtt_std else None,
                'reliability':  reliability,
                'successes':    int(r.successes or 0),
                'failures':     int(r.failures or 0),
                'total_tests':  int(total),
                'avg_hops':     round(r.avg_hops, 1) if r.avg_hops else None,
            })

        games.sort(key=lambda x: x['rtt_avg_ms'] or 9999)

        providers = [{
            'provider':    r.provider,
            'datacenter':  r.datacenter,
            'region':      r.region,
            'rtt_avg_ms':  round(r.rtt_avg / 1000, 2) if r.rtt_avg else None,
            'successes':   int(r.successes or 0),
            'failures':    int(r.failures or 0),
        } for r in provider_rows]

        return { 'games': games, 'providers': providers }
    finally:
        session.close()


# ── SOCIAL BREAKDOWN ──────────────────────────────────────────
@app.get("/api/social/breakdown")
def get_social_breakdown(
    scope_name: str = Query(...),
    agg_date: date = Query(...),
    current_user: User = Depends(get_current_user)
):
    session = SessionLocal()
    try:
        scope = session.query(Scope).filter(Scope.scope_name == scope_name).first()
        if not scope:
            raise HTTPException(status_code=404, detail="Scope not found")
        unit_ids_int = [su.unit_id for su in session.query(ScopeUnit).filter(ScopeUnit.scope_id == scope.id).all()]
        unit_ids = [str(u) for u in unit_ids_int]

        rows = session.query(
            RawSocialMedia.service,
            RawSocialMedia.media,
            RawSocialMedia.direction,
            RawSocialMedia.target,
            func.avg(RawSocialMedia.rtt_avg).label('rtt_avg'),
            func.avg(RawSocialMedia.rtt_median).label('rtt_median'),
            func.sum(RawSocialMedia.successes).label('successes'),
            func.sum(RawSocialMedia.failures).label('failures'),
            func.count(RawSocialMedia.id).label('sessions'),
        ).filter(
            RawSocialMedia.archive_date == agg_date,
            RawSocialMedia.unit_id.in_(unit_ids)
        ).group_by(
            RawSocialMedia.service,
            RawSocialMedia.media,
            RawSocialMedia.direction,
            RawSocialMedia.target,
        ).all()

        services = []
        for r in rows:
            total = (r.successes or 0) + (r.failures or 0)
            reliability = round(r.successes / total * 100, 4) if total > 0 else None
            target_lower = (r.target or '').lower()
            is_cdn = any(x in target_lower for x in ['cdn', 'go_cdn', '_cdn', 'edge'])
            services.append({
                'service':      r.service,
                'media':        r.media,
                'direction':    r.direction,
                'target':       r.target,
                'rtt_avg_ms':   round(r.rtt_avg / 1000, 2) if r.rtt_avg else None,
                'rtt_median_ms': round(r.rtt_median / 1000, 2) if r.rtt_median else None,
                'reliability':  reliability,
                'successes':    int(r.successes or 0),
                'failures':     int(r.failures or 0),
                'total_tests':  int(total),
                'is_cdn':       is_cdn,
            })

        services.sort(key=lambda x: x['rtt_avg_ms'] or 9999)
        return { 'services': services }
    finally:
        session.close()


# ── VIDEO BREAKDOWN ───────────────────────────────────────────
@app.get("/api/video/breakdown")
def get_video_breakdown(
    scope_name: str = Query(...),
    agg_date: date = Query(...),
    current_user: User = Depends(get_current_user)
):
    session = SessionLocal()
    try:
        scope = session.query(Scope).filter(Scope.scope_name == scope_name).first()
        if not scope:
            raise HTTPException(status_code=404, detail="Scope not found")
        unit_ids_int = [su.unit_id for su in session.query(ScopeUnit).filter(ScopeUnit.scope_id == scope.id).all()]
        unit_ids = [str(u) for u in unit_ids_int]

        rows = session.query(
            RawVideoConferencing.service,
            RawVideoConferencing.region,
            RawVideoConferencing.target,
            func.avg(RawVideoConferencing.rtt_avg).label('rtt_avg'),
            func.avg(RawVideoConferencing.rtt_median).label('rtt_median'),
            func.min(RawVideoConferencing.rtt_avg).label('rtt_best'),
            func.max(RawVideoConferencing.rtt_avg).label('rtt_worst'),
            func.sum(RawVideoConferencing.successes).label('successes'),
            func.sum(RawVideoConferencing.failures).label('failures'),
            func.count(RawVideoConferencing.id).label('sessions'),
        ).filter(
            RawVideoConferencing.archive_date == agg_date,
            RawVideoConferencing.unit_id.in_(unit_ids)
        ).group_by(
            RawVideoConferencing.service,
            RawVideoConferencing.region,
            RawVideoConferencing.target,
        ).all()

        platforms = []
        for r in rows:
            total = (r.successes or 0) + (r.failures or 0)
            reliability = round(r.successes / total * 100, 4) if total > 0 else None
            platforms.append({
                'service':       r.service,
                'region':        r.region,
                'target':        r.target,
                'rtt_avg_ms':    round(r.rtt_avg / 1000, 2) if r.rtt_avg else None,
                'rtt_median_ms': round(r.rtt_median / 1000, 2) if r.rtt_median else None,
                'rtt_best_ms':   round(r.rtt_best / 1000, 2) if r.rtt_best else None,
                'rtt_worst_ms':  round(r.rtt_worst / 1000, 2) if r.rtt_worst else None,
                'reliability':   reliability,
                'successes':     int(r.successes or 0),
                'failures':      int(r.failures or 0),
                'total_tests':   int(total),
            })

        platforms.sort(key=lambda x: x['rtt_avg_ms'] or 9999)
        return { 'platforms': platforms }
    finally:
        session.close()


# ── DNS DETAIL ────────────────────────────────────────────────
@app.get("/api/dns/detail")
def get_dns_detail(
        scope_name: str = Query(...),
        agg_date: date = Query(...),
        current_user: User = Depends(get_current_user)
):
    session = SessionLocal()
    try:
        scope = session.query(Scope).filter(Scope.scope_name == scope_name).first()
        if not scope:
            raise HTTPException(status_code=404, detail="Scope not found")

        # Get unit IDs for this scope
        unit_ids_int = [su.unit_id for su in session.query(ScopeUnit).filter(ScopeUnit.scope_id == scope.id).all()]
        unit_ids_str = [str(u) for u in unit_ids_int]

        results = {}

        # Only ONE loop, using strings for ip_version
        for ip_ver in ['4', '6']:
            rows = session.query(
                RawDns.nameserver,
                func.sum(RawDns.successes).label('successes'),
                func.sum(RawDns.failures).label('failures'),
                func.avg(RawDns.rtt).label('rtt_avg'),
            ).filter(
                RawDns.archive_date == agg_date,
                RawDns.unit_id.in_(unit_ids_str),
                RawDns.ip_version == ip_ver  # Compare string with string
            ).group_by(RawDns.nameserver).all()

            print(f"Rows returned for v{ip_ver}: {len(rows)}")

            nameservers = []
            total_tests_all = 0
            dead_tests = 0

            for r in rows:
                total = (r.successes or 0) + (r.failures or 0)
                reliability = round(r.successes / total * 100, 4) if total > 0 else 0
                is_dead = reliability < 1.0
                total_tests_all += total
                if is_dead:
                    dead_tests += total
                nameservers.append({
                    'nameserver': r.nameserver,
                    'reliability': reliability,
                    'successes': int(r.successes or 0),
                    'failures': int(r.failures or 0),
                    'total_tests': int(total),
                    'rtt_avg_ms': round(r.rtt_avg, 2) if r.rtt_avg else None,
                    'is_dead': is_dead,
                })

            nameservers.sort(key=lambda x: x['reliability'])
            dead_share = round(dead_tests / total_tests_all * 100, 2) if total_tests_all > 0 else 0

            # Top failing lookup hosts
            host_rows = session.query(
                RawDns.lookup_host,
                func.sum(RawDns.successes).label('successes'),
                func.sum(RawDns.failures).label('failures'),
            ).filter(
                RawDns.archive_date == agg_date,
                RawDns.unit_id.in_(unit_ids_str),
                RawDns.ip_version == ip_ver,
                RawDns.failures > 0
            ).group_by(RawDns.lookup_host).order_by(
                func.sum(RawDns.failures).desc()
            ).limit(10).all()

            top_failing = [{
                'host': r.lookup_host,
                'successes': int(r.successes or 0),
                'failures': int(r.failures or 0),
                'fail_rate': round(r.failures / ((r.successes or 0) + (r.failures or 0)) * 100, 2) if (
                                                                                                                  r.successes or 0) + (
                                                                                                                  r.failures or 0) > 0 else 0
            } for r in host_rows]

            results[f'v{ip_ver}'] = {
                'nameservers': nameservers,
                'dead_share_pct': dead_share,
                'top_failing_hosts': top_failing,
            }

        return results
    except Exception as e:
        print(f"DNS endpoint error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        session.close()

# ── TREND TIME SERIES ─────────────────────────────────────────
@app.get("/api/trends")
def get_trends(
    scope_name: str = Query(...),
    current_user: User = Depends(get_current_user)
):
    session = SessionLocal()
    try:
        scope = session.query(Scope).filter(Scope.scope_name == scope_name).first()
        if not scope:
            raise HTTPException(status_code=404, detail="Scope not found")

        from sqlalchemy import distinct
        rows = session.query(DailyAggregate).filter(
            DailyAggregate.scope_id == scope.id
        ).order_by(DailyAggregate.agg_date.asc()).all()

        # Build time series keyed by date
        by_date = {}
        for r in rows:
            d = str(r.agg_date)
            if d not in by_date:
                by_date[d] = {}
            by_date[d][r.category] = {
                'reliability':          r.reliability_pct,
                'weighted_reliability': r.weighted_reliability_pct,
                'uptime':               r.uptime_pct,
                'disconnections':       r.total_disconnections,
                'dns_v4_reliability':   r.dns_v4_reliability,
                'dns_v6_reliability':   r.dns_v6_reliability,
                'dns_v4_rtt_p50':       r.dns_v4_rtt_p50,
                'dns_v6_rtt_p50':       r.dns_v6_rtt_p50,
            }

        return { 'dates': sorted(by_date.keys()), 'data': by_date }
    finally:
        session.close()


@app.post("/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    print(f"\n=== LOGIN ATTEMPT ===")
    print(f"Username: {form_data.username}")
    print(f"Password length: {len(form_data.password)}")

    session = SessionLocal()
    try:
        user = session.query(User).filter(
            User.username == form_data.username
        ).first()

        if not user:
            print(f"❌ User not found: {form_data.username}")
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password"
            )

        print(f"✅ User found: {user.username}")
        print(f"Hash type: {'bcrypt' if user.hashed_password.startswith('$2b$') else 'other'}")

        is_valid = verify_password(form_data.password, user.hashed_password)
        print(f"Password valid: {is_valid}")

        if not is_valid:
            print(f"❌ Invalid password")
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password"
            )

        if not user.is_active:
            print(f"❌ User inactive")
            raise HTTPException(status_code=401, detail="Account is disabled")

        token = create_access_token({"sub": user.username})
        print(f"✅ Login successful, token generated")
        print(f"=== END LOGIN ===\n")

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            full_name=user.full_name or user.username,
            role=user.role,
        )
    finally:
        session.close()



@app.get("/api/available-dates")
def get_available_dates( current_user: User = Depends(get_current_user)):
    """Lists all archive dates available on SamKnows server.
    Returns an empty list when SamKnows credentials are not configured so the
    dashboard falls back to already-loaded dates without a 500 error.
    """
    samknows_url = os.getenv("SAMKNOWS_URL")
    if not samknows_url:
        return []
    try:
        session = get_session()
        archives = list_archives(session)
        dates = []
        seen = set()
        for filename in archives:
            d = parse_date_from_filename(filename)
            if d:
                date_str = str(d)
                if date_str not in seen:
                    seen.add(date_str)
                    dates.append(date_str)
        return sorted(dates, reverse=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not fetch server archives: {str(e)}")


@app.get("/api/loaded-dates")
def get_loaded_dates( current_user: User = Depends(get_current_user)):
    """Lists dates already processed and in the database."""
    session = SessionLocal()
    try:
        from sqlalchemy import distinct
        dates = session.query(distinct(DailyAggregate.agg_date))\
            .order_by(DailyAggregate.agg_date.desc()).all()
        return [str(d[0]) for d in dates]
    finally:
        session.close()


processing_jobs = {}  # track in-progress jobs
processing_lock = threading.Lock()

def normalize_date_str(date_str: str):
    return date_str.replace('-', '')


def _get_load_status_for_date(date_str: str):
    date_str = normalize_date_str(date_str)
    with processing_lock:
        status = processing_jobs.get(date_str, "not_started")

    if status == "not_started":
        session = SessionLocal()
        try:
            agg_date = datetime.strptime(date_str, "%Y%m%d").date()
            count = session.query(DailyAggregate) \
                .filter(DailyAggregate.agg_date == agg_date).count()
            if count > 0:
                return "done"
        finally:
            session.close()

    return status


@app.post("/api/load-date/{date_str}")
def load_date(date_str: str):
    """Download and process a specific archive date on demand."""
    date_str = normalize_date_str(date_str)

    # Validate format
    try:
        datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must be in YYYYMMDD format")

    # Check if already loaded
    session = SessionLocal()
    try:
        agg_date = datetime.strptime(date_str, "%Y%m%d").date()
        count = session.query(DailyAggregate) \
            .filter(DailyAggregate.agg_date == agg_date).count()
        if count > 0:
            return {"status": "already_loaded", "date": date_str}
    finally:
        session.close()

    # Check if already processing
    with processing_lock:
        if processing_jobs.get(date_str) == "processing":
            return {"status": "processing", "date": date_str}
        processing_jobs[date_str] = "processing"

    def run():
        try:
            from pipeline.run_pipeline import process_one_date
            from pipeline.downloader import download_specific_date
            result = download_specific_date(date_str)
            if result:
                date_str_val, archive_path, deltadata_path = result
                process_one_date(date_str_val, deltadata_path)
            with processing_lock:
                processing_jobs[date_str] = "done"
        except Exception as e:
            with processing_lock:
                processing_jobs[date_str] = f"error: {str(e)}"

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return {"status": "processing", "date": date_str}


class LoadDatesRequest(BaseModel):
    dates: List[str]


@app.post("/api/load-dates")
def load_dates(request: LoadDatesRequest):
    dates = request.dates
    if not dates:
        raise HTTPException(status_code=400, detail="No dates provided")

    statuses = []
    for date_str in dates:
        date_str = normalize_date_str(date_str)
        try:
            datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {date_str}")

        session = SessionLocal()
        try:
            agg_date = datetime.strptime(date_str, "%Y%m%d").date()
            count = session.query(DailyAggregate) \
                .filter(DailyAggregate.agg_date == agg_date).count()
            if count > 0:
                statuses.append({"date": date_str, "status": "done"})
                continue
        finally:
            session.close()

        with processing_lock:
            current_status = processing_jobs.get(date_str)
            if current_status == "processing":
                statuses.append({"date": date_str, "status": "processing"})
                continue
            processing_jobs[date_str] = "processing"

        def run(date_str=date_str):
            try:
                from pipeline.run_pipeline import process_one_date
                from pipeline.downloader import download_specific_date
                result = download_specific_date(date_str)
                if result:
                    date_str_val, archive_path, deltadata_path = result
                    process_one_date(date_str_val, deltadata_path)
                with processing_lock:
                    processing_jobs[date_str] = "done"
            except Exception as e:
                with processing_lock:
                    processing_jobs[date_str] = f"error: {str(e)}"

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        statuses.append({"date": date_str, "status": "processing"})

    return {"statuses": statuses}


@app.get("/api/load-statuses")
def get_load_statuses(dates: str,  current_user: User = Depends(get_current_user)):
    if not dates:
        raise HTTPException(status_code=400, detail="No dates provided")

    results = []
    for date_str in dates.split(','):
        date_str = normalize_date_str(date_str)
        status = _get_load_status_for_date(date_str)
        results.append({"date": date_str, "status": status})

    return {"statuses": results}


@app.get("/api/load-status/{date_str}")
def get_load_status(date_str: str,  current_user: User = Depends(get_current_user)):
    """Check if a date is being processed."""
    date_str_normalized = normalize_date_str(date_str)
    status = _get_load_status_for_date(date_str_normalized)
    return {"status": status, "date": date_str_normalized}


@app.get("/api/scopes")
def get_scopes(  current_user: User = Depends(get_current_user) ):
    session = SessionLocal()
    try:
        scopes = session.query(Scope).all()
        return [
            {
                "id":                s.id,
                "scope_name":        s.scope_name,
                "operator_filter":   s.operator_filter,
                "technology_filter": s.technology_filter,
            }
            for s in scopes
        ]
    finally:
        session.close()

@app.get("/api/dates")
def get_available_dates(  current_user: User = Depends(get_current_user) ):
    session = SessionLocal()
    try:
        from sqlalchemy import distinct
        dates = session.query(distinct(DailyAggregate.agg_date))\
            .order_by(DailyAggregate.agg_date.desc())\
            .all()
        return [str(d[0]) for d in dates]
    finally:
        session.close()


@app.get("/api/units")
def get_units(  current_user: User = Depends(get_current_user) ):
    session = SessionLocal()
    try:
        units = session.query(Unit).filter(Unit.is_active == True).all()
        return [
            {
                "unit_id":    u.unit_id,
                "unit_name":  u.unit_name,
                "operator":   u.operator,
                "technology": u.technology,
                "identifier": u.identifier,
            }
            for u in units
        ]
    finally:
        session.close()

@app.get("/api/daily")
def get_daily(
    scope_name: str = Query(...),
    agg_date: Optional[date] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user)
):
    session = SessionLocal()
    try:
        scope = session.query(Scope).filter(
            Scope.scope_name == scope_name
        ).first()
        if not scope:
            raise HTTPException(status_code=404, detail=f"Scope '{scope_name}' not found")

        if start_date or end_date:
            if agg_date is not None:
                raise HTTPException(status_code=422, detail="Use either agg_date or start_date/end_date, not both")
            if not start_date or not end_date:
                raise HTTPException(status_code=422, detail="Both start_date and end_date are required for a date range")
            if start_date > end_date:
                raise HTTPException(status_code=422, detail="start_date must be before or equal to end_date")

            rows = session.query(DailyAggregate).filter(
                DailyAggregate.scope_id == scope.id,
                DailyAggregate.agg_date >= start_date,
                DailyAggregate.agg_date <= end_date
            ).order_by(DailyAggregate.agg_date.asc()).all()
            if not rows:
                raise HTTPException(status_code=404, detail="No data found for this scope and date range")

            metrics_by_date = {}
            for row in rows:
                date_key = str(row.agg_date)
                if date_key not in metrics_by_date:
                    metrics_by_date[date_key] = {}
                metrics_by_date[date_key][row.category] = {
                    "reliability_pct":          row.reliability_pct,
                    "weighted_reliability_pct": row.weighted_reliability_pct,
                    "uptime_pct":               row.uptime_pct,
                    "total_tests":              row.total_tests,
                    "total_disconnections":     row.total_disconnections,
                    "median_disconnection_sec": row.median_disconnection_sec,
                    "dns_v4_reliability":       row.dns_v4_reliability,
                    "dns_v6_reliability":       row.dns_v6_reliability,
                    "dns_v4_rtt_p50":           row.dns_v4_rtt_p50,
                    "dns_v6_rtt_p50":           row.dns_v6_rtt_p50,
                }

            return {
                "scope":          scope_name,
                "start_date":     str(start_date),
                "end_date":       str(end_date),
                "metrics_by_date": metrics_by_date
            }

        if agg_date is None:
            raise HTTPException(status_code=422, detail="Either agg_date or both start_date and end_date must be provided")

        rows = session.query(DailyAggregate).filter(
            DailyAggregate.scope_id == scope.id,
            DailyAggregate.agg_date == agg_date
        ).all()
        if not rows:
            raise HTTPException(status_code=404, detail="No data found for this scope and date")

        result = {}
        for row in rows:
            result[row.category] = {
                "reliability_pct":          row.reliability_pct,
                "weighted_reliability_pct": row.weighted_reliability_pct,
                "uptime_pct":               row.uptime_pct,
                "total_tests":              row.total_tests,
                "total_disconnections":     row.total_disconnections,
                "median_disconnection_sec": row.median_disconnection_sec,
                "dns_v4_reliability":       row.dns_v4_reliability,
                "dns_v6_reliability":       row.dns_v6_reliability,
                "dns_v4_rtt_p50":           row.dns_v4_rtt_p50,
                "dns_v6_rtt_p50":           row.dns_v6_rtt_p50,
            }

        return {
            "scope":   scope_name,
            "date":    str(agg_date),
            "metrics": result
        }
    finally:
        session.close()

@app.get("/api/hourly")
def get_hourly(
    scope_name: str = Query(...),
    agg_date: date = Query(...),
    category: str = Query(...),
    current_user: User = Depends(get_current_user)
):
    session = SessionLocal()
    try:
        scope = session.query(Scope).filter(
            Scope.scope_name == scope_name
        ).first()
        if not scope:
            raise HTTPException(status_code=404, detail=f"Scope '{scope_name}' not found")

        rows = session.query(HourlyAggregate).filter(
            HourlyAggregate.scope_id == scope.id,
            HourlyAggregate.agg_date == agg_date,
            HourlyAggregate.category == category
        ).order_by(HourlyAggregate.hour).all()
        if not rows:
            raise HTTPException(status_code=404, detail="No hourly data found")

        return {
            "scope":    scope_name,
            "date":     str(agg_date),
            "category": category,
            "hours": [
                {
                    "hour":                  r.hour,
                    "fail_rate_pct":         r.fail_rate_pct,
                    "disconnection_minutes": r.disconnection_minutes,
                }
                for r in rows
            ]
        }
    finally:
        session.close()


@app.get("/api/comparison/{agg_date}")
def get_comparison(agg_date: date, current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    try:
        scopes = session.query(Scope).filter(
            Scope.scope_name.in_(["GO/FTTH", "KSA Average"])
        ).all()
        if not scopes:
            raise HTTPException(status_code=404, detail="Scopes not found")

        result = {}
        for scope in scopes:
            rows = session.query(DailyAggregate).filter(
                DailyAggregate.scope_id == scope.id,
                DailyAggregate.agg_date == agg_date,
                DailyAggregate.category == "Combined"
            ).first()
            if rows:
                result[scope.scope_name] = {
                    "reliability_pct":          rows.reliability_pct,
                    "weighted_reliability_pct": rows.weighted_reliability_pct,
                    "uptime_pct":               rows.uptime_pct,
                    "total_disconnections":     rows.total_disconnections,
                    "median_disconnection_sec": rows.median_disconnection_sec,
                    "dns_v4_reliability":       rows.dns_v4_reliability,
                    "dns_v6_reliability":       rows.dns_v6_reliability,
                    "dns_v4_rtt_p50":           rows.dns_v4_rtt_p50,
                    "dns_v6_rtt_p50":           rows.dns_v6_rtt_p50,
                }

        return {
            "date":   str(agg_date),
            "scopes": result
        }
    finally:
        session.close()