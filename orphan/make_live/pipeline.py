import logging
from pathlib import Path
from datetime import datetime

LOG_FILE = Path("orphan/make_live/cron_log.txt")

##### Real pipline

# Download BT XML
# Download Whisper 
# Download yt
# Match BT and Whisper
# Topic modelling 


def run_pipeline() -> None:
    # pretend steps
    logging.info("Step 1: start")
    logging.info("Step 2: do nothing, just a toy pipeline")
    logging.info("Step 3: finished at %s", datetime.now())

def main() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(LOG_FILE),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
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
