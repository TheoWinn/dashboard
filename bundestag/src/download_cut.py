import argparse
from bt_utils import main

# Run the main function with command-line arguments
# You have to be in the bundestag/src directory to run this script.
# Example usage:
# uv run download_cut.py --start 2023-01-01 --end 2023-12-31
# This will download and cut protocols from Jan 1, 2023 to Dec 31, 2023
# If no end date is provided, it will download up to the current date.

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