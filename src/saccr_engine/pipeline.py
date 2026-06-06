"""End-to-end SA-CCR pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from saccr_engine.addon import calculate_addons
from saccr_engine.data_checks import validate_trades
from saccr_engine.enrichment import enrich_trades
from saccr_engine.exposure import calculate_exposure, calculate_replacement_costs
from saccr_engine.reporting import build_asset_class_summary, build_counterparty_summary


def run_pipeline(
    trades_path: str | Path,
    counterparty_reference_path: str | Path | None = None,
    collateral_path: str | Path | None = None,
) -> dict[str, pd.DataFrame]:
    trades = pd.read_csv(trades_path)
    data_quality_issues = validate_trades(trades)
    enriched = enrich_trades(trades)

    collateral = _read_optional_csv(collateral_path)
    counterparty_reference = _read_optional_csv(counterparty_reference_path)

    asset_class_addon, netting_set_addon, addon_detail = calculate_addons(enriched)
    replacement_costs = calculate_replacement_costs(enriched, collateral)
    netting_set_exposure = calculate_exposure(
        netting_set_addon, replacement_costs, counterparty_reference
    )

    counterparty_summary = build_counterparty_summary(netting_set_exposure)
    asset_class_summary = build_asset_class_summary(asset_class_addon)

    return {
        "data_quality_issues": data_quality_issues,
        "trade_level_enriched": enriched,
        "addon_detail": addon_detail,
        "asset_class_addon": asset_class_addon,
        "netting_set_exposure": netting_set_exposure,
        "counterparty_summary": counterparty_summary,
        "asset_class_summary": asset_class_summary,
    }


def _read_optional_csv(path: str | Path | None) -> pd.DataFrame | None:
    if path is None:
        return None
    csv_path = Path(path)
    if not csv_path.exists():
        return None
    return pd.read_csv(csv_path)

