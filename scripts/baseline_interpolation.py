import argparse
import json
from pathlib import Path

import numpy as np
import xarray as xr

FIELDS = ["t2m", "d2m", "u10", "v10", "msl"]


def main():
    parser = argparse.ArgumentParser(
        description="Interpolate GFS onto BRAMS and evaluate differences"
    )
    
    parser.add_argument("--gfs", type=Path, required=True)
    parser.add_argument("--brams", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument(
        "--method",
        choices=["linear", "nearest"],
        default="linear",
    )
    args = parser.parse_args()

    paths = [args.gfs, args.brams, args.output, args.metrics]
    if len({path.resolve() for path in paths}) != len(paths):
        raise ValueError("Input and output paths must be distinct")

    for path in [args.gfs, args.brams]:
        if not path.is_file():
            raise FileNotFoundError(path)

    for path in [args.output, args.metrics]:
        if path.exists():
            raise FileExistsError(f"Output already exists: {path}")

    with xr.open_dataset(args.gfs) as source:
        gfs = source[FIELDS].load()
    with xr.open_dataset(args.brams) as source:
        brams = source[FIELDS].load()

    if not np.array_equal(gfs.time.values, brams.time.values):
        raise ValueError("Different valid times")
    if brams.sizes["time"] != 1:
        raise ValueError("Expected one paired valid time")

    metadata_keys = [
        "initialization_date",
        "initialization_time",
        "source_end_step",
        "source_step_units_code",
    ]
    for key in metadata_keys:
        if gfs.attrs[key] != brams.attrs[key]:
            raise ValueError(f"Incompatible source metadata: {key}")

    for name in FIELDS:
        if gfs[name].attrs["units"] != brams[name].attrs["units"]:
            raise ValueError(f"{name}: incompatible units")
        if not np.isfinite(gfs[name].values).all():
            raise ValueError(f"{name}: non-finite GFS input")

    interpolated = gfs.interp(
        latitude=brams.latitude,
        longitude=brams.longitude,
        method=args.method,
    )
    interpolated, brams = xr.align(
        interpolated, brams, join="exact"
    )

    weights = np.cos(np.deg2rad(brams.latitude))
    dimensions = ("time", "latitude", "longitude")
    results = {}

    print("Area-weighted differences: interpolated GFS minus BRAMS")

    for name in FIELDS:
        prediction = interpolated[name]
        reference = brams[name]

        if not (
            np.isfinite(prediction.values).all()
            and np.isfinite(reference.values).all()
        ):
            raise ValueError(f"{name}: non-finite values")

        error = prediction - reference
        mae = abs(error).weighted(weights).mean(dimensions).item()
        mse = (error**2).weighted(weights).mean(dimensions).item()
        bias = error.weighted(weights).mean(dimensions).item()
        rmse = float(np.sqrt(mse))
        unit = reference.attrs["units"]

        results[name] = {
            "mae": mae,
            "rmse": rmse,
            "bias": bias,
            "units": unit,
            "n_cells": int(error.size),
        }
        print(
            f"{name}: MAE={mae:.3f}, RMSE={rmse:.3f}, "
            f"bias={bias:.3f}, units={unit}"
        )

    report = {
        "schema_version": 1,
        "method": f"{args.method} interpolation along latitude and longitude",
        "difference": "GFS minus BRAMS",
        "weighting": "cos(latitude)",
        "domain": "full rectangular crop, including ocean",
        "reference_kind": "BRAMS numerical model output",
        "gfs_file": str(args.gfs),
        "brams_file": str(args.brams),
        "valid_time_utc": np.datetime_as_string(
            brams.time.values[0], unit="s"
        ),
        "source_metadata": {
            key: int(gfs.attrs[key]) for key in metadata_keys
        },
        "metrics": results,
    }
    report_text = json.dumps(report, indent=2, allow_nan=False) + "\n"

    interpolated.attrs.pop("grid_spacing_degrees", None)
    interpolated.attrs.update(
        {
            "interpolation_method": f"{args.method} interpolation along latitude and longitude",
            "target_grid_source": args.brams.name,
            "verification_reference": "BRAMS numerical model output",
        }
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    interpolated.to_netcdf(args.output, engine="scipy")
    args.metrics.write_text(report_text, encoding="utf-8")

    print(f"Saved dataset: {args.output}")
    print(f"Saved metrics: {args.metrics}")


if __name__ == "__main__":
    main()