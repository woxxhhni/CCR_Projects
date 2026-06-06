"""Build an SA-CCR-ready sample trade file from DTCC public SDR records."""

from __future__ import annotations

import argparse
import hashlib
import math
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

REPORT_DATE = "2025-02-14"
TARGET_ROWS = {
    "RATES": 80,
    "FOREX": 70,
    "COMMODITIES": 70,
    "CREDITS": 50,
    "EQUITIES": 50,
}

ASSET_MAP = {
    "IR": "Interest Rate",
    "FX": "FX",
    "CO": "Commodity",
    "CR": "Credit",
    "EQ": "Equity",
}

COUNTERPARTIES = [
    "CP_BANK_A",
    "CP_BANK_B",
    "CP_ASSET_MANAGER_A",
    "CP_HEDGE_FUND_A",
    "CP_CORPORATE_A",
    "CP_INSURER_A",
    "CP_SOVEREIGN_A",
    "CP_PENSION_A",
]

COUNTERPARTY_REFERENCE = {
    "CP_BANK_A": ("Bank", "A", 0.50),
    "CP_BANK_B": ("Bank", "BBB", 0.50),
    "CP_ASSET_MANAGER_A": ("Financial Institution", "BBB", 0.50),
    "CP_HEDGE_FUND_A": ("Fund", "BB", 1.00),
    "CP_CORPORATE_A": ("Corporate", "BBB", 1.00),
    "CP_INSURER_A": ("Insurance", "A", 0.50),
    "CP_SOVEREIGN_A": ("Sovereign", "AA", 0.20),
    "CP_PENSION_A": ("Pension", "A", 0.50),
}

