import argparse
from pathlib import Path

import numpy as np
import xarray as xr
from eccodes import (
    codes_get,
    codes_get_array,
    codes_grib_new_from_file,
    codes_release,
)

from cosmic_downscaler.preprocessing.grid import build_regional_field

INPUT = Path("data/raw/brams/BRAMS_ams_08km_2026010100_2026010106.grib2")
OUTPUT = Path("data/interim/brams/brams_ne_2026010106.nc")
FIELDS = {
    ("2t", "heightAboveGround", 2): ("t2m", "K"),
    ("2d", "heightAboveGround", 2): ("d2m", "K"),
    ("10u", "heightAboveGround", 10): ("u10", "m s**-1"),
    ("10v", "heightAboveGround", 10): ("v10", "m s**-1"),
    ("prmsl", "meanSea", 0): ("msl", "Pa"),
}

def extract_field(message):
    if codes_get(message, "gridType") != "regular_ll":
        raise ValueError("Expected a regular latitude-longitude grid")

    bitmap = None
    if codes_get(message, "bitmapPresent"):
        bitmap = codes_get_array(message, "bitmap")

    return build_regional_field(
        codes_get_array(message, "latitudes"),
        codes_get_array(message, "longitudes"),
        codes_get_array(message, "values"),
        bitmap=bitmap,
    )


def main():
    fields = {}
    reference_time = None

    parser = argparse.ArgumentParser(
    description="Extract regional surface fields from a GRIB file"
    )
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output

    if input_path.resolve() == output_path.resolve():
        raise ValueError("Input and output paths must be different")
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    if output_path.exists():
        raise FileExistsError(
            f"Output already exists: {output_path}. Choose another path."
        )

    with input_path.open("rb") as stream:
        while True:
            message = codes_grib_new_from_file(stream)
            if message is None:
                break

            try:
                key = (
                    codes_get(message, "shortName"),
                    codes_get(message, "typeOfLevel"),
                    codes_get(message, "level"),
                )
                if key not in FIELDS:
                    continue
                if codes_get(message, "stepType") != "instant":
                    continue

                name, expected_units = FIELDS[key]
                if name in fields:
                    raise ValueError(f"Duplicate field: {name}")

                units = codes_get(message, "units")
                if units != expected_units:
                    raise ValueError(f"{name}: unexpected units {units!r}")

                times = (
                    codes_get(message, "dataDate"),
                    codes_get(message, "dataTime"),
                    codes_get(message, "validityDate"),
                    codes_get(message, "validityTime"),
                    codes_get(message, "endStep"),
                    codes_get(message, "stepUnits"),
                )
                if reference_time is None:
                    reference_time = times
                elif times != reference_time:
                    raise ValueError(f"{name}: inconsistent source times")

                field = extract_field(message)
                if not field.size:
                    raise ValueError("Empty regional crop")

                field.attrs = {
                    "units": "m/s" if name in {"u10", "v10"} else units,
                    "long_name": codes_get(message, "name"),
                    "grib_short_name": key[0],
                }
                fields[name] = field
            finally:
                codes_release(message)

    missing = {name for name, _ in FIELDS.values()} - fields.keys()
    if missing:
        raise ValueError(f"Missing fields: {sorted(missing)}")

    aligned = xr.align(*fields.values(), join="exact")
    dataset = xr.Dataset(dict(zip(fields, aligned, strict=True)))

    date, hour, valid_date, valid_hour, step, step_units = reference_time
    valid_text = f"{valid_date:08d}{valid_hour:04d}"
    valid_time = np.datetime64(
        f"{valid_text[:4]}-{valid_text[4:6]}-{valid_text[6:8]}"
        f"T{valid_text[8:10]}:{valid_text[10:12]}"
    )
    dataset = dataset.expand_dims(time=[valid_time])
    dataset.time.attrs["timezone"] = "UTC"
    dataset.latitude.attrs["units"] = "degrees_north"
    dataset.longitude.attrs["units"] = "degrees_east"
    dataset.attrs = {
        "source": "CPTEC/INPE BRAMS",
        "source_file": input_path.name,
        "initialization_date": int(date),
        "initialization_time": int(hour),
        "source_end_step": int(step),
        "source_step_units_code": int(step_units),
        "reference_kind": "numerical model output",
        "nominal_resolution": "8 km",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_netcdf(output_path, engine="scipy")

    print(dataset)
    for name, field in dataset.data_vars.items():
        values = field.values
        finite = values[np.isfinite(values)]
        if not finite.size:
            raise ValueError(f"{name}: no finite values")
        print(
            f"{name}: min={finite.min():.3f}, max={finite.max():.3f}, "
            f"missing={np.isnan(values).sum()}, units={field.attrs['units']}"
        )
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()