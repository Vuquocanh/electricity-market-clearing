"""
Step_6.py
Reserve market clearing for a single hour (hour 19).

Two market designs:
- EU sequential: reserve market cleared first (minimize reserve cost),
  then DA energy market cleared with reduced capacity for reserve providers.
- US joint: energy and reserve co-optimized in a single problem
  (maximize social welfare minus reserve cost). Reserve prices include
  the opportunity cost of withheld capacity, so US prices > EU prices.
"""

import numpy as np
import gurobipy as gp
from gurobipy import GRB
import pandas as pd


def reserve_market_EU(data, gen_reg=[], t=19):
    """
    EU-style reserve market: standalone minimization of reserve procurement cost.
    Results are passed to Copper_Plate_Single_Hour to enforce capacity constraints.
    """

    loads = data["load"]

    reserve_up_price   = data["reserve_up_price"]
    reserve_down_price = data["reserve_down_price"]
    hourly_load        = data["hourly_load"]
    reserve_power      = data["reserve_power"]

    total_load    = sum(hourly_load[d, t] for d in loads)
    reserve_up    = 0.15 * total_load   # 15% upward reserve requirement
    reserve_down  = 0.10 * total_load   # 10% downward reserve requirement

    model = gp.Model("Reserve Market, EU, Single Hour")
    model.Params.TimeLimit = 100

    Preserve_up   = {g: model.addVar(lb=0, ub=GRB.INFINITY, name=f'Preserve_up_{g}',   vtype=GRB.CONTINUOUS) for g in gen_reg}
    Preserve_down = {g: model.addVar(lb=0, ub=GRB.INFINITY, name=f'Preserve_down_{g}', vtype=GRB.CONTINUOUS) for g in gen_reg}

    # Minimize total reserve procurement cost
    OF = (gp.quicksum(reserve_up_price[g]   * Preserve_up[g]   for g in gen_reg)
          + gp.quicksum(reserve_down_price[g] * Preserve_down[g] for g in gen_reg))
    model.setObjective(OF, GRB.MINIMIZE)

    # Total reserve requirements
    total_reserve_up   = model.addConstr(gp.quicksum(Preserve_up[g]   for g in gen_reg) == reserve_up,   name='total_upward_reserve')
    total_reserve_down = model.addConstr(gp.quicksum(Preserve_down[g] for g in gen_reg) == reserve_down, name='total_downward_reserve')

    # Individual reserve capacity limits
    reserve_up_power   = {g: model.addConstr(Preserve_up[g]   <= reserve_power[g], name=f'upward_reserve_{g}')   for g in gen_reg}
    reserve_down_power = {g: model.addConstr(Preserve_down[g] <= reserve_power[g], name=f'downward_reserve_{g}') for g in gen_reg}

    model.optimize()

    results = {}
    if model.Status == GRB.OPTIMAL:
        results["hour"]               = t
        results["obj_val"]            = model.ObjVal
        results["P_reserve_up"]       = {g: Preserve_up[g].X   for g in gen_reg}
        results["P_reserve_down"]     = {g: Preserve_down[g].X for g in gen_reg}
        # Reserve prices = duals of the reserve requirement constraints
        results["reserve_up_price"]   = abs(total_reserve_up.Pi)
        results["reserve_down_price"] = abs(total_reserve_down.Pi)
        return results
    else:
        raise RuntimeError("The problem does not have an optimal solution")


