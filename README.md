# 46755 Renewables in Electricity Markets — Assignment 1

Market clearing optimization models for an IEEE 24-bus power system, covering day-ahead, balancing, and reserve markets under various network and storage configurations.

---

## Requirements

- Python 3.9+
- [Gurobi](https://www.gurobi.com/) with a valid license
- Dependencies: `gurobipy`, `pandas`, `numpy`, `matplotlib`

Install dependencies:
```bash
pip install pandas numpy matplotlib
```

---

## Project Structure

```
Assignment/
├── models/
│   ├── Step_1.py        # Copper-plate, single hour
│   ├── Step_2.py        # Copper-plate, 24 hours with BESS
│   ├── Step_3.py        # Network constraints (nodal & zonal)
│   ├── Step_5.py        # Balancing market
│   └── Step_6.py        # Reserve market (EU & US)
├── data_loader.py       # Loads and preprocesses all input data
├── export_results.py    # Saves results to CSV
├── results_config.py    # Defines CSV export structure per step
├── main.py              # Entry point — run individual steps here
├── convert_xlsx_to_csv.py  # One-time conversion of input_data.xlsx → data/
├── plot_figures.ipynb   # Plotting notebook for all figures
├── input_data.xlsx      # Raw input data (generators, loads, wind, network)
└── README.md
```

---

## Getting Started

**Step 1 — Convert input data** (run once):
```bash
python convert_xlsx_to_csv.py
```
This reads `input_data.xlsx` and writes all sheets as CSV files into the `data/` folder.

**Step 2 — Run models:**

Open `main.py` and uncomment the step(s) you want to run at the bottom:
```python
if __name__ == "__main__":
    data = input_data()

    # run_step1(data, t=1)
    # run_step2(data)
    # run_step3(data, t=1)
    run_step5(data, t=19)     # ← currently active
    # run_step6(data, t=19)
```

Then run:
```bash
python main.py
```

Results are saved automatically to `results/Step_X/...` as CSV files.

**Step 3 — Plot figures:**

Open `plot_figures.ipynb` in Jupyter and run the relevant cells. Figures are saved as PDF files alongside the results.

---

## Model Overview

| Step | Model | Hour |
|------|-------|------|
| 1 | Copper-plate market clearing, single hour | t = 1 |
| 2 | 24-hour market with BESS sensitivity analysis | t = 1–24 |
| 3 | Nodal and zonal pricing with DC power flow | t = 1 |
| 5 | Balancing market (g10 outage, wind deviations) | t = 19 |
| 6 | Reserve market — EU sequential and US joint clearing | t = 19 |

Steps 5 and 6 use hour 19 as it represents a peak demand period with limited wind production, creating a meaningful system imbalance for the balancing and reserve market analysis.

---

## Notes

- The `data/` and `results/` folders are not tracked by Git and will be generated locally after running the scripts above.
- Gurobi solver output can be suppressed by adding `model.Params.OutputFlag = 0` in any step file.
- Wind capacity factor data is sourced from [Renewables.ninja](https://www.renewables.ninja/) using locations in Denmark and Sweden, scaled to 200 MW per farm.
