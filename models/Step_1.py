"""
Step_1.py
Copper-plate market clearing for a single hour (hour 1).
Optionally accepts committed reserve results from Step 6 (EU)
to enforce capacity constraints in the DA market.
"""

import numpy as np
import gurobipy as gp
from gurobipy import GRB
import pandas as pd


def Copper_Plate_Single_Hour(data, reserve_results=None, t=1):

    # --- Index sets ---
    gens  = data["gen"]
    loads = data["load"]
    winds = data["wind"]

    # --- Bid prices ---
    gen_price  = data["gen_price"]
    wind_price = data["wind_price"]
    load_price = data["load_price"]

    gen_data    = data["gen_data"]
    hourly_wind = data["hourly_wind"]
    hourly_load = data["hourly_load"]

    # Extract committed reserve from Step 6 EU results if provided
    if isinstance(reserve_results, dict):
        P_res_up   = reserve_results.get("P_reserve_up",   {})
        P_res_down = reserve_results.get("P_reserve_down", {})
    else:
        P_res_up   = {}
        P_res_down = {}

    # --- Model ---
    model = gp.Model("Market Clearing, Copper plate, Single Hour")
    model.Params.TimeLimit = 100

    # --- Variables ---
    Pgen  = {g: model.addVar(lb=0, ub=GRB.INFINITY, name=f'Pgen_{g}',  vtype=GRB.CONTINUOUS) for g in gens}
    Pload = {d: model.addVar(lb=0, ub=GRB.INFINITY, name=f'Pload_{d}', vtype=GRB.CONTINUOUS) for d in loads}
    Pwind = {w: model.addVar(lb=0, ub=GRB.INFINITY, name=f'Pwind_{w}', vtype=GRB.CONTINUOUS) for w in winds}

    # --- Objective: maximize social welfare ---
    OF = (gp.quicksum(load_price[d] * Pload[d] for d in loads)
          - gp.quicksum(gen_price[g] * Pgen[g] for g in gens)
          - gp.quicksum(wind_price[w] * Pwind[w] for w in winds))
    model.setObjective(OF, GRB.MAXIMIZE)

    # --- Constraints ---
    power_balance = model.addConstr(
        gp.quicksum(Pgen[g] for g in gens) + gp.quicksum(Pwind[w] for w in winds)
        == gp.quicksum(Pload[d] for d in loads),
        name='power_balance'
    )

    # Upper capacity limit reduced by committed upward reserve
    gen_capacity = {
        g: model.addConstr(
            Pgen[g] <= gen_data.loc[g, 'pmax'] - P_res_up.get(g, 0),
            name=f'gen_capacity_{g}'
        )
        for g in gens
    }

    # Must-run lower bound from committed downward reserve
    gen_min_reserve = {
        g: model.addConstr(
            Pgen[g] >= P_res_down.get(g, 0),
            name=f'gen_min_reserve_{g}'
        )
        for g in gens if P_res_down.get(g, 0) > 0
    }

    wind_capacity = {
        w: model.addConstr(
            Pwind[w] <= hourly_wind[w, t],
            name=f'wind_capacity_{w}'
        )
        for w in winds
    }

    load_capacity = {
        d: model.addConstr(
            Pload[d] == hourly_load[d, t],
            name=f'load_capacity_{d}'
        )
        for d in loads
    }

    model.optimize()

    constraints = model.getConstrs()

    # --- Results ---
    results = {}
    if model.Status == GRB.OPTIMAL:
        mcp = abs(power_balance.Pi)  # market clearing price = dual of power balance

        results["hour"]            = t
        results["obj_val"]         = model.ObjVal
        results["total_oper_cost"] = (sum(gen_price[g] * Pgen[g].X for g in gens)
                                      + sum(wind_price[w] * Pwind[w].X for w in winds))
        results["total_load_price"] = sum(load_price[d] * Pload[d].X for d in loads)
        results["clearing_price"]  = mcp
        results["P_gen"]           = {g: Pgen[g].X for g in gens}
        results["P_wind"]          = {w: Pwind[w].X for w in winds}
        results["P_load"]          = {l: Pload[l].X for l in loads}
        results["duals_constr"]    = [constraints[c].Pi for c in range(len(constraints))]

        # Profit = (MCP - marginal cost) * dispatch
        results["gen_profit"]  = {g: (mcp - gen_price[g]) * Pgen[g].X for g in gens}
        results["wind_profit"] = {w: wind_capacity[w].Pi * Pwind[w].X for w in winds}
        results["load_profit"] = {l: load_capacity[l].Pi * Pload[l].X for l in loads}

        results["dual_gen_capacity"]  = {g: gen_capacity[g].Pi for g in gens}
        results["dual_wind_capacity"] = {w: wind_capacity[w].Pi for w in winds}
        results["dual_load_capacity"] = {l: load_capacity[l].Pi for l in loads}
        return results
    else:
        raise RuntimeError("The problem does not have an optimal solution")
