"""
convert_xlsx_to_csv.py
Converts each sheet in input_data.xlsx to a separate CSV file in the data/ folder.
Run this once before running main.py if the CSV files are not yet generated.
"""

import pandas as pd
from pathlib import Path

# Paths relative to this file's location
BASE_DIR   = Path(__file__).parent
excel_file = BASE_DIR / "input_data.xlsx"
output_dir = BASE_DIR / "data"

output_dir.mkdir(exist_ok=True)

xls = pd.ExcelFile(excel_file)

for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet, index_col=0)
    csv_path = output_dir / f"{sheet}.csv"
    df.to_csv(csv_path)
    print(f"Saved: {csv_path}")
