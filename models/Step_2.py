"""
Step_2.py
Copper-plate market clearing over 24 hours with a Battery Energy Storage System (BESS).
The BESS exploits price differences across hours (arbitrage) by charging at off-peak
hours and discharging during peak hours.
"""

import numpy as np
import gurobipy as gp
from gurobipy import GRB
import pandas as pd


def Copper_Plate_Multiple_Hours(data):

    # --- Index sets ---
    gens  = data["gen"]
    winds = data["wind"]
    loads = data["load"]
    hours = data["hour"]
    bess  = data["bess"]

    # --- Bid prices ---
    gen_price  = data["gen_price"]
    wind_price = data["wind_price"]
    load_price = data["load_price"]

    gen_data    = data["gen_data"]
    hourly_wind = data["hourly_wind"]
    hourly_load = data["hourly_load"]
    bess_data   = data["bess_data"]

    SOC_0 = 0.5  # initial SOC at 50% of capacity

    # --- Model ---
    model = gp.Model("Market Clearing, Copper plate, Multiple Hours")
    model.Params.TimeLimit = 100

    # --- Variables ---
    Pgen  = {(g, t): model.addVar(lb=0, ub=GRB.INFINITY, name=f"Pgen_{g}_{t}",  vtype=GRB.CONTINUOUS) for g in gens  for t in hours}
    Pwind = {(w, t): model.addVar(lb=0, ub=GRB.INFINITY, name=f"Pwind_{w}_{t}", vtype=GRB.CONTINUOUS) for w in winds for t in hours}
    Pload = {(d, t): model.addVar(lb=0, ub=GRB.INFINITY, name=f"Pload_{d}_{t}", vtype=GRB.CONTINUOUS) for d in loads for t in hours}
    Pch   = {(b, t): model.addVar(lb=0, ub=GRB.INFINITY, name=f"Pch_{b}_{t}",   vtype=GRB.CONTINUOUS) for b in bess  for t in hours}
    Pdch  = {(b, t): model.addVar(lb=0, ub=GRB.INFINITY, name=f"Pdch_{b}_{t}",  vtype=GRB.CONTINUOUS) for b in bess  for t in hours}

    # SOC indexed from 0 to 24 (hour 0 = initial state)
    SOC_hours = [0] + hours
    SOC = {(b, t): model.addVar(lb=0, ub=GRB.INFINITY, name=f"SOC_{b}_{t}", vtype=GRB.CONTINUOUS) for b in bess for t in SOC_hours}

    # --- Objective: maximize social welfare ---
    OF = (gp.quicksum(load_price[d] * Pload[d, t] for d in loads for t in hours)
          - gp.quicksum(gen_price[g] * Pgen[g, t]  for g in gens  for t in hours)
          - gp.quicksum(wind_price[w] * Pwind[w, t] for w in winds for t in hours))
    model.setObjective(OF, GRB.MAXIMIZE)

    # --- Constraints ---

    # Power balance including BESS discharge/charge
    power_balance = {
        t: model.addConstr(
            gp.quicksum(Pgen[g, t] for g in gens)
            + gp.quicksum(Pwind[w, t] for w in winds)
            + gp.quicksum(Pdch[b, t] - Pch[b, t] for b in bess)
            == gp.quicksum(Pload[d, t] for d in loads)
        )
        for t in hours
    }

    gen_capacity = {
        (g, t): model.addConstr(Pgen[g, t] <= gen_data.loc[g, "pmax"], name=f'gen_capacity_{g}_{t}')
        for g in gens for t in hours
    }

    wind_capacity = {
        (w, t): model.addConstr(Pwind[w, t] <= hourly_wind[w, t], name=f'wind_capacity_{w}_{t}')
        for w in winds for t in hours
    }

    load_capacity = {
        (d, t): model.addConstr(Pload[d, t] <= hourly_load[d, t], name=f'load_capacity_{d}_{t}')
        for d in loads for t in hours
    }

    # BESS charge/discharge power limits
    bess_charge = {
        (b, t): model.addConstr(Pch[b, t] <= bess_data.loc[b, "pmax"], name=f'bess_charge_{b}_{t}')
        for b in bess for t in hours
    }
    bess_discharge = {
        (b, t): model.addConstr(Pdch[b, t] <= bess_data.loc[b, "pmax"], name=f'bess_discharge_{b}_{t}')
        for b in bess for t in hours
    }

    # Initial and final SOC (circularity ensures sustainable daily operation)
    initial_soc = {b: model.addConstr(SOC[b, 0]  == SOC_0, name=f'initial_soc_{b}') for b in bess}
    final_soc   = {b: model.addConstr(SOC[b, 24] == SOC_0, name=f'final_soc_{b}')   for b in bess}

    # SOC dynamics: charging adds energy (× η_ch), discharging removes energy (÷ η_dis)
    bess_soc = {
        (b, t): model.addConstr(
            SOC[b, t] == SOC[b, t-1]
            + (bess_data.loc[b, "nch"] * Pch[b, t] - Pdch[b, t] / bess_data.loc[b, "ndis"])
            / bess_data.loc[b, "E"],
            name=f'bess_soc_{b}_{t}'
        )
        for b in bess for t in hours
    }

    # SOC bounds
    soc_uplimit   = {(b, t): model.addConstr(SOC[b, t] <= bess_data.loc[b, "socmax"], name=f'soc_uplimit_{b}_{t}')   for b in bess for t in hours}
    soc_downlimit = {(b, t): model.addConstr(SOC[b, t] >= bess_data.loc[b, "socmin"], name=f'soc_downlimit_{b}_{t}') for b in bess for t in hours}

    model.optimize()

    constraints = model.getConstrs()

    # --- Results ---
    results = {}
    if model.Status == GRB.OPTIMAL:
        results["obj_val"]         = model.ObjVal
        results["total_oper_cost"] = (sum(gen_price[g] * Pgen[g, t].X for g in gens for t in hours)
                                      + sum(wind_price[w] * Pwind[w, t].X for w in winds for t in hours))
        results["P_gen"]           = {(g, t): Pgen[g, t].X  for g in gens  for t in hours}
        results["P_wind"]          = {(w, t): Pwind[w, t].X for w in winds for t in hours}
        results["P_load"]          = {(d, t): Pload[d, t].X for d in loads for t in hours}
        results["P_ch"]            = {(b, t): Pch[b, t].X   for b in bess  for t in hours}
        results["P_dch"]           = {(b, t): Pdch[b, t].X  for b in bess  for t in hours}
        results["SOC"]             = {(b, t): SOC[b, t].X   for b in bess  for t in hours}
        results["duals_constr"]    = [constraints[c].Pi for c in range(len(constraints))]

        # MCP = dual of power balance constraint per hour
        results["clearing_price"] = {t: abs(power_balance[t].Pi) for t in hours}

        results["gen_profit"]  = {(g, t): gen_capacity[g, t].Pi  * Pgen[g, t].X  for g in gens  for t in hours}
        results["wind_profit"] = {(w, t): wind_capacity[w, t].Pi * Pwind[w, t].X for w in winds for t in hours}
        results["load_profit"] = {(l, t): load_capacity[l, t].Pi * Pload[l, t].X for l in loads for t in hours}

        # BESS profit = revenue from discharging - cost of charging (at MCP)
        results["BESS_profit"] = {
            (b, t): abs(power_balance[t].Pi) * (Pdch[b, t].X - Pch[b, t].X)
            for b in bess for t in hours
        }
        return results
    else:
        raise RuntimeError("The problem does not have an optimal solution")
