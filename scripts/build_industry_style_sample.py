"""Build a public-safe, anonymized industry-style SA-CCR sample portfolio.

The generated data uses product coverage and field conventions commonly seen
in bank SA-CCR implementation templates, but it does not copy client/project
trade rows. Counterparties, trade ids, dates, notionals, MtM, collateral, and
ratings are deterministic synthetic values designed for a reproducible public
portfolio demo.
"""

from __future__ import annotations

import argparse
import hashlib
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd

COB_DATE = date(2025, 2, 14)

USD_RATES = {
    "USD": 1.0,
    "CNY": 0.14,
    "CNH": 0.14,
    "EUR": 1.05,
    "GBP": 1.25,
    "JPY": 0.0067,
    "AUD": 0.66,
    "CAD": 0.74,
    "CHF": 1.10,
    "XAU": 2_000.0,
}

COUNTERPARTIES = {
    "IND_BANK_001": ("Bank", "A", 0.50),
    "IND_BANK_002": ("Bank", "BBB", 0.50),
    "IND_BROKER_001": ("Broker Dealer", "BBB", 0.50),
    "IND_ASSET_MANAGER_001": ("Asset Manager", "A", 0.50),
    "IND_HEDGE_FUND_001": ("Fund", "BB", 1.00),
    "IND_CORPORATE_001": ("Corporate", "BBB", 1.00),
    "IND_CORPORATE_002": ("Corporate", "BB", 1.00),
    "IND_INSURER_001": ("Insurance", "A", 0.50),
    "IND_SOVEREIGN_001": ("Sovereign", "AA", 0.20),
    "IND_PENSION_001": ("Pension", "A", 0.50),
    "IND_CLEARING_MEMBER_001": ("Clearing Member", "A", 0.50),
    "IND_REGIONAL_BANK_001": ("Bank", "BBB", 0.50),
}