USD_RATES = {
    "USD": 1.0,
    "EUR": 1.05,
    "GBP": 1.25,
    "AUD": 0.66,
    "NZD": 0.60,
    "CAD": 0.74,
    "CHF": 1.10,
    "JPY": 0.0067,
    "KRW": 0.00073,
    "INR": 0.012,
    "TWD": 0.031,
    "IDR": 0.000064,
    "PHP": 0.017,
    "MYR": 0.21,
    "CNY": 0.14,
    "CNH": 0.14,
    "THB": 0.028,
    "SGD": 0.74,
    "BRL": 0.20,
    "MXN": 0.059,
    "NOK": 0.095,
    "SEK": 0.096,
    "ZAR": 0.053,
    "CLP": 0.0011,
    "COP": 0.00025,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build curated SA-CCR sample from SDR data.")
    parser.add_argument("--raw-dir", default="data/raw_sdr")
    parser.add_argument("--output", default="data/sample_trades.csv")
    parser.add_argument("--counterparties", default="data/counterparty_reference.csv")
    parser.add_argument("--collateral", default="data/collateral.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_dir = Path(args.raw_dir)
    frames = []
    for asset_name, target in TARGET_ROWS.items():
        zpath = next(raw_dir.glob(f"CFTC_CUMULATIVE_{asset_name}_*.zip"))
        selected = select_rows(zpath, target)
        frames.append(selected)

    raw_sample = pd.concat(frames, ignore_index=True)
    saccr = raw_sample.apply(map_sdr_row_to_saccr, axis=1).tolist()
    output = pd.DataFrame(saccr)
    output = output.sort_values(["Asset Class", "Counterparty ID", "Netting Set ID"]).reset_index(drop=True)
    output.to_csv(args.output, index=False)

    write_counterparty_reference(args.counterparties)
    write_collateral(output, args.collateral)

    print(f"Wrote {len(output)} trades to {args.output}")
    print(output["Asset Class"].value_counts().to_string())


def select_rows(zpath: Path, target: int) -> pd.DataFrame:
    collected: list[pd.DataFrame] = []
    with zipfile.ZipFile(zpath) as zf:
        csv_name = zf.namelist()[0]
        with zf.open(csv_name) as handle:
            for chunk in pd.read_csv(handle, chunksize=20_000, low_memory=False):
                filtered = filter_chunk(chunk)
                if not filtered.empty:
                    collected.append(filtered)
                if sum(len(frame) for frame in collected) >= target * 3:
                    break

    if not collected:
        raise ValueError(f"No usable rows found in {zpath}")

    combined = pd.concat(collected, ignore_index=True).drop_duplicates("Dissemination Identifier")
    combined["selection_bucket"] = combined.apply(selection_bucket, axis=1)
    pieces = []
    per_bucket = max(math.ceil(target / max(combined["selection_bucket"].nunique(), 1)), 5)
    for _, bucket_frame in combined.groupby("selection_bucket"):
        pieces.append(bucket_frame.head(per_bucket))
    balanced = pd.concat(pieces, ignore_index=True).drop_duplicates("Dissemination Identifier")
    if len(balanced) < target:
        remaining = combined[
            ~combined["Dissemination Identifier"].isin(balanced["Dissemination Identifier"])
        ]
        balanced = pd.concat([balanced, remaining], ignore_index=True)
    return balanced.head(target)


def filter_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    required = [
        "Dissemination Identifier",
        "Action type",
        "Event type",
        "Asset Class",
        "Effective Date",
        "Expiration Date",
        "Notional amount-Leg 1",
        "Notional currency-Leg 1",
    ]
    missing = [column for column in required if column not in chunk.columns]
    if missing:
        raise ValueError(f"Missing SDR columns: {missing}")

    df = chunk.copy()
    df = df[(df["Action type"] == "NEWT") & (df["Event type"] == "TRAD")]
    df = df[df["Effective Date"].notna() & df["Expiration Date"].notna()]
    df = df[df["Notional amount-Leg 1"].notna() & df["Notional currency-Leg 1"].notna()]

    expiration = pd.to_datetime(df["Expiration Date"], errors="coerce")
    report_date = pd.to_datetime(REPORT_DATE)
    df = df[expiration.notna() & (expiration > report_date) & (expiration.dt.year <= 2075)]
    df = df[df["Notional amount-Leg 1"].map(parse_number) > 0]
    df["Base Notional USD Check"] = df.apply(row_base_notional_usd, axis=1)
    thresholds = {
        "IR": 1_000_000,
        "FX": 100_000,
        "CO": 100_000,
        "CR": 1_000_000,
        "EQ": 10_000,
    }
    df = df[df.apply(lambda row: row["Base Notional USD Check"] >= thresholds[row["Asset Class"]], axis=1)]
    return df


def row_base_notional_usd(row: pd.Series) -> float:
    leg1 = parse_number(row.get("Notional amount-Leg 1"))
    leg2 = parse_number(row.get("Notional amount-Leg 2"))
    ccy1 = text(row.get("Notional currency-Leg 1"))
    ccy2 = text(row.get("Notional currency-Leg 2"))
    return max(convert_to_usd(leg1, ccy1), convert_to_usd(leg2, ccy2), 0.0)


def selection_bucket(row: pd.Series) -> str:
    asset = row["Asset Class"]
    fisn = text(row.get("UPI FISN"))
    product = text(row.get("Product name"))
    underlier = text(row.get("UPI Underlier Name"))
    combined = f"{fisn} {product} {underlier}".upper()
    if asset == "IR":
        if "OIS" in combined:
            return "IR OIS"
        if "FWD" in combined or "FRA" in combined:
            return "IR FRA"
        return "IR Fixed-Float"
    if asset == "FX":
        if "/O " in combined or "OPTION" in combined or " VAN " in combined or " BAR " in combined:
            return "FX Option"
        if "SWAPS" in combined or "NDS" in combined:
            return "FX Swap"
        return "FX Forward/NDF"
    if asset == "CO":
        if "OPTION" in combined:
            return "Commodity Option"
        if "ENERGY" in combined:
            return "Commodity Energy"
        if "METALS" in combined:
            return "Commodity Metals"
        if "AGRICULTURAL" in combined:
            return "Commodity Agricultural"
        return "Commodity Other"
    if asset == "CR":
        if "IDX" in combined or "INDEX" in combined:
            return "Credit Index CDS"
        if "SN" in combined:
            return "Credit Single Name CDS"
        return "Credit Other"
    if asset == "EQ":
        if "INDEX" in combined or "BASKET" in combined:
            return "Equity Index Swap"
        return "Equity Single Stock TRS"
    return asset


def map_sdr_row_to_saccr(row: pd.Series) -> dict[str, object]:
    source_asset = text(row["Asset Class"])
    asset_class = ASSET_MAP[source_asset]
    dissemination_id = text(row["Dissemination Identifier"])
    cp = deterministic_choice(COUNTERPARTIES, dissemination_id)
    netting_set = 1000 + stable_int(f"{cp}-{asset_class}") % 50

    leg1 = parse_number(row.get("Notional amount-Leg 1"))
    leg2 = parse_number(row.get("Notional amount-Leg 2"))
    ccy1 = text(row.get("Notional currency-Leg 1"))
    ccy2 = text(row.get("Notional currency-Leg 2"))
    base_notional = max(convert_to_usd(leg1, ccy1), convert_to_usd(leg2, ccy2), 0.0)
    if base_notional == 0:
        base_notional = leg1

    trade_type = trade_type_from_row(row)
    mtm = synthetic_mtm(base_notional, asset_class, dissemination_id)
    margin_flag, ccp, margin_frequency = margin_fields(row, dissemination_id)

    return {
        "COB Date": REPORT_DATE,
        "Counterparty ID": cp,
        "Netting Set ID": netting_set,
        "Ticket Number": dissemination_id,
        "Trade Type": trade_type,
        "Asset Class": asset_class,
        "Sub Class": subclass_from_row(row),
        "Trade Leg 1 Currency": ccy1,
        "Trade Leg 2 Currency": ccy2,
        "Base Currency": base_currency(asset_class, ccy1, ccy2),
        "Basis/Volatility Indicator": basis_vol_indicator(row),
        "Specific Basis": "",
        "Underlying Entity Name": underlier_name(row, asset_class),
        "Underlying Entity Type": underlying_entity_type(row, asset_class),
        "Underlying Entity Rating": credit_rating(row, asset_class),
        "Maturity Date": date_or_blank(row.get("Expiration Date")),
        "Start Date": date_or_blank(row.get("Effective Date")),
        "End Date": date_or_blank(row.get("Expiration Date")),
        "Leg 1 Notional": leg1,
        "Leg 2 Notional": leg2,
        "Base Notional": round(base_notional, 2),
        "Margined/ Unmargined": margin_flag,
        "CCP": ccp,
        "Margin Frequency (Business Days)": margin_frequency,
        "Buy/Sell Indicator": "B" if stable_int(dissemination_id) % 2 == 0 else "S",
        "Contractual Exercise Date": date_or_blank(row.get("First exercise date")),
        "Put/Call Indicator": put_call(row),
        "Strike Price (Ki)": parse_number(row.get("Strike Price")),
        "Underlying Price (Pi)": parse_number(row.get("Price")),
        "MtM": round(mtm, 2),
        "Source": "DTCC CFTC Public Price Dissemination",
        "Source Dissemination Identifier": dissemination_id,
        "Source Product Name": text(row.get("Product name")),
        "Source UPI FISN": text(row.get("UPI FISN")),
        "Source UPI Underlier Name": text(row.get("UPI Underlier Name")),
    }


def trade_type_from_row(row: pd.Series) -> str:
    asset = row["Asset Class"]
    bucket = selection_bucket(row)
    if asset == "IR":
        return bucket.replace("IR ", "Interest Rate ")
    if asset == "FX":
        return bucket
    if asset == "CO":
        return bucket
    if asset == "CR":
        return bucket
    if asset == "EQ":
        return bucket
    return bucket


def subclass_from_row(row: pd.Series) -> str:
    asset = row["Asset Class"]
    combined = f"{text(row.get('Product name'))} {text(row.get('UPI FISN'))} {text(row.get('UPI Underlier Name'))}".upper()
    if asset == "CO":
        if "NATGAS" in combined or "GAS" in combined:
            return "Gas"
        if "OIL" in combined or "ENERGY" in combined:
            return "Oil"
        if "METALS" in combined or "GOLD" in combined or "COPPER" in combined:
            return "Copper"
        if "AGRICULTURAL" in combined or "GRAINS" in combined or "WHEAT" in combined:
            return "Wheat"
        if "ELECTRIC" in combined:
            return "Electricity"
        return "Other"
    if asset == "EQ":
        return "Single Stock" if "SSTK" in combined or "SINGLE" in combined else "Index"
    return ""


def underlier_name(row: pd.Series, asset_class: str) -> str:
    candidates = [
        text(row.get("UPI Underlier Name")),
        text(row.get("Underlying Asset Name")),
        text(row.get("Underlier ID-Leg 1")),
        text(row.get("Product name")),
        text(row.get("UPI FISN")),
    ]
    for candidate in candidates:
        if candidate and candidate != "No name obtainable":
            return candidate[:120]
    return f"{asset_class}_UNKNOWN"


def underlying_entity_type(row: pd.Series, asset_class: str) -> str:
    combined = f"{text(row.get('UPI FISN'))} {text(row.get('UPI Underlier Name'))} {text(row.get('Product name'))}".upper()
    if asset_class in {"Credit", "Equity"}:
        if "IDX" in combined or "INDEX" in combined or "BASKET" in combined:
            return "Index"
        return "Singleton"
    return ""


def credit_rating(row: pd.Series, asset_class: str) -> str:
    if asset_class != "Credit":
        return ""
    combined = f"{text(row.get('UPI FISN'))} {text(row.get('UPI Underlier Name'))}".upper()
    if "IG" in combined or "AAA" in combined:
        return "IG"
    if "HY" in combined or "CROSSOVER" in combined or "SG" in combined:
        return "SG"
    ratings = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
    return deterministic_choice(ratings, text(row["Dissemination Identifier"]))


def base_currency(asset_class: str, ccy1: str, ccy2: str) -> str:
    if asset_class == "Interest Rate":
        return ccy1
    if asset_class == "FX":
        return "USD" if "USD" in {ccy1, ccy2} else ccy1
    return ccy1 or "USD"


def basis_vol_indicator(row: pd.Series) -> str:
    combined = f"{text(row.get('Product name'))} {text(row.get('UPI FISN'))}".upper()
    if "OPTION" in combined or "/O " in combined:
        return "Volatility"
    if "BASIS" in combined:
        return "Basis"
    return ""


def put_call(row: pd.Series) -> str:
    value = text(row.get("Option Type")).upper()
    if value.startswith("CALL"):
        return "C"
    if value.startswith("PUT"):
        return "P"
    combined = f"{text(row.get('Product name'))} {text(row.get('UPI FISN'))}".upper()
    if "CALL" in combined:
        return "C"
    if "PUT" in combined:
        return "P"
    return ""


def margin_fields(row: pd.Series, key: str) -> tuple[str, str, float | str]:
    cleared = text(row.get("Cleared")).upper()
    if cleared in {"Y", "I"}:
        return "M", "Y", 5.0
    if stable_int(key) % 10 < 7:
        return "M", "N", 10.0
    return "U", "N", ""


def synthetic_mtm(base_notional: float, asset_class: str, key: str) -> float:
    max_pct = {
        "Interest Rate": 0.004,
        "FX": 0.006,
        "Credit": 0.015,
        "Equity": 0.025,
        "Commodity": 0.020,
    }[asset_class]
    centered = (stable_int(f"mtm-{key}") % 2001 - 1000) / 1000.0
    return base_notional * max_pct * centered


def write_counterparty_reference(path: str | Path) -> None:
    rows = [
        {
            "Counterparty ID": cp,
            "Counterparty Type": values[0],
            "Credit Rating": values[1],
            "Risk Weight": values[2],
        }
        for cp, values in COUNTERPARTY_REFERENCE.items()
    ]
    pd.DataFrame(rows).to_csv(path, index=False)


def write_collateral(trades: pd.DataFrame, path: str | Path) -> None:
    rows = []
    for (cp, netting_set), frame in trades.groupby(["Counterparty ID", "Netting Set ID"]):
        notional = frame["Base Notional"].sum()
        collateral_ratio = [0.0, 0.02, 0.05, 0.10, 0.15][stable_int(f"{cp}-{netting_set}") % 5]
        rows.append(
            {
                "Counterparty ID": cp,
                "Netting Set ID": netting_set,
                "Collateral Amount": round(notional * collateral_ratio, 2),
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)


def parse_number(value: object) -> float:
    if value is None or pd.isna(value):
        return 0.0
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    if cleaned in {"", "-", "."}:
        return 0.0
    return float(cleaned)


def convert_to_usd(amount: float, currency: str) -> float:
    if amount == 0:
        return 0.0
    return amount * USD_RATES.get(currency.upper(), 1.0)


def text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def date_or_blank(value: object) -> str:
    if value is None or pd.isna(value) or text(value) == "":
        return ""
    return pd.to_datetime(value).strftime("%Y-%m-%d")


def stable_int(value: str) -> int:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def deterministic_choice(values: Iterable[str], key: str) -> str:
    values = list(values)
    return values[stable_int(key) % len(values)]


if __name__ == "__main__":
    main()
