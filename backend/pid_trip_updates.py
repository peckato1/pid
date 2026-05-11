import argparse
import logging
import time

from sqlalchemy.orm import Session

from pid.db import engine
from pid.trip_updates import sync


def main():
    parser = argparse.ArgumentParser(description="Sync PID realtime feed to database")
    parser.add_argument("--route", action="append", metavar="ROUTE_ID", dest="routes", help="Filter by route id (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be inserted without writing to the database")
    parser.add_argument("--interval", type=float, metavar="SECONDS", help="Repeat sync every SECONDS (run once if omitted)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if args.verbose:
        logging.getLogger("pid.trip_updates").setLevel(logging.DEBUG)

    logger = logging.getLogger(__name__)

    routes = set(args.routes) if args.routes else None
    with Session(engine) as session:
        while True:
            sync(session, routes=routes, dry_run=args.dry_run)
            if args.interval is None:
                break
            logger.debug("sleeping %.1fs until next sync", args.interval)
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
