"""
filter_hcahps_to_ny.py

One-time script. Filters HCAHPS-Hospital.csv to NY-only rows so the file
is small enough to commit (~3-4 MB instead of 102 MB).

Run once after downloading the full HCAHPS-Hospital.csv from CMS.
After this runs successfully, you can delete the full file from data/.

Usage (from project root, with .venv activated):
    python scripts/filter_hcahps_to_ny.py

Reads:  data/HCAHPS-Hospital.csv
Writes: data/HCAHPS-Hospital-NY.csv
"""

import os
import sys
import pandas as pd

# Resolve paths from the script location, not from wherever you ran it.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

INPUT_PATH = os.path.join(DATA_DIR, "HCAHPS-Hospital.csv")
OUTPUT_PATH = os.path.join(DATA_DIR, "HCAHPS-Hospital-NY.csv")


def main() -> int:
    if not os.path.exists(INPUT_PATH):
        print(f"ERROR: Input file not found: {INPUT_PATH}")
        print("Download the full HCAHPS-Hospital.csv from")
        print("https://data.cms.gov/provider-data/dataset/dgck-syfz")
        print("and place it in the data/ folder before running this script.")
        return 1

    print(f"Reading {INPUT_PATH}...")
    df = pd.read_csv(INPUT_PATH, dtype={"Facility ID": str}, low_memory=False)

    total_rows = len(df)
    total_facilities = df["Facility ID"].nunique()
    print(f"  Total rows: {total_rows:,}")
    print(f"  Total facilities: {total_facilities:,}")

    ny_df = df[df["State"] == "NY"].copy()
    ny_rows = len(ny_df)
    ny_facilities = ny_df["Facility ID"].nunique()
    print(f"  NY rows: {ny_rows:,}")
    print(f"  NY facilities: {ny_facilities:,}")

    if ny_rows == 0:
        print("ERROR: No NY rows found. Check the 'State' column values.")
        return 1

    print(f"\nWriting {OUTPUT_PATH}...")
    ny_df.to_csv(OUTPUT_PATH, index=False)

    output_size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"  File size: {output_size_mb:.2f} MB")
    print("\nDone. You can now delete data/HCAHPS-Hospital.csv if you want to.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
