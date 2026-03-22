import numpy as np
import gurobipy as gp
from gurobipy import GRB
import pandas as pd
from pathlib import Path

from data_loader import input_data
from models.Step_1 import Copper_Plate_Single_Hour
from models.Step_2 import Copper_Plate_Multiple_Hours
from models.Step_3 import Network_Constraints_Single_Hour_Nodal, Network_Constraints_Single_Hour_Zonal, run_line_sensitivity
from models.Step_5 import balancing_market
from models.Step_6 import reserve_market_EU, reserve_market_US
from export_results import save_results, print_results, print_clearing_prices
from results_config import (structure_step1, structure_step2, structure_step3_zonal,
                             structure_step3_nodal, structure_step5, structure_step6)

# Base directory — all result paths are relative to this file's location
BASE_DIR   = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"

# Shared scenario parameters used across multiple steps
GEN_SERVICE   = ['g1', 'g2', 'g3', 'g4', 'g7', 'g11']
GEN_OUTAGE    = ['g10']
WIND_INCREASE = ['w1', 'w2', 'w3']
WIND_DECREASE = ['w4', 'w5', 'w6']


# =============================================================================
# STEP 1 — Copper-plate market clearing, single hour (hour 19)
# =============================================================================
def run_step1(data, t = 1):
    print("======= Step 1 =======")
    result = Copper_Plate_Single_Hour(data, reserve_results=None, t=t)

    print(f"Market clearing price: €{result['clearing_price']}")
    print(f"Total operating cost:  €{result['total_oper_cost']}")
    print(f"Social welfare:        €{result['obj_val']}")

    save_results(result, structure_step1, RESULTS_DIR / f"Step_1/t{t}")
    return result


# =============================================================================
# STEP 2 — Copper-plate, 24 hours with BESS sensitivity analysis
# =============================================================================
def run_step2(data):
    print("\n======= Step 2 =======")

    bess_scenarios = [
        {"name": "no_BESS",      "pmax": 0,     "E": 10e-6},   # baseline: no storage
        {"name": "1000_2000",    "pmax": 1000,  "E": 2000},
        {"name": "3000_6000",    "pmax": 3000,  "E": 6000},     # optimal scenario
        {"name": "30000_60000",  "pmax": 30000, "E": 60000},
    ]

    for scenario in bess_scenarios:
        # Copy data to avoid mutating the original
        data_scenario = data.copy()
        data_scenario["bess_data"] = data_scenario["bess_data"].copy()
        data_scenario["bess_data"]["pmax"] = scenario["pmax"]
        data_scenario["bess_data"]["E"]    = scenario["E"]

        print(f"\nRunning Step 2 — BESS scenario: {scenario['name']}")
        result = Copper_Plate_Multiple_Hours(data_scenario)

        print(f"Total operating cost: €{result['total_oper_cost']}")
        print(f"Social welfare:       €{result['obj_val']}")
        print(f"Total BESS profit:    €{sum(result['BESS_profit'].values())}")

        save_results(result, structure_step2, RESULTS_DIR / f"Step_2/With_BESS_{scenario['name']}")


