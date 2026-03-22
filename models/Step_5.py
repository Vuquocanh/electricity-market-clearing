"""
Step_5.py
Balancing market clearing for a single hour (hour 19).

Scenario:
- Generator g10 trips (outage) → system short
- Wind w1-w3 produce 10% more than DA forecast
- Wind w4-w6 produce 15% less than DA forecast
- Flexible generators in gen_reg provide upward/downward regulation

Two settlement schemes are computed:
- One-price: all imbalances settled at the balancing price
- Two-price: balancing providers settled at their bid; only counter-direction deviations penalized
"""

import numpy as np
import gurobipy as gp
from gurobipy import GRB
import pandas as pd


def balancing_market(data, step1_results, gen_out=[], wind_up=[], wind_down=[], gen_reg=[], reserve_results=None, t=19):

    # --- Index sets ---
    gens  = data["gen"]
    loads = data["load"]
    winds = data["wind"]

    # --- Bid prices ---
    gen_price  = data["gen_price"]
    wind_price = data["wind_price"]
    load_price = data["load_price"]
    gen_data   = data["gen_data"]

    # --- Day-ahead market results ---
    Pgen_DA      = step1_results["P_gen"]
    Pwind_DA     = step1_results["P_wind"]
    Pload_DA     = step1_results["P_load"]
    price_DA     = step1_results["clearing_price"]
    gen_profit_DA  = step1_results["gen_profit"]
    load_profit_DA = step1_results["load_profit"]
    wind_profit_DA = step1_results["wind_profit"]

    # Regulation prices: DA price ± percentage of marginal cost
    reg_up_price   = {g: price_DA + 0.10 * gen_price[g] for g in gen_reg}
    reg_down_price = {g: price_DA - 0.15 * gen_price[g] for g in gen_reg}
    curt_cost = 500  # load curtailment penalty (€/MWh)

    # Reserved capacity from Step 6 (reduces headroom for regulation)
    if isinstance(reserve_results, dict):
        P_res_up   = reserve_results.get("P_reserve_up",   {})
        P_res_down = reserve_results.get("P_reserve_down", {})
    else:
        P_res_up   = {}
        P_res_down = {}

    # --- Real-time deviations from DA schedule ---
    Pgen_out = {g: Pgen_DA[g] for g in gen_out}
    for g in gen_out:
        Pgen_DA[g] = 0  # outage generator set to zero

    Pwind_act = {w: Pwind_DA[w] for w in winds}
    for w in wind_up:
        Pwind_act[w] += Pwind_DA[w] * 0.10   # +10% wind
    for w in wind_down:
        Pwind_act[w] -= Pwind_DA[w] * 0.15   # -15% wind

    # Total imbalance: positive = system short (need upward regulation)
    Pimbalance = sum(Pgen_out.values()) - sum(Pwind_act[w] - Pwind_DA[w] for w in winds)

    # --- Model ---
    model = gp.Model("Balancing Market, Single Hour")
    model.Params.TimeLimit = 100

    # --- Variables ---
    Pgen_up   = {g: model.addVar(lb=0, ub=GRB.INFINITY, name=f'Pgenup_{g}',   vtype=GRB.CONTINUOUS) for g in gen_reg}
    Pgen_down = {g: model.addVar(lb=0, ub=GRB.INFINITY, name=f'Pgendown_{g}', vtype=GRB.CONTINUOUS) for g in gen_reg}
    Pload_curt = {d: model.addVar(lb=0, ub=GRB.INFINITY, name=f'Ploadcurt_{d}', vtype=GRB.CONTINUOUS) for d in loads}

    # --- Objective: minimize total balancing cost ---
    OF = (gp.quicksum(reg_up_price[g]   * Pgen_up[g]    for g in gen_reg)
          - gp.quicksum(reg_down_price[g] * Pgen_down[g]  for g in gen_reg)
          + gp.quicksum(curt_cost         * Pload_curt[d]  for d in loads))
    model.setObjective(OF, GRB.MINIMIZE)

    # --- Constraints ---

    # Real-time power balance
    power_balance = model.addConstr(
        gp.quicksum(Pgen_DA[g] for g in gens)
        + gp.quicksum(Pgen_up[g] - Pgen_down[g] for g in gen_reg)
        + gp.quicksum(Pwind_act[w] for w in winds)
        == gp.quicksum(Pload_DA[l] for l in loads) - gp.quicksum(Pload_curt[d] for d in loads),
        name='power_balance'
    )

    # Upward regulation limited by remaining capacity (after DA dispatch and reserve)
    gen_up = {
        g: model.addConstr(
            Pgen_up[g] <= gen_data.loc[g, 'pmax'] - Pgen_DA[g] - P_res_up.get(g, 0),
            name=f'gen_up_{g}'
        )
        for g in gen_reg
    }

    # Downward regulation limited by DA dispatch (minus reserved downward capacity)
    gen_down = {
        g: model.addConstr(
            Pgen_down[g] <= Pgen_DA[g] - P_res_down.get(g, 0),
            name=f'gen_down_{g}'
        )
        for g in gen_reg
    }

    load_curt = {
        d: model.addConstr(Pload_curt[d] <= Pload_DA[d], name=f'load_curt_{d}')
        for d in loads
    }

    model.optimize()

    constraints = model.getConstrs()

    # --- Settlement schemes ---
    price_balancing = abs(power_balance.Pi)

    # Final dispatch after regulation
    Pgen_one = {
        g: Pgen_DA[g] + (Pgen_up[g].X if g in gen_reg else 0) - (Pgen_down[g].X if g in gen_reg else 0)
        for g in gens
    }
    Pload_one = {d: Pload_DA[d] - Pload_curt[d].X for d in loads}
    Pwind_one = Pwind_act  # actual wind realization

    # One-price: all settled at balancing price
    Gen_payment_one  = {g: price_balancing * Pgen_up[g].X   for g in gen_reg}
    Gen_charge_one   = {g: price_balancing * Pgen_down[g].X  for g in gen_reg}
    Load_charge_one  = {d: curt_cost * Pload_curt[d].X       for d in loads}
    Wind_balancing_one = {w: price_balancing * (Pwind_act[w] - Pwind_DA[w]) for w in winds}

    # Two-price: providers settled at their bid; deviations hurting system penalized at balancing price
    Gen_payment_two = {g: reg_up_price[g]   * Pgen_up[g].X  for g in gen_reg}
    Gen_charge_two  = {g: reg_down_price[g] * Pgen_down[g].X for g in gen_reg}
    Load_charge_two = Load_charge_one.copy()

    Wind_balancing_two = {}
    for w in winds:
        surplus = Pwind_act[w] - Pwind_DA[w]
        if Pimbalance > 0:  # system short: surplus wind helps → rewarded at DA price
            price = price_DA if surplus > 0 else price_balancing
        else:               # system long: surplus wind hurts → penalized at balancing price
            price = price_balancing if surplus > 0 else price_DA
        Wind_balancing_two[w] = surplus * price

    # --- Total profits (DA + balancing) ---
    Total_gen_profit_one  = sum(gen_profit_DA.values())  + sum(Gen_payment_one.values())  - sum(Gen_charge_one.values())
    Total_gen_profit_two  = sum(gen_profit_DA.values())  + sum(Gen_payment_two.values())  - sum(Gen_charge_two.values())
    Total_wind_profit_one = sum(wind_profit_DA.values()) + sum(Wind_balancing_one.values())
    Total_wind_profit_two = sum(wind_profit_DA.values()) + sum(Wind_balancing_two.values())
    Total_load_profit_one = sum(load_profit_DA.values()) - sum(Load_charge_one.values())
    Total_load_profit_two = sum(load_profit_DA.values()) - sum(Load_charge_two.values())

    # Per-unit profit breakdown
    gen_profit_one_detail = {
        g: gen_profit_DA[g] + (Gen_payment_one[g] - Gen_charge_one[g] if g in gen_reg else 0)
        for g in gens
    }
    gen_profit_two_detail = {
        g: gen_profit_DA[g] + (Gen_payment_two[g] - Gen_charge_two[g] if g in gen_reg else 0)
        for g in gens
    }
    wind_profit_one_detail = {w: wind_profit_DA[w] + Wind_balancing_one[w] for w in winds}
    wind_profit_two_detail = {w: wind_profit_DA[w] + Wind_balancing_two[w] for w in winds}

    # --- Results ---
    results = {}
    if model.Status == GRB.OPTIMAL:
        results["hour"]             = t
        results["obj_val"]          = model.ObjVal
        results["total_oper_cost"]  = (sum(gen_price[g]  * Pgen_one[g]  for g in gens)
                                       + sum(wind_price[w] * Pwind_one[w] for w in winds))
        results["total_load_price"] = sum(load_price[d] * Pload_one[d] for d in loads)
        results["balancing_price"]  = price_balancing
        results["imbalance"]        = Pimbalance
        results["P_gen"]            = {g: Pgen_one[g]   for g in gens}
        results["P_gen_up"]         = {g: Pgen_up[g].X   for g in gen_reg}
        results["P_gen_down"]       = {g: Pgen_down[g].X for g in gen_reg}
        results["P_wind"]           = {w: Pwind_one[w]  for w in winds}
        results["P_load"]           = {l: Pload_one[l]  for l in loads}
        results["P_load_curt"]      = {d: Pload_curt[d].X for d in loads}
        results["duals_constr"]     = [constraints[c].Pi for c in range(len(constraints))]
        results["reg_up_price"]     = reg_up_price
        results["reg_down_price"]   = reg_down_price
        results["gen_profit_one"]   = Total_gen_profit_one
        results["wind_profit_one"]  = Total_wind_profit_one
        results["load_profit_one"]  = Total_load_profit_one
        results["gen_profit_two"]   = Total_gen_profit_two
        results["wind_profit_two"]  = Total_wind_profit_two
        results["load_profit_two"]  = Total_load_profit_two
        results["gen_profit_one_detail"]  = gen_profit_one_detail
        results["gen_profit_two_detail"]  = gen_profit_two_detail
        results["wind_profit_one_detail"] = wind_profit_one_detail
        results["wind_profit_two_detail"] = wind_profit_two_detail
        return results
    else:
        raise RuntimeError("The problem does not have an optimal solution")
