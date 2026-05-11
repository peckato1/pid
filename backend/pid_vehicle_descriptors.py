import argparse
import datetime
import logging
import time

from sqlalchemy.orm import Session

from pid.db import engine
from pid.vehicle_descriptors import enrich

logger = logging.getLogger(__name__)

# Sleep between cycles when there are no candidates.
IDLE_SLEEP = 30


def main():
    parser = argparse.ArgumentParser(description="Enrich rt_trip rows with descriptor data from per-service endpoint")
    parser.add_argument("--limit", type=int, default=None, help="Max trips to enrich in this run")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    while True:
        with Session(engine) as session:
            try:
                processed = enrich(session, limit=args.limit)
            except Exception:
                logger.exception("enrich cycle failed")
                session.rollback()
                processed = 0
        if processed == 0:
            until = (datetime.datetime.now() + datetime.timedelta(seconds=IDLE_SLEEP)).strftime("%H:%M:%S")
            logger.info("no candidates, sleeping %ds (until %s)", IDLE_SLEEP, until)
            time.sleep(IDLE_SLEEP)


if __name__ == "__main__":
    main()
