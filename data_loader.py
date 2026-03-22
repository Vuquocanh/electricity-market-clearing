"""
data_loader.py
Loads and preprocesses all input data from CSV files in the data/ folder.
Returns a single dict containing all sets, parameters, and mappings
needed by the optimization models.
"""

import numpy as np
import pandas as pd
from pathlib import Path

# Data folder relative to this file's location
DATA_DIR = Path(__file__).parent / "data"


def input_data():
    """Load all input CSVs and return a preprocessed data dictionary."""

    # --- Load raw CSVs ---
    gen_mapping     = pd.read_csv(DATA_DIR / "gen_map.csv",      index_col="gen_id")
    gen_df          = pd.read_csv(DATA_DIR / "gen_data.csv",     index_col="gen_id")
    load_df         = pd.read_csv(DATA_DIR / "load_data.csv",    index_col="load_id")
    hourly_load_df  = pd.read_csv(DATA_DIR / "hourly_load.csv",  index_col="time_id")
    line_mapping    = pd.read_csv(DATA_DIR / "line_map.csv",     index_col="line_id")
    line_df         = pd.read_csv(DATA_DIR / "line_data.csv",    index_col="line_id")
    wind_mapping    = pd.read_csv(DATA_DIR / "wind_map.csv",     index_col="wind_id")
    wind_df         = pd.read_csv(DATA_DIR / "wind_data.csv",    index_col="wind_id")
    hourly_wind_df  = pd.read_csv(DATA_DIR / "hourly_wind.csv",  index_col="time_id")
    bess_df         = pd.read_csv(DATA_DIR / "bess_data.csv",    index_col="bess_id")
    bess_mapping    = pd.read_csv(DATA_DIR / "bess_map.csv",     index_col="bess_id")
    zone_df         = pd.read_csv(DATA_DIR / "zone_map.csv")

    # Replace NaN with 0 in incidence matrices
    gen_mapping.fillna(0, inplace=True)
    line_mapping.fillna(0, inplace=True)
    wind_mapping.fillna(0, inplace=True)

    # --- Per-unit base values (IEEE 24-bus system) ---
    S_base  = 100   # MVA
    V1_base = 138   # kV (lower voltage level)
    V2_base = 230   # kV (higher voltage level)
    X1_base = V1_base**2 / S_base
    X2_base = V2_base**2 / S_base

    # --- Build data dictionary ---
    data = {}

    # Raw dataframes (kept for direct access in models)
    data["gen_map"]   = gen_mapping
    data["gen_data"]  = gen_df
    data["load_data"] = load_df
    data["line_map"]  = line_mapping
    data["line_data"] = line_df
    data["wind_map"]  = wind_mapping
    data["wind_data"] = wind_df
    data["bess_data"] = bess_df
    data["bess_map"]  = bess_mapping
    data["zone_df"]   = zone_df

    # Index sets
    data["bus"]  = line_mapping.columns.tolist()
    data["gen"]  = gen_mapping.index.tolist()
    data["wind"] = wind_mapping.index.tolist()
    data["bess"] = bess_mapping.index.tolist()
    data["load"] = load_df.index.tolist()
    data["line"] = line_mapping.index.tolist()
    data["hour"] = hourly_load_df.index.tolist()

    # Per-unit base values
    data["base_MVA"] = S_base
    data["base_V1"]  = V1_base
    data["base_V2"]  = V2_base
    data["base_X1"]  = X1_base
    data["base_X2"]  = X2_base

    # --- Bus-to-component mappings (from incidence matrices) ---
    # Each mapping is built by finding the column with value 1 in the relevant row

    gen_bus = {}
    for g in gen_mapping.index:
        row = gen_mapping.loc[g]
        gen_bus[g] = row[row == 1].index[0]
    data["gen_bus"] = gen_bus

    wind_bus = {}
    for w in wind_mapping.index:
        row = wind_mapping.loc[w]
        wind_bus[w] = row[row == 1].index[0]
    data["wind_bus"] = wind_bus

    # Loads are mapped directly by their own ID
    data["load_bus"] = {d: d for d in data["load"]}

    bess_bus = {}
    for b in bess_mapping.index:
        row = bess_mapping.loc[b]
        bess_bus[b] = row[row == 1].index[0]
    data["bess_bus"] = bess_bus

    from_bus = {}
    to_bus   = {}
    for l in line_mapping.index:
        row     = line_mapping.loc[l]
        from_bus[l] = row[row == 1].index[0]   # +1 = sending end
        to_bus[l]   = row[row == -1].index[0]  # -1 = receiving end
    data["line_from"] = from_bus
    data["line_to"]   = to_bus

    # --- Zone mapping ---
    zone_df = zone_df.rename(columns=lambda c: str(c).strip())

    if "bus_id" in zone_df.columns and "zone" in zone_df.columns:
        data["zone_map"] = dict(zip(zone_df["bus_id"].astype(str).str.strip(), zone_df["zone"]))
    elif zone_df.index.name == "bus_id" and "zone" in zone_df.columns:
        data["zone_map"] = dict(zip(zone_df.index.astype(str), zone_df["zone"]))
    else:
        raise ValueError("zone_map.csv must contain columns bus_id and zone (or index bus_id with column zone)")

    # --- Bid prices and cost coefficients ---
    data["gen_price"]          = gen_df['C'].to_dict()      # energy bid price
    data["wind_price"]         = wind_df['C'].to_dict()     # wind bid price (zero)
    data["load_price"]         = load_df['C'].to_dict()     # load utility (willingness to pay)
    data["reg_up_price"]       = gen_df['Cplus'].to_dict()  # upward regulation cost (Step 5)
    data["reg_down_price"]     = gen_df['Cminus'].to_dict() # downward regulation cost (Step 5)
    data["reserve_up_price"]   = gen_df['Cu'].to_dict()     # upward reserve capacity cost (Step 6)
    data["reserve_down_price"] = gen_df['Cd'].to_dict()     # downward reserve capacity cost (Step 6)
    data["reserve_power"]      = gen_df['Rplus'].to_dict()  # max reserve capacity per generator

    # --- Hourly profiles (indexed by (id, time)) ---
    data["hourly_wind"] = {(w, t): hourly_wind_df.loc[t, w] for w in data["wind"] for t in data["hour"]}
    data["hourly_load"] = {(d, t): hourly_load_df.loc[t, d] for d in data["load"] for t in data["hour"]}

    return data
