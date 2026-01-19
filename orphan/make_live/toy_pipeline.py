import logging
from pathlib import Path
from datetime import datetime

THIS_DIR = Path(__file__).resolve().parent
LOG_FILE = THIS_DIR / "cron_log.txt"

def run_pipeline() -> None:
    logging.info("Step 1: start")
    logging.info("Step 2: do nothing, just a toy pipeline")
    logging.info("Step 3: finished at %s", datetime.now())

def main() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(LOG_FILE),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,   # ensures config is applied even if logging was configured elsewhere
    )
    logging.info("Toy pipeline triggered")
    try:
        run_pipeline()
        logging.info("Toy pipeline completed successfully")
    except Exception as exc:
        logging.exception("Toy pipeline failed: %s", exc)
        raise

if __name__ == "__main__":
    main()
