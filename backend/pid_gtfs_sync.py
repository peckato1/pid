import argparse
import logging
import zipfile
from datetime import date
from pathlib import Path

import requests
from sqlalchemy.orm import Session

from pid.db import engine
from pid.sync import sync, read_feed_start_date, synced_today


GTFS_URL = "https://data.pid.cz/PID_GTFS.zip"
DEFAULT_ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "gtfs_archives"


def download_archive(archive_dir: Path) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / f"PID_GTFS.{date.today():%Y%m%d}.zip"
    if target.exists():
        logging.info("Archive already exists: %s", target)
        return target
    logging.info("Downloading %s -> %s", GTFS_URL, target)
    tmp = target.with_suffix(".zip.part")
    with requests.get(GTFS_URL, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    tmp.rename(target)
    return target


def main():
    parser = argparse.ArgumentParser(description="Import PID GTFS data from a ZIP archive")
    parser.add_argument("zip_path", nargs="?", help="Path to the GTFS ZIP file (omit with --download)")
    parser.add_argument("--download", action="store_true", help="Download the latest GTFS archive before syncing")
    parser.add_argument("--archive-dir", default=str(DEFAULT_ARCHIVE_DIR), help="Directory to store downloaded archives")
    parser.add_argument("--if-stale", action="store_true", help="Skip if gtfs_feed_info shows a sync already applied today")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if args.verbose:
        logging.getLogger("pid.sync").setLevel(logging.DEBUG)

    if args.if_stale:
        with Session(engine) as session:
            if synced_today(session):
                print("Feed already synced today; skipping.")
                return

    if args.download:
        zip_path = download_archive(Path(args.archive_dir))
    elif args.zip_path:
        zip_path = Path(args.zip_path)
    else:
        parser.error("zip_path is required unless --download is given")

    with zipfile.ZipFile(zip_path) as zf:
        feed_date = read_feed_start_date(zf)
        print(f"Syncing GTFS feed valid from {feed_date}...")
        with Session(engine) as session:
            sync(session, zf)
    print("Done.")


if __name__ == "__main__":
    main()
