"""
results_config.py
Defines the export structure for each step's results.
Each entry maps a result key to its CSV filename, column names, and dimensionality:
    dim=0 — scalar value
    dim=1 — dict {id: value}
    dim=2 — dict {(id1, id2): value}
"""

# Step 1 — Copper-plate, single hour
structure_step1 = {
    "obj_val":              {"dim": 0, "filename": "social_welfare.csv"},
    "P_gen":                {"dim": 1, "columns": ["gen", "Pgen"],                  "filename": "pgen_results.csv"},
    "P_wind":               {"dim": 1, "columns": ["wind", "Pwind"],                "filename": "pwind_results.csv"},
    "P_load":               {"dim": 1, "columns": ["load", "Pload"],                "filename": "pload_results.csv"},
    "gen_profit":           {"dim": 1, "columns": ["gen", "profit"],                "filename": "gen_profit.csv"},
    "wind_profit":          {"dim": 1, "columns": ["wind", "profit"],               "filename": "wind_profit.csv"},
    "load_profit":          {"dim": 1, "columns": ["load", "profit"],               "filename": "load_profit.csv"},
    "clearing_price":       {"dim": 1, "columns": ["hour", "clearing_price"],       "filename": "market_price_results.csv"},
    "dual_gen_capacity":    {"dim": 1, "columns": ["gen", "dual_gen_capacity"],     "filename": "dual_gen_capacity.csv"},
    "dual_wind_capacity":   {"dim": 1, "columns": ["wind", "dual_wind_capacity"],   "filename": "dual_wind_capacity.csv"},
    "dual_load_capacity":   {"dim": 1, "columns": ["load", "dual_load_capacity"],   "filename": "dual_load_capacity.csv"},
}

# Step 2 — Copper-plate, 24 hours with BESS
structure_step2 = {
    "obj_val":              {"dim": 0, "filename": "social_welfare.csv"},
    "P_gen":                {"dim": 2, "columns": ["gen", "hour", "Pgen"],          "filename": "pgen_results.csv"},
    "P_wind":               {"dim": 2, "columns": ["wind", "hour", "Pwind"],        "filename": "pwind_results.csv"},
    "P_load":               {"dim": 2, "columns": ["load", "hour", "Pload"],        "filename": "pload_results.csv"},
    "P_ch":                 {"dim": 2, "columns": ["bess", "hour", "Pch"],          "filename": "pcharge_results.csv"},
    "P_dch":                {"dim": 2, "columns": ["bess", "hour", "Pdch"],         "filename": "pdischarge_results.csv"},
    "SOC":                  {"dim": 2, "columns": ["bess", "hour", "SOC"],          "filename": "soc_results.csv"},
    "clearing_price":       {"dim": 1, "columns": ["hour", "clearing_price"],       "filename": "market_price_results.csv"},
    "gen_profit":           {"dim": 2, "columns": ["gen", "hour", "profit"],        "filename": "gen_profit.csv"},
    "wind_profit":          {"dim": 2, "columns": ["wind", "hour", "profit"],       "filename": "wind_profit.csv"},
    "load_profit":          {"dim": 2, "columns": ["load", "hour", "profit"],       "filename": "load_profit.csv"},
    "BESS_profit":          {"dim": 2, "columns": ["bess", "hour", "profit"],       "filename": "BESS_profit.csv"},
    "dual_gen_capacity":    {"dim": 2, "columns": ["gen", "hour", "dual_gen_capacity"],  "filename": "dual_gen_capacity.csv"},
    "dual_wind_capacity":   {"dim": 2, "columns": ["wind", "hour", "dual_wind_capacity"],"filename": "dual_wind_capacity.csv"},
    "dual_load_capacity":   {"dim": 2, "columns": ["load", "hour", "dual_load_capacity"],"filename": "dual_load_capacity.csv"},
}

