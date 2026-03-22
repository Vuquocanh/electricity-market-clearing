"""
Step_3.py
Network-constrained market clearing for a single hour (hour 1).

Two models:
- Nodal: DC power flow with per-bus locational marginal prices (LMPs)
- Zonal: aggregated zones with Available Transfer Capacity (ATC) limits

Also includes run_line_sensitivity() for capacity sensitivity analysis.
"""

import numpy as np
import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import math
import copy


def Network_Constraints_Single_Hour_Nodal(data, t=1):

    # --- Index sets ---
    gens  = data["gen"]
    loads = data["load"]
    winds = data["wind"]
    lines = data["line"]
    bus   = data["bus"]
    slack_bus = "b13"   # reference bus (voltage angle = 0)

    # --- Per-unit base values ---
    Sbase = data["base_MVA"]

    # --- Bus mappings ---
    gen_bus   = data["gen_bus"]
    wind_bus  = data["wind_bus"]
    load_bus  = data["load_bus"]
    line_from = data["line_from"]
    line_to   = data["line_to"]

    # --- Bid prices ---
    gen_price  = data["gen_price"]
    wind_price = data["wind_price"]
    load_price = data["load_price"]

    gen_data    = data["gen_data"]
    hourly_wind = data["hourly_wind"]
    hourly_load = data["hourly_load"]
    line_data   = data["line_data"]
    reactance   = line_data["reactance_pu"].to_dict()

    # --- Model ---
    model = gp.Model("Market Clearing, Nodal, Single Hour")
    model.Params.TimeLimit = 100

    # --- Variables (in per-unit) ---
    Pgen_pu  = {g: model.addVar(lb=0,            ub=GRB.INFINITY,  name=f'Pgen_{g}',  vtype=GRB.CONTINUOUS) for g in gens}
    Pload_pu = {d: model.addVar(lb=0,            ub=GRB.INFINITY,  name=f'Pload_{d}', vtype=GRB.CONTINUOUS) for d in loads}
    Pwind_pu = {w: model.addVar(lb=0,            ub=GRB.INFINITY,  name=f'Pwind_{w}', vtype=GRB.CONTINUOUS) for w in winds}
    Pline_pu = {l: model.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f'Pline_{l}', vtype=GRB.CONTINUOUS) for l in lines}
    Phi      = {b: model.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f'Phi_{b}',   vtype=GRB.CONTINUOUS) for b in bus}

    # --- Objective: maximize social welfare (MW values scaled by Sbase) ---
    OF = (gp.quicksum(load_price[d] * Pload_pu[d] * Sbase for d in loads)
          - gp.quicksum(gen_price[g]  * Pgen_pu[g]  * Sbase for g in gens)
          - gp.quicksum(wind_price[w] * Pwind_pu[w] * Sbase for w in winds))
    model.setObjective(OF, GRB.MAXIMIZE)

    # --- Constraints ---

    # Nodal power balance: injection - withdrawal - net line flow = 0 at each bus
    power_balance = {
        b: model.addConstr(
            gp.quicksum(Pgen_pu[g]  for g in gens  if gen_bus[g]  == b)
            + gp.quicksum(Pwind_pu[w] for w in winds if wind_bus[w] == b)
            - gp.quicksum(Pline_pu[l] for l in lines if line_from[l] == b)
            + gp.quicksum(Pline_pu[l] for l in lines if line_to[l]   == b)
            - gp.quicksum(Pload_pu[d] for d in loads if load_bus[d]  == b) == 0,
            name=f'power_balance_{b}'
        )
        for b in bus
    }

    gen_capacity  = {g: model.addConstr(Pgen_pu[g]  <= gen_data.loc[g, 'pmax'] / Sbase,      name=f'gen_capacity_{g}')  for g in gens}
    wind_capacity = {w: model.addConstr(Pwind_pu[w] <= hourly_wind[w, t] / Sbase,             name=f'wind_capacity_{w}') for w in winds}
    load_capacity = {d: model.addConstr(Pload_pu[d] <= hourly_load[d, t] / Sbase,             name=f'load_capacity_{d}') for d in loads}

    # DC power flow: P_line = (1/X) * (angle_from - angle_to)
    dc_flow = {
        l: model.addConstr(
            Pline_pu[l] == (1 / reactance[l]) * (Phi[line_from[l]] - Phi[line_to[l]]),
            name=f'dc_flow_{l}'
        )
        for l in lines
    }

    # Line thermal limits
    line_upperlimit = {l: model.addConstr(Pline_pu[l] <=  line_data.loc[l, "capacity"] / Sbase, name=f'line_limit_upper_{l}') for l in lines}
    line_lowerlimit = {l: model.addConstr(Pline_pu[l] >= -line_data.loc[l, "capacity"] / Sbase, name=f'line_limit_lower_{l}') for l in lines}

    # Voltage angle limits
    angle_upperlimit = {b: model.addConstr(Phi[b] <=  math.pi, name=f'angle_upper_{b}') for b in bus}
    angle_lowerlimit = {b: model.addConstr(Phi[b] >= -math.pi, name=f'angle_lower_{b}') for b in bus}

    # Reference bus: angle fixed to zero
    slack_bus_angle = model.addConstr(Phi[slack_bus] == 0, name='slack_bus_angle')

    model.optimize()

    constraints = model.getConstrs()

    # --- Results ---
    results = {}
    if model.Status == GRB.OPTIMAL:
        results["hour"]             = t
        results["obj_val"]          = model.ObjVal
        results["total_oper_cost"]  = (sum(gen_price[g]  * Pgen_pu[g].X  * Sbase for g in gens)
                                       + sum(wind_price[w] * Pwind_pu[w].X * Sbase for w in winds))
        results["total_load_price"] = sum(load_price[d] * Pload_pu[d].X * Sbase for d in loads)
        results["P_gen"]            = {g: Pgen_pu[g].X  * Sbase for g in gens}
        results["P_wind"]           = {w: Pwind_pu[w].X * Sbase for w in winds}
        results["P_load"]           = {l: Pload_pu[l].X * Sbase for l in loads}
        results["P_line"]           = {l: Pline_pu[l].X * Sbase for l in lines}
        results["Phi"]              = {b: Phi[b].X for b in bus}

        # Line loading = actual flow / capacity
        results["line_loading"]     = {l: Pline_pu[l].X * Sbase / line_data.loc[l, "capacity"] for l in lines}
        results["duals_constr"]     = [constraints[c].Pi for c in range(len(constraints))]

        # LMP = dual of nodal power balance / Sbase
        results["clearing_price"]   = {b: abs(power_balance[b].Pi) / Sbase for b in bus}

        results["gen_profit"]       = {g: gen_capacity[g].Pi  * Pgen_pu[g].X  for g in gens}
        results["wind_profit"]      = {w: wind_capacity[w].Pi * Pwind_pu[w].X for w in winds}
        results["load_profit"]      = {l: load_capacity[l].Pi * Pload_pu[l].X for l in loads}
        results["dual_gen_capacity"]  = {g: gen_capacity[g].Pi  for g in gens}
        results["dual_wind_capacity"] = {w: wind_capacity[w].Pi for w in winds}
        results["dual_load_capacity"] = {l: load_capacity[l].Pi for l in loads}
        return results
    else:
        raise RuntimeError("The problem does not have an optimal solution")


