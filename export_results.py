import numpy as np
import pandas as pd
from pathlib import Path


def save_results(result_dict, structure_dict, base_path):
    """Save all results in result_dict to CSV files under base_path,
    using the layout defined in structure_dict."""

    base_path = Path(base_path)
    base_path.mkdir(parents=True, exist_ok=True)

    for key, config in structure_dict.items():

        if key not in result_dict:
            continue  # skip keys not present in this step's results

        data = result_dict[key]

        try:
            if config["dim"] == 1:
                if isinstance(data, dict):
                    rows = list(data.items())
                elif isinstance(data, (list, tuple)):
                    rows = list(enumerate(data, start=1))
                else:
                    rows = [(1, data)]
                df = pd.DataFrame(rows, columns=config["columns"])

            elif config["dim"] == 2:
                # Expecting dict with 2-tuple keys: {(id1, id2): value}
                if all(isinstance(k, tuple) and len(k) == 2 for k in data.keys()):
                    df = pd.DataFrame(
                        [(k1, k2, v) for (k1, k2), v in data.items()],
                        columns=config["columns"]
                    )
                else:
                    print(f"DEBUG: key={key}, value type={type(data)}, keys={list(data.keys())[:5]}")
                    raise ValueError("Expected dict with tuple keys for dim=2")

            elif config["dim"] == 0:
                # Scalar value — single-cell CSV
                df = pd.DataFrame([data], columns=[config["filename"].replace(".csv", "")])

            else:
                raise ValueError(f"Unsupported dimension {config['dim']} for key {key}")

            df.to_csv(base_path / config["filename"], index=False)

        except Exception as e:
            print(f"ERROR processing key='{key}': {e}")
            print(f"Value sample: {data if isinstance(data, (int, float, str)) else str(list(data.items())[:5])}")
            raise


def print_results(results: dict, structure: dict):
    """Print all results in a human-readable format."""
    for key, meta in structure.items():
        if key in results:
            print(f"--- {key} ---")
            if meta["dim"] == 1:
                for k, v in results[key].items():
                    print(f"{k}: {v}")
            elif meta["dim"] == 2:
                for (k1, k2), v in results[key].items():
                    print(f"{k1}, {k2}: {v}")
            print("")


def print_clearing_prices(step3_result, data):
    """Print nodal or zonal clearing prices from Step 3 results."""
    if "clearing_price" in step3_result:
        cp = step3_result["clearing_price"]
        if isinstance(cp, dict):
            for bus, price in cp.items():
                print(f"Market clearing price at bus {bus}: ${abs(price):.4f}")
            return
        if isinstance(cp, (list, tuple, np.ndarray)):
            for bus, price in zip(data["bus"], cp):
                print(f"Market clearing price at bus {bus}: ${abs(price):.4f}")
            return

    if "zone_price" in step3_result:
        for zone, price in sorted(step3_result["zone_price"].items(), key=lambda kv: str(kv[0])):
            print(f"Market clearing price at zone {zone}: ${abs(price):.4f}")
        return

    print("No clearing price field found in Step 3 result.")
