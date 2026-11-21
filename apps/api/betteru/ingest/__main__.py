import argparse
import logging
import sys
from pathlib import Path

from betteru.db import SessionLocal
from betteru.ingest.documents import ingest_pdfs, ingest_web
from betteru.ingest.exercises import ingest_exercises
from betteru.ingest.foods import ingest_foods

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m betteru.ingest", description="Load BetterU reference data")
    parser.add_argument("what", choices=["foods", "exercises", "docs", "all"], nargs="?", default="all")
    parser.add_argument("--force", action="store_true", help="Reload even if data is already present")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    failures = 0
    with SessionLocal() as db:
        if args.what in ("foods", "all"):
            ingest_foods(db, DATA_DIR / "raw", force=args.force)
        if args.what in ("exercises", "all"):
            ingest_exercises(db, force=args.force)
        if args.what in ("docs", "all"):
            failures += ingest_web(db, force=args.force)
            (DATA_DIR / "pdfs").mkdir(parents=True, exist_ok=True)
            ingest_pdfs(db, DATA_DIR / "pdfs", force=args.force)
    if failures:
        logging.warning("%d source(s) failed; re-run later to retry them.", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
