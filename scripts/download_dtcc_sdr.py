"""Download DTCC CFTC Public Price Dissemination cumulative SDR files."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from urllib.request import urlretrieve

ASSET_FILES = {
    "RATES": "CFTC_CUMULATIVE_RATES_{date}.zip",
    "FOREX": "CFTC_CUMULATIVE_FOREX_{date}.zip",
    "COMMODITIES": "CFTC_CUMULATIVE_COMMODITIES_{date}.zip",
    "CREDITS": "CFTC_CUMULATIVE_CREDITS_{date}.zip",
    "EQUITIES": "CFTC_CUMULATIVE_EQUITIES_{date}.zip",
}

BASE_URL = "https://kgc0418-tdw-data-0.s3.amazonaws.com/cftc/eod/"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download DTCC CFTC cumulative SDR files.")
    parser.add_argument("--date", default="2025-02-14", help="Report date in YYYY-MM-DD format.")
    parser.add_argument("--output-dir", default="data/raw_sdr")
    parser.add_argument(
        "--assets",
        nargs="+",
        default=list(ASSET_FILES),
        choices=list(ASSET_FILES),
        help="Asset file groups to download.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report_date = datetime.strptime(args.date, "%Y-%m-%d").strftime("%Y_%m_%d")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for asset in args.assets:
        filename = ASSET_FILES[asset].format(date=report_date)
        url = BASE_URL + filename
        output_path = output_dir / filename
        print(f"Downloading {url}")
        urlretrieve(url, output_path)
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