def reserve_market_US(data, gen_reg=[], t=19):
    """
    US-style joint market: energy dispatch and reserve procurement co-optimized.
    Reserve prices embed the opportunity cost of withheld energy capacity,
    so they are higher than EU sequential prices.
    """

    gens  = data["gen"]
    loads = data["load"]
    winds = data["wind"]
    t     = 19

    gen_price          = data["gen_price"]
    wind_price         = data["wind_price"]
    load_price         = data["load_price"]
    reserve_up_price   = data["reserve_up_price"]
    reserve_down_price = data["reserve_down_price"]
    reserve_power      = data["reserve_power"]

    gen_data    = data["gen_data"]
    hourly_wind = data["hourly_wind"]
    hourly_load = data["hourly_load"]

    total_load   = sum(hourly_load[d, t] for d in loads)
    reserve_up   = 0.15 * total_load
    reserve_down = 0.10 * total_load

    model = gp.Model("Reserve Market, US Joint, Single Hour")
    model.Params.TimeLimit = 100

    # --- Variables ---
    Pgen   = {g: model.addVar(lb=0, ub=GRB.INFINITY, name=f'Pgen_{g}',        vtype=GRB.CONTINUOUS) for g in gens}
    Pload  = {d: model.addVar(lb=0, ub=GRB.INFINITY, name=f'Pload_{d}',       vtype=GRB.CONTINUOUS) for d in loads}
    Pwind  = {w: model.addVar(lb=0, ub=GRB.INFINITY, name=f'Pwind_{w}',       vtype=GRB.CONTINUOUS) for w in winds}
    Preserve_up   = {g: model.addVar(lb=0, ub=GRB.INFINITY, name=f'Preserve_up_{g}',   vtype=GRB.CONTINUOUS) for g in gen_reg}
    Preserve_down = {g: model.addVar(lb=0, ub=GRB.INFINITY, name=f'Preserve_down_{g}', vtype=GRB.CONTINUOUS) for g in gen_reg}

    # --- Objective: maximize (social welfare - reserve cost) jointly ---
    OF = (gp.quicksum(load_price[d]         * Pload[d]         for d in loads)
          - gp.quicksum(gen_price[g]          * Pgen[g]          for g in gens)
          - gp.quicksum(wind_price[w]         * Pwind[w]         for w in winds)
          - gp.quicksum(reserve_up_price[g]   * Preserve_up[g]   for g in gen_reg)
          - gp.quicksum(reserve_down_price[g] * Preserve_down[g] for g in gen_reg))
    model.setObjective(OF, GRB.MAXIMIZE)

    # --- Constraints ---
    power_balance = model.addConstr(
        gp.quicksum(Pgen[g] for g in gens) + gp.quicksum(Pwind[w] for w in winds)
        == gp.quicksum(Pload[d] for d in loads),
        name='power_balance'
    )

    # Non-reserve generators: simple capacity limit
    gen_capacity = {
        g: model.addConstr(Pgen[g] <= gen_data.loc[g, 'pmax'], name=f'gen_capacity_{g}')
        for g in gens if g not in gen_reg
    }

    # Reserve-providing generators: capacity reduced by committed upward reserve
    gen_reg_capacity = {
        g: model.addConstr(Pgen[g] <= gen_data.loc[g, 'pmax'] - Preserve_up[g], name=f'gen_reg_capacity_{g}')
        for g in gen_reg
    }

    # Must-run lower bound from committed downward reserve
    gen_min_reserve = {
        g: model.addConstr(Pgen[g] >= Preserve_down[g], name=f'gen_min_reserve_{g}')
        for g in gen_reg
    }

    wind_capacity = {w: model.addConstr(Pwind[w] <= hourly_wind[w, t], name=f'wind_capacity_{w}') for w in winds}
    load_capacity = {d: model.addConstr(Pload[d] == hourly_load[d, t], name=f'load_capacity_{d}') for d in loads}

    # Reserve requirement constraints
    total_reserve_up   = model.addConstr(gp.quicksum(Preserve_up[g]   for g in gen_reg) == reserve_up,   name='total_upward_reserve')
    total_reserve_down = model.addConstr(gp.quicksum(Preserve_down[g] for g in gen_reg) == reserve_down, name='total_downward_reserve')

    reserve_up_power   = {g: model.addConstr(Preserve_up[g]   <= reserve_power[g], name=f'upward_reserve_{g}')   for g in gen_reg}
    reserve_down_power = {g: model.addConstr(Preserve_down[g] <= reserve_power[g], name=f'downward_reserve_{g}') for g in gen_reg}

    model.optimize()

    results = {}
    if model.Status == GRB.OPTIMAL:
        results["hour"]             = t
        results["obj_val"]          = model.ObjVal
        results["social_welfare"]   = (sum(load_price[d] * Pload[d].X for d in loads)
                                       - sum(gen_price[g]  * Pgen[g].X  for g in gens)
                                       - sum(wind_price[w] * Pwind[w].X for w in winds))
        results["total_oper_cost"]  = (sum(gen_price[g]  * Pgen[g].X  for g in gens)
                                       + sum(wind_price[w] * Pwind[w].X for w in winds))
        results["clearing_price"]   = abs(power_balance.Pi)
        results["P_gen"]            = {g: Pgen[g].X  for g in gens}
        results["P_wind"]           = {w: Pwind[w].X for w in winds}
        results["P_load"]           = {l: Pload[l].X for l in loads}
        results["P_reserve_up"]     = {g: Preserve_up[g].X   for g in gen_reg}
        results["P_reserve_down"]   = {g: Preserve_down[g].X for g in gen_reg}
        # Reserve prices include opportunity cost → higher than EU sequential
        results["reserve_up_price"]   = abs(total_reserve_up.Pi)
        results["reserve_down_price"] = abs(total_reserve_down.Pi)
        results["reserve_cost"]       = sum(
            reserve_up_price[g] * Preserve_up[g].X + reserve_down_price[g] * Preserve_down[g].X
            for g in gen_reg
        )
        return results
    else:
        raise RuntimeError("The problem does not have an optimal solution")
