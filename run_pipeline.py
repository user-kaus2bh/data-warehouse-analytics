"""
run_pipeline.py — Main ETL pipeline runner.

Usage:
    python run_pipeline.py              # Full pipeline (generate → extract → transform → load)
    python run_pipeline.py --skip-gen   # Skip data generation (use existing raw files)
    python run_pipeline.py --only gen   # Only generate data
    python run_pipeline.py --only etl   # Only run extract/transform/load
"""

import sys
import time
import argparse
from pathlib import Path

# Allow imports from the etl directory
sys.path.insert(0, str(Path(__file__).parent / "etl"))

from logger import get_logger

log = get_logger("pipeline")


def run_generation():
    log.info("━━━ PHASE 0: DATA GENERATION ━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    from generate_data import main as generate_main
    generate_main()


def run_etl():
    log.info("━━━ PHASE 1: EXTRACT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    from extract import extract_all
    raw = extract_all()

    log.info("━━━ PHASE 2: TRANSFORM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    from transform import transform_all
    cleaned = transform_all(raw)

    log.info("━━━ PHASE 3: LOAD ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    from load import load_all
    results = load_all(cleaned)

    return results


def main():
    parser = argparse.ArgumentParser(description="Data Warehouse ETL Pipeline")
    parser.add_argument("--skip-gen", action="store_true", help="Skip data generation")
    parser.add_argument("--only",     choices=["gen", "etl"], help="Run only one phase")
    args = parser.parse_args()

    start_time = time.time()

    log.info("╔══════════════════════════════════════════════════════════╗")
    log.info("║     DATA WAREHOUSE ETL PIPELINE — DAY 1                 ║")
    log.info("╚══════════════════════════════════════════════════════════╝")

    try:
        if args.only == "gen":
            run_generation()
        elif args.only == "etl":
            run_etl()
        elif args.skip_gen:
            run_etl()
        else:
            run_generation()
            run_etl()

        elapsed = time.time() - start_time
        log.info("╔══════════════════════════════════════════════════════════╗")
        log.info(f"║  Pipeline complete in {elapsed:.1f}s                          ║")
        log.info("╚══════════════════════════════════════════════════════════╝")

    except Exception as e:
        log.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
