import argparse
from bt_utils import main

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Download plenary protocols from DIP API.")

    parser.add_argument(
        "--start",
        type=str,
        default="2025-10-01",
        help="Start date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End date (YYYY-MM-DD), optional"
    )

    args = parser.parse_args()


    main(base="https://search.dip.bundestag.de/api/v1",
         api_key="OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw", 
         start_date=args.start,
         end_date=args.end,
         base_dir="../data"
         )