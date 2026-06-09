"""
run_pipeline.py — Master pipeline runner.

Usage:
    python run_pipeline.py                  # Full pipeline: generate → ETL → warehouse → analytics
    python run_pipeline.py --skip-gen       # Skip data generation
    python run_pipeline.py --only gen       # Only generate raw data
    python run_pipeline.py --only etl       # Only run ETL (extract/transform/load)
    python run_pipeline.py --only warehouse # Only build warehouse + analytics
"""

import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "etl"))
sys.path.insert(0, str(Path(__file__).parent / "warehouse"))
sys.path.insert(0, str(Path(__file__).parent / "analytics"))

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
    load_all(cleaned)


def run_warehouse():
    log.info("━━━ PHASE 4: BUILD WAREHOUSE ━━━━━━━━━━━━━━━━━━━━━━━━━━")
    from build_warehouse import build_all
    build_all()

    log.info("━━━ PHASE 5: RUN ANALYTICS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    from run_analytics import main as analytics_main
    analytics_main()


def main():
    parser = argparse.ArgumentParser(description="Data Warehouse Pipeline")
    parser.add_argument("--skip-gen", action="store_true", help="Skip data generation")
    parser.add_argument("--only", choices=["gen", "etl", "warehouse"], help="Run one phase only")
    args = parser.parse_args()

    start = time.time()

    log.info("╔══════════════════════════════════════════════════════════╗")
    log.info("║     DATA WAREHOUSE PIPELINE — DAYS 1 & 2               ║")
    log.info("╚══════════════════════════════════════════════════════════╝")

    try:
        if args.only == "gen":
            run_generation()
        elif args.only == "etl":
            run_etl()
        elif args.only == "warehouse":
            run_warehouse()
        elif args.skip_gen:
            run_etl()
            run_warehouse()
        else:
            run_generation()
            run_etl()
            run_warehouse()

        elapsed = time.time() - start
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
