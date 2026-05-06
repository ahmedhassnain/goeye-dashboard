# downloader.py
import os
import requests
import hashlib
import logging
import tarfile
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger(__name__)

BASE_URL = os.getenv("SAMKNOWS_URL")
USERNAME = os.getenv("SAMKNOWS_USER")
PASSWORD = os.getenv("SAMKNOWS_PASS")

RAW_DIR     = Path(__file__).parent.parent / "raw"
STAGING_DIR = Path(__file__).parent.parent / "staging"


def get_session():
    session = requests.Session()
    session.auth = (USERNAME, PASSWORD)
    return session


def list_archives(session):
    log.info(f"Fetching archive listing from {BASE_URL}")
    response = session.get(BASE_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    seen = set()
    archives = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.endswith('.tar.gz') or href.endswith('.tar'):
            filename = os.path.basename(href.rstrip('/'))
            if filename not in seen:
                seen.add(filename)
                archives.append(filename)
    log.info(f"Found {len(archives)} archives.")
    return sorted(archives)


def parse_date_from_filename(filename):
    try:
        date_part = filename.split('-')[0]
        return datetime.strptime(date_part, "%Y%m%d").date()
    except (ValueError, IndexError):
        return None


def get_already_downloaded():
    if not RAW_DIR.exists():
        return set()
    downloaded = set()
    for folder in RAW_DIR.iterdir():
        if folder.is_dir():
            try:
                datetime.strptime(folder.name, "%Y%m%d")
                downloaded.add(folder.name)
            except ValueError:
                pass
    return downloaded


def compute_checksum(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def download_archive(session, filename, dest_folder):
    dest_folder = Path(dest_folder)
    dest_folder.mkdir(parents=True, exist_ok=True)
    dest_path = dest_folder / filename

    if dest_path.exists():
        log.info(f"Already exists: {dest_path} - skipping.")
        return str(dest_path)

    url = f"{BASE_URL.rstrip('/')}/{filename}"
    log.info(f"Downloading {filename} from {url}")

    response = session.get(url, stream=True, timeout=120)
    response.raise_for_status()

    total      = int(response.headers.get('content-length', 0))
    downloaded = 0

    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  Progress: {pct:.1f}% ({downloaded/1024/1024:.1f} MB)", end='', flush=True)

    print()
    log.info(f"Download complete: {dest_path}")
    checksum = compute_checksum(dest_path)
    log.info(f"SHA-256: {checksum}")
    with open(str(dest_path) + '.sha256', 'w') as f:
        f.write(checksum)

    return str(dest_path)


def extract_archive(archive_path, date_str):
    staging_path = STAGING_DIR / date_str
    staging_path.mkdir(parents=True, exist_ok=True)
    log.info(f"Extracting {archive_path} to {staging_path}")
    with tarfile.open(archive_path, 'r:gz') as tar:
        tar.extractall(path=staging_path)
    log.info(f"Extraction complete: {staging_path}")
    return str(staging_path)


def find_deltadata_path(staging_path):
    staging = Path(staging_path)
    for item in staging.rglob('deltadata'):
        if item.is_dir():
            return str(item)
    log.warning("Could not find deltadata folder in extracted archive.")
    return None


def download_latest(force=False):
    session      = get_session()
    archives     = list_archives(session)
    already_done = get_already_downloaded()

    if not force:
        new_archives = [
            a for a in archives
            if parse_date_from_filename(a) is not None
            and parse_date_from_filename(a).strftime("%Y%m%d") not in already_done
        ]
    else:
        new_archives = archives

    if not new_archives:
        log.info("No new archives to download.")
        return []

    log.info(f"{len(new_archives)} new archive(s) to process.")
    results = []

    for filename in new_archives:
        archive_date = parse_date_from_filename(filename)
        if not archive_date:
            log.warning(f"Could not parse date from {filename} - skipping.")
            continue

        date_str    = archive_date.strftime("%Y%m%d")
        dest_folder = RAW_DIR / date_str

        try:
            archive_path   = download_archive(session, filename, dest_folder)
            staging_path   = extract_archive(archive_path, date_str)
            deltadata_path = find_deltadata_path(staging_path)

            if deltadata_path:
                results.append((date_str, archive_path, deltadata_path))
                log.info(f"Ready to process: {deltadata_path}")
            else:
                log.error(f"No deltadata found for {date_str}")

        except Exception as e:
            log.error(f"Failed to process {filename}: {e}")
            continue

    return results


def download_specific_date(date_str):
    session  = get_session()
    archives = list_archives(session)
    matching = [a for a in archives if a.startswith(date_str)]

    if not matching:
        log.error(f"No archive found for date {date_str}")
        return None

    filename     = matching[0]
    dest_folder  = RAW_DIR / date_str
    archive_path = download_archive(session, filename, dest_folder)
    staging_path = extract_archive(archive_path, date_str)
    deltadata    = find_deltadata_path(staging_path)

    if deltadata:
        return (date_str, archive_path, deltadata)
    return None


if __name__ == "__main__":
    results = download_latest()
    if results:
        print(f"\nReady to process {len(results)} archive(s):")
        for date_str, archive_path, deltadata_path in results:
            print(f"  {date_str}")
            print(f"    Archive:   {archive_path}")
            print(f"    Deltadata: {deltadata_path}")
    else:
        print("Nothing new to download.")