PRODUCT_SPECS = [
    ("FX Forward", "FX", "", 32, 1_000_000, 180_000_000, ["USD/CNY", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]),
    ("FX Swap", "FX", "", 24, 2_000_000, 260_000_000, ["USD/CNY", "EUR/USD", "USD/JPY", "USD/CNH"]),
    ("FX Option", "FX", "", 28, 1_000_000, 150_000_000, ["USD/CNY", "EUR/USD", "GBP/USD", "USD/JPY"]),
    ("Interest Rate Swap", "Interest Rate", "", 34, 10_000_000, 1_800_000_000, ["CNY", "USD", "EUR", "JPY"]),
    ("Cross Currency Swap", "Interest Rate", "", 16, 20_000_000, 900_000_000, ["USD/CNY", "EUR/USD", "USD/JPY"]),
    ("Interest Rate FRA", "Interest Rate", "", 16, 10_000_000, 600_000_000, ["CNY", "USD", "EUR"]),
    ("OIS", "Interest Rate", "", 14, 15_000_000, 1_000_000_000, ["USD", "EUR", "CNY"]),
    ("Swaption", "Interest Rate", "", 10, 10_000_000, 500_000_000, ["CNY", "USD", "EUR"]),
    ("Cap/Floor", "Interest Rate", "", 14, 5_000_000, 450_000_000, ["CNY", "USD", "EUR"]),
    ("Precious Metal Forward", "Commodity", "Gold", 14, 1_000_000, 120_000_000, ["XAU/USD", "XAU/CNY"]),
    ("Precious Metal Swap", "Commodity", "Gold", 10, 1_000_000, 100_000_000, ["XAU/USD", "XAU/CNY"]),
    ("Commodity Option", "Commodity", "Gold", 12, 1_000_000, 90_000_000, ["XAU/USD", "XAU/CNY", "Oil/USD"]),
    ("Oil Forward", "Commodity", "Oil", 10, 1_000_000, 80_000_000, ["Oil/USD"]),
    ("Electricity Swap", "Commodity", "Electricity", 6, 1_000_000, 60_000_000, ["Power/USD"]),
    ("Credit TRS", "Credit", "", 12, 5_000_000, 160_000_000, ["Corporate Bond", "Credit Index"]),
    ("Credit Single Name CDS", "Credit", "", 10, 5_000_000, 130_000_000, ["Corporate Bond"]),
    ("Credit Index CDS", "Credit", "", 12, 10_000_000, 220_000_000, ["Credit Index"]),
    ("Equity TRS", "Equity", "Single Stock", 14, 1_000_000, 70_000_000, ["Single Stock"]),
    ("Equity Index Option", "Equity", "Index", 10, 1_000_000, 90_000_000, ["Equity Index"]),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build anonymized industry-style SA-CCR sample data.")
    parser.add_argument("--trades", default="data/sample_trades.csv")
    parser.add_argument("--counterparties", default="data/counterparty_reference.csv")
    parser.add_argument("--collateral", default="data/collateral.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trades = build_trades()
    collateral = build_collateral(trades)
    counterparties = build_counterparty_reference()

    for path in [args.trades, args.counterparties, args.collateral]:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    trades.to_csv(args.trades, index=False)
    counterparties.to_csv(args.counterparties, index=False)
    collateral.to_csv(args.collateral, index=False)

    print(f"Wrote {len(trades)} trades to {args.trades}")
    print(trades.groupby(["Asset Class", "Trade Type"]).size().to_string())


def build_trades() -> pd.DataFrame:
    rows = []
    trade_index = 1
    cp_ids = list(COUNTERPARTIES)
    for product, asset_class, subclass, count, min_notional, max_notional, underliers in PRODUCT_SPECS:
        for sequence in range(1, count + 1):
            key = f"{product}-{sequence}"
            counterparty = deterministic_choice(cp_ids, key)
            margin_flag = "M" if stable_int(f"margin-{key}") % 10 < 7 else "U"
            ccp_flag = "Y" if asset_class == "Interest Rate" and stable_int(f"ccp-{key}") % 10 < 3 else "N"
            netting_set = 3000 + stable_int(f"{counterparty}-{asset_class}-{margin_flag}") % 400
            underlier = deterministic_choice(underliers, key)
            leg1_ccy, leg2_ccy, base_ccy = currencies_for(asset_class, underlier)
            base_notional = rounded_notional(min_notional, max_notional, key)
            leg1_notional = amount_in_currency(base_notional, leg1_ccy)
            leg2_notional = amount_in_currency(base_notional, leg2_ccy) if leg2_ccy else 0.0
            start_date, maturity_date, exercise_date = dates_for(product, key)
            direction = "B" if stable_int(f"direction-{key}") % 2 == 0 else "S"
            put_call = option_type(product, key)
            strike, underlying_price = option_prices(product, asset_class, underlier, key)
            mtm = mark_to_market(base_notional, asset_class, product, key)
            rating, entity_type = entity_fields(asset_class, product, key)

            rows.append(
                {
                    "COB Date": COB_DATE.isoformat(),
                    "Counterparty ID": counterparty,
                    "Netting Set ID": netting_set,
                    "Ticket Number": f"IND-{trade_index:06d}",
                    "Trade Type": product,
                    "Asset Class": asset_class,
                    "Sub Class": subclass,
                    "Trade Leg 1 Currency": leg1_ccy,
                    "Trade Leg 2 Currency": leg2_ccy,
                    "Base Currency": base_ccy,
                    "Basis/Volatility Indicator": basis_or_volatility(product, key),
                    "Specific Basis": "",
                    "Underlying Entity Name": anonymized_underlying(asset_class, underlier, key),
                    "Underlying Entity Type": entity_type,
                    "Underlying Entity Rating": rating,
                    "Maturity Date": maturity_date.isoformat(),
                    "Start Date": start_date.isoformat(),
                    "End Date": maturity_date.isoformat(),
                    "Leg 1 Notional": round(leg1_notional, 2),
                    "Leg 2 Notional": round(leg2_notional, 2),
                    "Base Notional": round(base_notional, 2),
                    "Margined/ Unmargined": margin_flag,
                    "CCP": ccp_flag,
                    "Margin Frequency (Business Days)": 5.0 if ccp_flag == "Y" else (10.0 if margin_flag == "M" else ""),
                    "Buy/Sell Indicator": direction,
                    "Contractual Exercise Date": exercise_date.isoformat() if exercise_date else "",
                    "Put/Call Indicator": put_call,
                    "Strike Price (Ki)": strike,
                    "Underlying Price (Pi)": underlying_price,
                    "MtM": round(mtm, 2),
                    "Source": "Public-safe anonymized industry-style SA-CCR sample",
                    "Source Dissemination Identifier": f"ANON-{trade_index:06d}",
                    "Source Product Name": product,
                    "Source UPI FISN": "",
                    "Source UPI Underlier Name": underlier,
                }
            )
            trade_index += 1
    return pd.DataFrame(rows)


def build_counterparty_reference() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Counterparty ID": cp,
                "Counterparty Type": values[0],
                "Credit Rating": values[1],
                "Risk Weight": values[2],
            }
            for cp, values in COUNTERPARTIES.items()
        ]
    )


