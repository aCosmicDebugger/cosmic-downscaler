import argparse
import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import xarray as xr

FIELDS = {
    "t2m": "K",
    "d2m": "K",
    "u10": "m/s",
    "v10": "m/s",
    "msl": "Pa",
}
NAME_PATTERN = re.compile(r"gfs_ne_(\d{10})\.nc")


def grid_id(dataset):
    digest = hashlib.sha256()

    for name in ["latitude", "longitude"]:
        coordinates = np.asarray(dataset[name].values, dtype="<f8")
        digest.update(name.encode("utf-8"))
        digest.update(np.asarray(coordinates.shape, dtype="<i8").tobytes())
        digest.update(coordinates.tobytes())

    return digest.hexdigest()


def describe_file(path, expected_time):
    with xr.open_dataset(path) as dataset:
        if dataset.sizes["time"] != 1:
            raise ValueError(f"{path}: expected one valid time")

        valid_time = np.datetime_as_string(
            dataset.time.values[0], unit="s"
        )
        if datetime.fromisoformat(valid_time).replace(tzinfo=UTC) != expected_time:
            raise ValueError(f"{path}: filename/time mismatch")

        for coordinate in ["latitude", "longitude"]:
            values = dataset[coordinate].values
            if not (
                values.ndim == 1
                and values.size > 1
                and np.isfinite(values).all()
                and np.all(np.diff(values) > 0)
            ):
                raise ValueError(f"{path}: invalid {coordinate}")

        for name, unit in FIELDS.items():
            field = dataset[name]
            if field.dims != ("time", "latitude", "longitude"):
                raise ValueError(f"{path}: unexpected dimensions for {name}")
            if field.attrs["units"] != unit:
                raise ValueError(f"{path}: unexpected units for {name}")
            if not np.isfinite(field.values).all():
                raise ValueError(f"{path}: non-finite values in {name}")

        date = int(dataset.attrs["initialization_date"])
        hour = int(dataset.attrs["initialization_time"])
        initialization = datetime.strptime(
            f"{date:08d}{hour:04d}", "%Y%m%d%H%M"
            ).replace(tzinfo=UTC)

        if int(dataset.attrs["source_step_units_code"]) != 1:
            raise ValueError(f"{path}: expected lead expressed in hours")

        lead = int(dataset.attrs["source_end_step"])
        if initialization + timedelta(hours=lead) != expected_time:
            raise ValueError(f"{path}: inconsistent initialization/lead")

        return {
            "path": str(path),
            "source": dataset.attrs["source"],
            "source_file": dataset.attrs["source_file"],
            "initialization_time_utc": initialization.isoformat(),
            "lead_hours": lead,
            "grid_id": grid_id(dataset),
            "grid_shape": [
                dataset.sizes["latitude"],
                dataset.sizes["longitude"],
            ],
            "bounds": {
                "south": float(dataset.latitude.values[0]),
                "north": float(dataset.latitude.values[-1]),
                "west": float(dataset.longitude.values[0]),
                "east": float(dataset.longitude.values[-1]),
            },
        }


def main():
    parser = argparse.ArgumentParser(
        description="Build a validated manifest of regional GFS/BRAMS pairs"
    )
    parser.add_argument(
        "--gfs-dir", type=Path, default=Path("data/interim/gfs")
    )
    parser.add_argument(
        "--brams-dir", type=Path, default=Path("data/interim/brams")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/manifests/paired_samples.json"),
    )
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError(args.output)

    pairs = []
    reference_grids = {}

    for gfs_path in sorted(args.gfs_dir.glob("gfs_ne_*.nc")):
        match = NAME_PATTERN.fullmatch(gfs_path.name)
        if match is None:
            continue

        stamp = match.group(1)
        expected_time = datetime.strptime(
            stamp, "%Y%m%d%H"
            ).replace(tzinfo=UTC)
        brams_path = args.brams_dir / f"brams_ne_{stamp}.nc"
        if not brams_path.is_file():
            raise FileNotFoundError(f"Missing paired reference: {brams_path}")

        gfs = describe_file(gfs_path, expected_time)
        brams = describe_file(brams_path, expected_time)

        for key in ["initialization_time_utc", "lead_hours"]:
            if gfs[key] != brams[key]:
                raise ValueError(f"{stamp}: incompatible {key}")

        for model, description in [("gfs", gfs), ("brams", brams)]:
            previous = reference_grids.setdefault(
                model, description["grid_id"]
            )
            if description["grid_id"] != previous:
                raise ValueError(f"{stamp}: changing {model} grid")

        pairs.append(
            {
                "sample_id": stamp,
                "valid_time_utc": expected_time.isoformat(),
                "gfs": gfs,
                "brams": brams,
            }
        )
        print(
            f"{stamp}: valid pair, lead +{gfs['lead_hours']} h, "
            f"GFS {gfs['grid_shape']}, BRAMS {brams['grid_shape']}"
        )

    if not pairs:
        raise ValueError("No canonical paired samples found")

    manifest = {
        "schema_version": 1,
        "channels": FIELDS,
        "pairing_policy": "same initialization, lead and valid time",
        "grid_id_definition": "SHA256 of named float64 coordinate arrays",
        "availability": "publication timestamps not yet recorded",
        "n_pairs": len(pairs),
        "samples": pairs,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"Saved {len(pairs)} pairs: {args.output}")


if __name__ == "__main__":
    main()