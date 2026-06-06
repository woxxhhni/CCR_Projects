"""Configuration tables for the simplified SA-CCR engine."""

ALPHA = 1.4
MULTIPLIER_FLOOR = 0.05
BUSINESS_DAYS_PER_YEAR = 250.0
SUPERVISORY_DURATION_RATE = 0.05

MaturityBucket = str

MATURITY_BUCKETS: list[MaturityBucket] = ["<1Y", "1Y-5Y", ">5Y"]

SUPERVISORY_FACTORS = {
    "Interest Rate": 0.005,
    "FX": 0.04,
    "Equity Single Name": 0.32,
    "Equity Index": 0.20,
    "Commodity Electricity": 0.40,
    "Commodity Oil/Gas": 0.18,
    "Commodity Metals": 0.18,
    "Commodity Agricultural": 0.18,
    "Commodity Other": 0.18,
}

CREDIT_SUPERVISORY_FACTORS = {
    "AAA": 0.0038,
    "AA": 0.0038,
    "A": 0.0042,
    "BBB": 0.0054,
    "BB": 0.0106,
    "B": 0.0160,
    "CCC": 0.0600,
    "IG": 0.0038,
    "SG": 0.0106,
}

CORRELATIONS = {
    "Credit Single Name": 0.50,
    "Credit Index": 0.80,
    "Equity Single Name": 0.50,
    "Equity Index": 0.80,
    "Commodity": 0.40,
}

OPTION_SUPERVISORY_VOLATILITY = {
    "Interest Rate": 0.50,
    "FX": 0.15,
    "Credit": 1.00,
    "Equity": 1.20,
    "Commodity": 0.70,
}

COMMODITY_GROUPS = {
    "Oil": "Energy",
    "Gas": "Energy",
    "Crude Oil": "Energy",
    "Electricity": "Energy",
    "Gold": "Metals",
    "Steel": "Metals",
    "Aluminum": "Metals",
    "Copper": "Metals",
    "Wheat": "Agricultural",
}

COMMODITY_FACTOR_KEYS = {
    "Electricity": "Commodity Electricity",
    "Oil": "Commodity Oil/Gas",
    "Gas": "Commodity Oil/Gas",
    "Crude Oil": "Commodity Oil/Gas",
    "Gold": "Commodity Metals",
    "Steel": "Commodity Metals",
    "Aluminum": "Commodity Metals",
    "Copper": "Commodity Metals",
    "Wheat": "Commodity Agricultural",
}