def build_collateral(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (cp, netting_set), frame in trades.groupby(["Counterparty ID", "Netting Set ID"]):
        is_margined = (frame["Margined/ Unmargined"] == "M").any()
        notional = frame["Base Notional"].sum()
        key = f"{cp}-{netting_set}"
        if is_margined:
            collateral_ratio = [0.02, 0.05, 0.10, 0.15][stable_int(key) % 4]
            threshold_ratio = [0.0025, 0.005, 0.01][stable_int(f"threshold-{key}") % 3]
            mta_ratio = 0.001
            nica_ratio = [0.0, 0.01, 0.02][stable_int(f"nica-{key}") % 3]
        else:
            collateral_ratio = threshold_ratio = mta_ratio = nica_ratio = 0.0
        rows.append(
            {
                "Counterparty ID": cp,
                "Netting Set ID": netting_set,
                "Margin Agreement ID": f"CSA-IND-{netting_set}" if is_margined else "",
                "Collateral Amount": round(notional * collateral_ratio, 2),
                "Threshold Amount": round(notional * threshold_ratio, 2),
                "Minimum Transfer Amount": round(notional * mta_ratio, 2),
                "Net Independent Collateral Amount": round(notional * nica_ratio, 2),
            }
        )
    return pd.DataFrame(rows)


def currencies_for(asset_class: str, underlier: str) -> tuple[str, str, str]:
    if "/" in underlier:
        left, right = underlier.split("/", 1)
        return left[:3], right[:3], "USD" if "USD" in {left[:3], right[:3]} else right[:3]
    if asset_class == "Interest Rate":
        ccy = underlier if len(underlier) == 3 else "CNY"
        return ccy, ccy, ccy
    if asset_class in {"Credit", "Equity"}:
        return "USD", "", "USD"
    return "USD", "", "USD"


def amount_in_currency(base_usd: float, ccy: str) -> float:
    rate = USD_RATES.get(ccy, 1.0)
    return base_usd / rate if rate else base_usd


def rounded_notional(min_notional: float, max_notional: float, key: str) -> float:
    u = (stable_int(f"notional-{key}") % 10_000) / 10_000
    skewed = u**1.8
    amount = min_notional + (max_notional - min_notional) * skewed
    rounding = 1_000_000 if amount >= 100_000_000 else 100_000
    return max(round(amount / rounding) * rounding, min_notional)


def dates_for(product: str, key: str) -> tuple[date, date, date | None]:
    start_offset = -(stable_int(f"start-{key}") % 900)
    start = COB_DATE + timedelta(days=start_offset)
    if "FRA" in product:
        tenor_days = 90 + stable_int(f"tenor-{key}") % 270
    elif "Option" in product or product in {"Swaption", "Cap/Floor"}:
        tenor_days = 180 + stable_int(f"tenor-{key}") % 1800
    elif product in {"Interest Rate Swap", "Cross Currency Swap", "OIS"}:
        tenor_days = 365 + stable_int(f"tenor-{key}") % 3650
    else:
        tenor_days = 30 + stable_int(f"tenor-{key}") % 2200
    maturity = COB_DATE + timedelta(days=tenor_days)
    exercise = None
    if "Option" in product or product in {"Swaption", "Cap/Floor"}:
        exercise = COB_DATE + timedelta(days=max(14, int(tenor_days * 0.75)))
    return start, maturity, exercise


def option_type(product: str, key: str) -> str:
    if "Option" not in product and product not in {"Swaption", "Cap/Floor"}:
        return ""
    if product == "Cap/Floor":
        return "C" if stable_int(f"capfloor-{key}") % 2 == 0 else "P"
    return "C" if stable_int(f"option-{key}") % 2 == 0 else "P"


def option_prices(product: str, asset_class: str, underlier: str, key: str) -> tuple[float, float]:
    if "Option" not in product and product not in {"Swaption", "Cap/Floor"}:
        return 0.0, 0.0
    if asset_class == "Interest Rate":
        price = 0.015 + (stable_int(f"px-{key}") % 400) / 10_000
        strike = price * (0.85 + (stable_int(f"k-{key}") % 300) / 1_000)
    elif asset_class == "FX":
        price = 7.1 if "CNY" in underlier else 1.1 + (stable_int(f"px-{key}") % 250) / 1_000
        strike = price * (0.9 + (stable_int(f"k-{key}") % 250) / 1_000)
    elif asset_class == "Commodity":
        price = 2_050.0 if "XAU" in underlier else 78.0
        strike = price * (0.85 + (stable_int(f"k-{key}") % 350) / 1_000)
    else:
        price = 100.0 + stable_int(f"px-{key}") % 40
        strike = price * (0.85 + (stable_int(f"k-{key}") % 350) / 1_000)
    return round(strike, 6), round(price, 6)


def mark_to_market(base_notional: float, asset_class: str, product: str, key: str) -> float:
    max_pct = {
        "Interest Rate": 0.006,
        "FX": 0.010,
        "Credit": 0.020,
        "Equity": 0.030,
        "Commodity": 0.030,
    }[asset_class]
    if "Option" in product or product in {"Swaption", "Cap/Floor"}:
        max_pct *= 1.5
    centered = (stable_int(f"mtm-{key}") % 2001 - 1000) / 1000
    return base_notional * max_pct * centered


def entity_fields(asset_class: str, product: str, key: str) -> tuple[str, str]:
    if asset_class == "Credit":
        rating = deterministic_choice(["AAA", "AA", "A", "BBB", "BB", "B"], key)
        entity_type = "Index" if "Index" in product else "Singleton"
        return rating, entity_type
    if asset_class == "Equity":
        return "", "Index" if "Index" in product else "Singleton"
    return "", ""


def anonymized_underlying(asset_class: str, underlier: str, key: str) -> str:
    if asset_class == "Credit":
        return f"CREDIT_{'INDEX' if 'Index' in underlier else 'NAME'}_{stable_int(key) % 30:02d}"
    if asset_class == "Equity":
        return f"EQUITY_{'INDEX' if 'Index' in underlier else 'NAME'}_{stable_int(key) % 30:02d}"
    return underlier


def basis_or_volatility(product: str, key: str) -> str:
    if product == "Interest Rate Swap" and stable_int(f"basis-{key}") % 12 == 0:
        return "Basis"
    if product == "Equity Index Option" and stable_int(f"vol-{key}") % 20 == 0:
        return "Volatility"
    return ""


def deterministic_choice(values: Iterable[str], key: str) -> str:
    values = list(values)
    return values[stable_int(key) % len(values)]


def stable_int(value: str) -> int:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


if __name__ == "__main__":
    main()