def run_line_sensitivity(data_base, lines_to_change, multipliers):
    """Run nodal model for each capacity multiplier on the specified lines."""
    results = {}
    for m in multipliers:
        data_mod = copy.deepcopy(data_base)
        for l in lines_to_change:
            data_mod["line_data"].loc[l, "capacity"] *= m
        results[m] = Network_Constraints_Single_Hour_Nodal(data_mod)
    return results


def Network_Constraints_Single_Hour_Zonal(data, t=1):

    # --- Index sets ---
    gens  = data["gen"]
    loads = data["load"]
    winds = data["wind"]
    lines = data["line"]

    # --- Bus mappings ---
    gen_bus   = data["gen_bus"]
    wind_bus  = data["wind_bus"]
    load_bus  = data["load_bus"]
    line_from = data["line_from"]
    line_to   = data["line_to"]

    # --- Bid prices ---
    gen_price  = data["gen_price"]
    wind_price = data["wind_price"]
    load_price = data["load_price"]

    gen_data    = data["gen_data"]
    hourly_wind = data["hourly_wind"]
    hourly_load = data["hourly_load"]
    line_data   = data["line_data"]

    # Build zone map (normalize to strings to avoid type mismatches)
    if "zone_map" in data:
        zone_map_raw = {str(k).strip(): v for k, v in data["zone_map"].items()}
    else:
        zone_df = pd.read_csv("data/zone_map.csv")
        zone_df.columns = [c.strip() for c in zone_df.columns]
        if "bus_id" not in zone_df.columns or "zone" not in zone_df.columns:
            raise ValueError("zone_map.csv must have columns: bus_id, zone")
        zone_map_raw = dict(zip(zone_df["bus_id"].astype(str).str.strip(), zone_df["zone"]))

    zone_map = {bus: str(zone).strip() for bus, zone in zone_map_raw.items() if pd.notna(zone)}
    zones    = sorted(set(zone_map.values()))

    # ATC between zones = sum of capacities of tie-lines connecting them
    atc = {}
    for l in lines:
        zf = zone_map[str(line_from[l])]
        zt = zone_map[str(line_to[l])]
        if zf == zt:
            continue  # intra-zonal line, skip
        pair = tuple(sorted((zf, zt), key=str))
        atc[pair] = atc.get(pair, 0.0) + float(line_data.loc[l, "capacity"])

    # --- Model ---
    model = gp.Model("Market Clearing, Zonal, Single Hour")
    model.Params.TimeLimit = 100

    # --- Variables (MW) ---
    Pgen  = {g: model.addVar(lb=0, ub=gen_data.loc[g, "pmax"],  name=f"Pgen_{g}",  vtype=GRB.CONTINUOUS) for g in gens}
    Pload = {d: model.addVar(lb=0, ub=hourly_load[d, t],         name=f"Pload_{d}", vtype=GRB.CONTINUOUS) for d in loads}
    Pwind = {w: model.addVar(lb=0, ub=hourly_wind[w, t],         name=f"Pwind_{w}", vtype=GRB.CONTINUOUS) for w in winds}

    # Inter-zonal exchange: positive = zone A exports to zone B
    F = {
        pair: model.addVar(lb=-cap, ub=cap, name=f"F_{pair[0]}_{pair[1]}", vtype=GRB.CONTINUOUS)
        for pair, cap in atc.items()
    }

    # --- Objective: maximize social welfare ---
    OF = (gp.quicksum(load_price[d] * Pload[d] for d in loads)
          - gp.quicksum(gen_price[g]  * Pgen[g]  for g in gens)
          - gp.quicksum(wind_price[w] * Pwind[w] for w in winds))
    model.setObjective(OF, GRB.MAXIMIZE)

    # --- Zonal power balance ---
    power_balance = {}
    for z in zones:
        gen_z  = gp.quicksum(Pgen[g]  for g in gens  if zone_map[str(gen_bus[g])]  == z)
        wind_z = gp.quicksum(Pwind[w] for w in winds if zone_map[str(wind_bus[w])] == z)
        load_z = gp.quicksum(Pload[d] for d in loads if zone_map[str(load_bus[d])] == z)

        # Net imports: sum flows entering zone z minus flows leaving
        net_import = gp.LinExpr()
        for (za, zb), f in F.items():
            if z == za:
                net_import -= f   # exporting
            elif z == zb:
                net_import += f   # importing

        power_balance[z] = model.addConstr(
            gen_z + wind_z + net_import == load_z,
            name=f"zonal_balance_{z}"
        )

    # ATC constraints (already in variable bounds, kept explicit for dual access)
    atc_upper = {pair: model.addConstr(F[pair] <=  atc[pair], name=f"atc_upper_{pair[0]}_{pair[1]}") for pair in atc}
    atc_lower = {pair: model.addConstr(F[pair] >= -atc[pair], name=f"atc_lower_{pair[0]}_{pair[1]}") for pair in atc}

    model.optimize()

    # --- Results ---
    results = {}
    if model.Status == GRB.OPTIMAL:
        # Zonal price = dual of zonal power balance
        zone_price = {z: abs(power_balance[z].Pi) for z in zones}

        results["hour"]             = t
        results["obj_val"]          = model.ObjVal
        results["total_oper_cost"]  = (sum(gen_price[g]  * Pgen[g].X  for g in gens)
                                       + sum(wind_price[w] * Pwind[w].X for w in winds))
        results["total_load_price"] = sum(load_price[d] * Pload[d].X for d in loads)
        results["P_gen"]            = {g: Pgen[g].X  for g in gens}
        results["P_wind"]           = {w: Pwind[w].X for w in winds}
        results["P_load"]           = {d: Pload[d].X for d in loads}
        results["ATC"]              = atc
        results["F_zone"]           = {pair: F[pair].X for pair in atc}
        results["zone_price"]       = zone_price
        results["clearing_price"]   = zone_price  # alias used by export functions
        results["zone_generation"]  = {z: sum(Pgen[g].X  for g in gens  if zone_map[str(gen_bus[g])]  == z) for z in zones}
        results["zone_load"]        = {z: sum(Pload[d].X for d in loads if zone_map[str(load_bus[d])] == z) for z in zones}

        # Profit uses the price of the zone each entity belongs to
        results["gen_profit"]  = {g: (zone_price[zone_map[str(gen_bus[g])]]  - gen_price[g])  * Pgen[g].X  for g in gens}
        results["wind_profit"] = {w: (zone_price[zone_map[str(wind_bus[w])]] - wind_price[w]) * Pwind[w].X for w in winds}
        results["load_profit"] = {d: (load_price[d] - zone_price[zone_map[str(load_bus[d])]]) * Pload[d].X for d in loads}
        return results
    else:
        raise RuntimeError("The problem does not have an optimal solution")
