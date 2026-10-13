from pathlib import Path

import numpy as np
import xarray as xr

GFS_PATH = Path("data/interim/gfs/gfs_ne_2026010106.nc")
BRAMS_PATH = Path("data/interim/brams/brams_ne_2026010106.nc")
OUTPUT = Path("data/interim/baselines/gfs_linear_2026010106.nc")
FIELDS = ["t2m", "d2m", "u10", "v10", "msl"]


def main():
    with xr.open_dataset(GFS_PATH) as source:
        gfs = source[FIELDS].load()
    with xr.open_dataset(BRAMS_PATH) as source:
        brams = source[FIELDS].load()

    if not np.array_equal(gfs.time.values, brams.time.values):
        raise ValueError("Different valid times")

    for name in FIELDS:
        if gfs[name].attrs["units"] != brams[name].attrs["units"]:
            raise ValueError(f"{name}: incompatible units")

    interpolated = gfs.interp(
        latitude=brams.latitude,
        longitude=brams.longitude,
        method="linear",
    )
    interpolated, brams = xr.align(
        interpolated, brams, join="exact"
    )

    weights = np.cos(np.deg2rad(brams.latitude))
    dimensions = ("time", "latitude", "longitude")

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

        print(
            f"{name}: MAE={mae:.3f}, RMSE={np.sqrt(mse):.3f}, "
            f"bias={bias:.3f}, units={reference.attrs['units']}"
        )

    interpolated.attrs.pop("grid_spacing_degrees", None)
    interpolated.attrs.update(
        {
            "interpolation_method": "linear along latitude and longitude",
            "target_grid_source": BRAMS_PATH.name,
            "verification_reference": "BRAMS numerical model output",
        }
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    interpolated.to_netcdf(OUTPUT, engine="scipy")
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()