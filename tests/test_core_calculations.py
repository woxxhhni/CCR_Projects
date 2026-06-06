from pathlib import Path

import pandas as pd
import pytest

from saccr_engine.enrichment import assign_supervisory_factor, normal_cdf
from saccr_engine.exposure import pfe_multiplier, replacement_cost
from saccr_engine.pipeline import run_pipeline


ROOT = Path(__file__).resolve().parents[1]


def test_replacement_cost_is_floored_at_zero():
    assert replacement_cost(value=-10.0, collateral=0.0) == 0.0
    assert replacement_cost(value=100.0, collateral=25.0) == 75.0


def test_margined_replacement_cost_uses_threshold_mta_and_nica():
    assert (
        replacement_cost(
            value=10.0,
            collateral=20.0,
            margin_flag="M",
            threshold=7.0,
            minimum_transfer_amount=2.0,
            nica=3.0,
        )
        == 6.0
    )
    assert (
        replacement_cost(
            value=50.0,
            collateral=20.0,
            margin_flag="M",
            threshold=7.0,
            minimum_transfer_amount=2.0,
            nica=3.0,
        )
        == 30.0
    )


def test_pfe_multiplier_is_between_floor_and_one():
    multiplier = pfe_multiplier(value=-50.0, collateral=0.0, addon_aggregate=100.0)
    assert 0.05 <= multiplier <= 1.0
    assert pfe_multiplier(value=50.0, collateral=0.0, addon_aggregate=100.0) == 1.0


def test_normal_cdf_midpoint():
    assert normal_cdf(0.0) == pytest.approx(0.5)


def test_basis_transaction_reduces_supervisory_factor():
    row = pd.Series({"Asset Class": "FX", "Basis/Volatility Indicator": "Basis"})
    assert assign_supervisory_factor(row) == pytest.approx(0.02)


def test_pipeline_runs_on_sample_data():
    results = run_pipeline(
        trades_path=ROOT / "data" / "sample_trades.csv",
        counterparty_reference_path=ROOT / "data" / "counterparty_reference.csv",
        collateral_path=ROOT / "data" / "collateral.csv",
    )
    assert not results["trade_level_enriched"].empty
    assert not results["netting_set_exposure"].empty
    assert {"PFE", "RC", "EAD", "RWA", "Unmargined EAD Cap", "EAD Cap Applied"}.issubset(
        results["netting_set_exposure"].columns
    )
    assert not results["unmargined_cap_exposure"].empty