# Step 3 — Nodal network constraints
structure_step3_nodal = {
    "obj_val":              {"dim": 0, "filename": "social_welfare.csv"},
    "P_gen":                {"dim": 1, "columns": ["gen", "Pgen"],                  "filename": "pgen_results.csv"},
    "P_wind":               {"dim": 1, "columns": ["wind", "Pwind"],                "filename": "pwind_results.csv"},
    "P_load":               {"dim": 1, "columns": ["load", "Pload"],                "filename": "pload_results.csv"},
    "P_line":               {"dim": 1, "columns": ["line", "Pline"],                "filename": "pline_results.csv"},
    "Phi":                  {"dim": 1, "columns": ["bus", "Phi"],                   "filename": "voltage_angle_results.csv"},
    "line_loading":         {"dim": 1, "columns": ["line", "line_loading"],         "filename": "line_loading_results.csv"},
    "clearing_price":       {"dim": 1, "columns": ["bus", "clearing_price"],        "filename": "market_price_results.csv"},
    "gen_profit":           {"dim": 1, "columns": ["gen", "profit"],                "filename": "gen_profit.csv"},
    "wind_profit":          {"dim": 1, "columns": ["wind", "profit"],               "filename": "wind_profit.csv"},
    "load_profit":          {"dim": 1, "columns": ["load", "profit"],               "filename": "load_profit.csv"},
    "dual_gen_capacity":    {"dim": 1, "columns": ["gen", "dual_gen_capacity"],     "filename": "dual_gen_capacity.csv"},
    "dual_wind_capacity":   {"dim": 1, "columns": ["wind", "dual_wind_capacity"],   "filename": "dual_wind_capacity.csv"},
    "dual_load_capacity":   {"dim": 1, "columns": ["load", "dual_load_capacity"],   "filename": "dual_load_capacity.csv"},
    "total_oper_cost":      {"dim": 0, "filename": "total_oper_cost.csv"},
}

# Step 3 — Zonal network constraints
structure_step3_zonal = {
    "obj_val":              {"dim": 0, "filename": "social_welfare.csv"},
    "P_gen":                {"dim": 1, "columns": ["gen", "Pgen"],                  "filename": "pgen_results.csv"},
    "P_wind":               {"dim": 1, "columns": ["wind", "Pwind"],                "filename": "pwind_results.csv"},
    "P_load":               {"dim": 1, "columns": ["load", "Pload"],                "filename": "pload_results.csv"},
    "F_zone":               {"dim": 2, "columns": ["zone_from", "zone_to", "F_zone"], "filename": "fzone_results.csv"},
    "clearing_price":       {"dim": 1, "columns": ["zone", "clearing_price"],       "filename": "market_price_results.csv"},
    "zone_generation":      {"dim": 1, "columns": ["zone", "generation"],           "filename": "zone_generation.csv"},
    "zone_load":            {"dim": 1, "columns": ["zone", "load"],                 "filename": "zone_load.csv"},
    "zone_price":           {"dim": 1, "columns": ["zone", "price"],                "filename": "zone_price.csv"},
    "gen_profit":           {"dim": 1, "columns": ["gen", "profit"],                "filename": "gen_profit.csv"},
    "wind_profit":          {"dim": 1, "columns": ["wind", "profit"],               "filename": "wind_profit.csv"},
    "load_profit":          {"dim": 1, "columns": ["load", "profit"],               "filename": "load_profit.csv"},
    "dual_gen_capacity":    {"dim": 1, "columns": ["gen", "dual_gen_capacity"],     "filename": "dual_gen_capacity.csv"},
    "dual_wind_capacity":   {"dim": 1, "columns": ["wind", "dual_wind_capacity"],   "filename": "dual_wind_capacity.csv"},
    "dual_load_capacity":   {"dim": 1, "columns": ["load", "dual_load_capacity"],   "filename": "dual_load_capacity.csv"},
    "total_oper_cost":      {"dim": 0, "filename": "total_oper_cost.csv"},
}

