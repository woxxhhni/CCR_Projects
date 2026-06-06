"""Run the simplified SA-CCR portfolio capital engine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saccr_engine import run_pipeline  # noqa: E402
from saccr_engine.reporting import write_reports  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SA-CCR portfolio capital calculation.")
    parser.add_argument("--trades", default=ROOT / "data" / "sample_trades.csv")
    parser.add_argument("--counterparties", default=ROOT / "data" / "counterparty_reference.csv")
    parser.add_argument("--collateral", default=ROOT / "data" / "collateral.csv")
    parser.add_argument("--output-dir", default=ROOT / "outputs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = run_pipeline(
        trades_path=args.trades,
        counterparty_reference_path=args.counterparties,
        collateral_path=args.collateral,
    )
    write_reports(results, args.output_dir)

    counterparty_summary = results["counterparty_summary"]
    print("SA-CCR run complete")
    print(f"Output directory: {args.output_dir}")
    print("\nCounterparty summary:")
    print(counterparty_summary.to_string(index=False))


if __name__ == "__main__":
    main()

