"""Run the FLEMMS pipeline from a terminal, without Airflow.

    python pipeline.py                       # all stages
    python pipeline.py --stages staging validate_staging
    python pipeline.py --list                # show stage names

The Airflow DAG (dags/flemms_pipeline.py) calls exactly the same functions.
Exits with code 1 if any stage fails, so failures are never reported as success.
"""
import argparse
import sys
import time

from src.utils.io_utils import new_batch_id
from src.utils.logging_utils import configure_cli_logging, get_logger

log = get_logger("pipeline")


def _stage(module: str, func: str):
    def run(batch_id):
        mod = __import__(module, fromlist=[func])
        return getattr(mod, func)(batch_id)
    return run


# Order matters: each stage reads what the previous ones wrote.
STAGES = {
    "fetch_regions": _stage("src.extract.fetch_psgc", "fetch_regions"),
    "ingest": _stage("src.extract.ingest_survey", "ingest_survey_files"),
    "profile": _stage("src.analysis.profiling", "profile_sources"),
    "staging": _stage("src.transform.staging", "build_staging"),
    "validate_staging": _stage("src.validation.layers", "validate_staging"),
    "curated": _stage("src.transform.curated", "build_curated"),
    "validate_curated": _stage("src.validation.layers", "validate_curated"),
    "load": _stage("src.load.warehouse", "load_warehouse"),
    "benchmark": _stage("src.analysis.format_benchmark", "benchmark_formats"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stages", nargs="+", choices=STAGES, help="run only these stages (in pipeline order)")
    parser.add_argument("--list", action="store_true", help="list stage names and exit")
    args = parser.parse_args()

    if args.list:
        print("\n".join(STAGES))
        return 0

    configure_cli_logging()
    selected = [s for s in STAGES if not args.stages or s in args.stages]
    batch_id = new_batch_id()
    log.info("=== FLEMMS pipeline started | batch %s | stages: %s", batch_id, ", ".join(selected))

    for name in selected:
        started = time.perf_counter()
        log.info("--- %s: start", name)
        try:
            STAGES[name](batch_id)
        except Exception:
            log.exception("--- %s: FAILED after %.1fs. Pipeline stopped.", name, time.perf_counter() - started)
            return 1
        log.info("--- %s: done in %.1fs", name, time.perf_counter() - started)

    log.info("=== FLEMMS pipeline finished successfully | batch %s", batch_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