# =============================================================================
# STEP 3 — Network constraints: nodal and zonal pricing (hour 1)
# =============================================================================
def run_step3(data, t = 1):

    def export_sensitivity_results(results_dict, output_dir, scenario_name, structure_dict):
        """Export sensitivity results for each line capacity multiplier."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for multiplier, res in results_dict.items():
            scenario_dir = output_dir / f"{scenario_name}_x{multiplier:.2f}"
            scenario_dir.mkdir(parents=True, exist_ok=True)
            save_results(res, structure_dict, scenario_dir)
            max_loading = max(abs(v) for v in res.get("line_loading", {}).values()) if "line_loading" in res else 0
            print(f"{scenario_name} x{multiplier:.2f} | cost={res.get('total_oper_cost', 0):.2f} | "
                  f"welfare={res.get('obj_val', 0):.2f} | max|loading|={max_loading:.4f}")

    # --- Nodal ---
    print("\n======= Step 3 (Nodal) =======")
    result_nodal = Network_Constraints_Single_Hour_Nodal(data, t=t)

    print_clearing_prices(result_nodal, data)
    print(f"Total operating cost: €{result_nodal['total_oper_cost']:.2f}")
    print(f"Social welfare:       €{result_nodal['obj_val']:.2f}")

    save_results(result_nodal, structure_step3_nodal, RESULTS_DIR / f"Step_3/Nodal/t{t}")

    # Sensitivity on the most congested line
    sorted_lines = sorted(result_nodal["line_loading"].items(), key=lambda kv: abs(kv[1]), reverse=True)
    top1 = sorted_lines[0][0]

    multipliers = [0.8, 1.0, 1.2]
    one_line_results = run_line_sensitivity(data, [top1], multipliers)

    output_dir_sensitivity = RESULTS_DIR / f"Step_3/Nodal/t{t}/Sensitivity"
    export_sensitivity_results(one_line_results, output_dir_sensitivity, f"line_{top1}", structure_step3_nodal)
    
    # --- Zonal ---
    print("\n======= Step 3 (Zonal) =======")
    result_zonal = Network_Constraints_Single_Hour_Zonal(data, t = t)

    print_clearing_prices(result_zonal, data)
    print(f"Total operating cost: €{result_zonal['total_oper_cost']:.2f}")
    print(f"Social welfare:       €{result_zonal['obj_val']:.2f}")

    save_results(result_zonal, structure_step3_zonal, RESULTS_DIR / f"Step_3/Zonal/t{t}")


# =============================================================================
# STEP 5 — Balancing market (hour 19)
# Scenario: g10 outage, w1-w3 +10%, w4-w6 -15%
# =============================================================================
def run_step5(data, t = 19):
    print("\n======= Step 5 =======")

    # Run DA market first to get day-ahead dispatch
    step1_result = Copper_Plate_Single_Hour(data, t=t) # override for step 5
    save_results(step1_result, structure_step1, RESULTS_DIR / f"Step_1/t{t}")

    result = balancing_market(
        data, step1_result,
        gen_out=GEN_OUTAGE, wind_up=WIND_INCREASE, wind_down=WIND_DECREASE,
        gen_reg=GEN_SERVICE, reserve_results=None, t = 19
    )

    print(f"Balancing price:          €{result['balancing_price']}")
    print(f"Total operating cost:     €{result['total_oper_cost']}")
    print(f"Objective function value: €{result['obj_val']}")

    save_results(result, structure_step5, RESULTS_DIR / f"Step_5/t{t}")

    # Print wind profit breakdown: DA vs total after balancing
    for w in data["wind"]:
        da  = step1_result["wind_profit"][w]
        bal = result["wind_profit_one_detail"][w]
        print(f"{w}: DA={da:.2f}, total_one={bal:.2f}, diff={bal-da:.2f}")


# =============================================================================
# STEP 6 — Reserve market: EU sequential and US joint clearing (hour 19)
# =============================================================================
def run_step6(data, t = 19):

    # --- EU sequential: reserve market cleared first, then DA ---
    print("\n======= Step 6 — EU Sequential =======")
    step6_result_EU = reserve_market_EU(data, gen_reg=GEN_SERVICE, t=t)
    

    # Re-run DA with reserve capacity constraints applied
    step1_result = Copper_Plate_Single_Hour(data, reserve_results=step6_result_EU, t = t)
    print(f"Clearing price:         €{step1_result['clearing_price']}")
    print(f"Total oper. cost:       €{step1_result['total_oper_cost']}")
    print(f"SW (DA - reserve cost): €{step1_result['obj_val'] - step6_result_EU['obj_val']:.2f}")

    save_results(step1_result,    structure_step1, RESULTS_DIR / f"Step_6/EU/t{t}")
    save_results(step6_result_EU, structure_step6, RESULTS_DIR / f"Step_6/EU/t{t}")

    # --- US joint: energy and reserve co-optimized in a single problem ---
    print("\n======= Step 6 — US Joint =======")
    step6_result_US = reserve_market_US(data, gen_reg=GEN_SERVICE, t=t)

    print(f"Market clearing price: €{step6_result_US['clearing_price']}")
    print(f"Reserve up price:      €{step6_result_US['reserve_up_price']:.4f}")
    print(f"Reserve down price:    €{step6_result_US['reserve_down_price']:.4f}")
    print(f"Total oper. cost:      €{step6_result_US['total_oper_cost']}")

    # Compute DA-equivalent profits for use in downstream calculations
    cp = step6_result_US["clearing_price"]
    step6_result_US["gen_profit"]  = {g: (cp - data["gen_price"][g])  * step6_result_US["P_gen"][g]  for g in data["gen"]}
    step6_result_US["wind_profit"] = {w: (cp - data["wind_price"][w]) * step6_result_US["P_wind"][w] for w in data["wind"]}
    step6_result_US["load_profit"] = {d: (data["load_price"][d] - cp) * step6_result_US["P_load"][d] for d in data["load"]}

    save_results(step6_result_US, structure_step6, RESULTS_DIR / f"Step_6/US/t{t}")


# =============================================================================
# Entry point — toggle which steps to run
# =============================================================================
if __name__ == "__main__":
    data = input_data()

    run_step1(data, t = 1)
    run_step2(data)
    run_step3(data, t = 1)
    run_step5(data, t = 19)
    run_step6(data, t = 19)