# Step 5 — Balancing market
structure_step5 = {
    "obj_val":                  {"dim": 0, "filename": "balancing_market_OF.csv"},
    "P_gen":                    {"dim": 1, "columns": ["gen", "Pgen"],              "filename": "pgen_results.csv"},
    "P_wind":                   {"dim": 1, "columns": ["wind", "Pwind"],            "filename": "pwind_results.csv"},
    "P_load":                   {"dim": 1, "columns": ["load", "Pload"],            "filename": "pload_results.csv"},
    "P_gen_up":                 {"dim": 1, "columns": ["gen", "Pgen_up"],           "filename": "pgen_up_results.csv"},
    "P_gen_down":               {"dim": 1, "columns": ["gen", "Pgen_down"],         "filename": "pgen_down_results.csv"},
    "P_load_curt":              {"dim": 1, "columns": ["load", "Pload_curt"],       "filename": "pload_curt_results.csv"},
    "balancing_price":          {"dim": 1, "columns": ["hour", "balancing_price"],  "filename": "balancing_price_results.csv"},
    "gen_profit_one":           {"dim": 0, "filename": "gen_profit_one.csv"},
    "wind_profit_one":          {"dim": 0, "filename": "wind_profit_one.csv"},
    "load_profit_one":          {"dim": 0, "filename": "load_profit_one.csv"},
    "gen_profit_two":           {"dim": 0, "filename": "gen_profit_two.csv"},
    "wind_profit_two":          {"dim": 0, "filename": "wind_profit_two.csv"},
    "load_profit_two":          {"dim": 0, "filename": "load_profit_two.csv"},
    "gen_profit_one_detail":    {"dim": 1, "columns": ["gen", "profit"],            "filename": "gen_profit_one_detail.csv"},
    "gen_profit_two_detail":    {"dim": 1, "columns": ["gen", "profit"],            "filename": "gen_profit_two_detail.csv"},
    "wind_profit_one_detail":   {"dim": 1, "columns": ["wind", "profit"],           "filename": "wind_profit_one_detail.csv"},
    "wind_profit_two_detail":   {"dim": 1, "columns": ["wind", "profit"],           "filename": "wind_profit_two_detail.csv"},
    "imbalance":                {"dim": 0, "filename": "imbalance.csv"},
    "reg_up_price":             {"dim": 1, "columns": ["gen", "reg_up_price"],      "filename": "reg_up_price.csv"},
    "reg_down_price":           {"dim": 1, "columns": ["gen", "reg_down_price"],    "filename": "reg_down_price.csv"},
}

# Step 6 — Reserve market (EU sequential and US joint)
structure_step6 = {
    "obj_val":              {"dim": 0, "filename": "reserve_market_OF.csv"},
    "social_welfare":       {"dim": 0, "filename": "social_welfare.csv"},
    "P_reserve_up":         {"dim": 1, "columns": ["gen", "P_reserve_up"],          "filename": "preserve_up_results.csv"},
    "P_reserve_down":       {"dim": 1, "columns": ["gen", "P_reserve_down"],        "filename": "preserve_down_results.csv"},
    "reserve_up_price":     {"dim": 0, "filename": "reserve_up_price.csv"},
    "reserve_down_price":   {"dim": 0, "filename": "reserve_down_price.csv"},
    "P_gen":                {"dim": 1, "columns": ["gen", "Pgen"],                  "filename": "pgen_results.csv"},
    "P_wind":               {"dim": 1, "columns": ["wind", "Pwind"],                "filename": "pwind_results.csv"},
    "P_load":               {"dim": 1, "columns": ["load", "Pload"],                "filename": "pload_results.csv"},
    "clearing_price":       {"dim": 1, "columns": ["hour", "clearing_price"],       "filename": "market_price_results.csv"},
    "reserve_cost":         {"dim": 0, "filename": "reserve_cost.csv"},
}
