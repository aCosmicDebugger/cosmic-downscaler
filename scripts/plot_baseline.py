from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

BRAMS_PATH = Path("data/interim/brams/brams_ne_2026010106.nc")
BASELINE_PATH = Path("data/interim/baselines/gfs_linear_2026010106.nc")
OUTPUT_DIR = Path("reports/figures/baseline_2026010106")

# Name, display unit, scale and offset.
FIELDS = {
    "t2m": ("Temperature at 2 m", "degC", 1.0, -273.15),
    "d2m": ("Dewpoint at 2 m", "degC", 1.0, -273.15),
    "u10": ("Eastward wind at 10 m", "m/s", 1.0, 0.0),
    "v10": ("Northward wind at 10 m", "m/s", 1.0, 0.0),
    "msl": ("Mean sea-level pressure", "hPa", 0.01, 0.0),
}


def main():
    with xr.open_dataset(BRAMS_PATH) as source:
        brams = source.load()
    with xr.open_dataset(BASELINE_PATH) as source:
        baseline = source.load()

    baseline, brams = xr.align(baseline, brams, join="exact")
    if brams.sizes["time"] != 1:
        raise ValueError("Expected one valid time")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    valid_time = np.datetime_as_string(brams.time.values[0], unit="m")

    for name, (label, unit, scale, offset) in FIELDS.items():
        if baseline[name].attrs["units"] != brams[name].attrs["units"]:
            raise ValueError(f"{name}: incompatible units")

        reference = brams[name].isel(time=0) * scale + offset
        prediction = baseline[name].isel(time=0) * scale + offset
        difference = prediction - reference

        if not (
            np.isfinite(reference.values).all()
            and np.isfinite(prediction.values).all()
        ):
            raise ValueError(f"{name}: non-finite values")

        lower = min(reference.values.min(), prediction.values.min())
        upper = max(reference.values.max(), prediction.values.max())
        if lower == upper:
            lower -= 0.5
            upper += 0.5

        difference_limit = max(
            float(np.abs(difference.values).max()), 1e-6
        )

        fig, axes = plt.subplots(
            1,
            3,
            figsize=(15, 6),
            sharex=True,
            sharey=True,
            layout="constrained",
        )

        panels = [
            (reference, "BRAMS", "viridis", lower, upper),
            (prediction, "GFS interpolated", "viridis", lower, upper),
            (
                difference,
                "GFS - BRAMS",
                "RdBu_r",
                -difference_limit,
                difference_limit,
            ),
        ]

        for ax, (field, title, cmap, vmin, vmax) in zip(
            axes, panels, strict=True
        ):
            image = ax.pcolormesh(
                field.longitude.values,
                field.latitude.values,
                field.values,
                shading="auto",
                cmap=cmap,
                vmin=vmin,
                vmax=vmax,
            )
            ax.set_title(title)
            ax.set_xlabel("Longitude (degrees east)")
            ax.set_xlim(-49, -33)
            ax.set_ylim(-19, 1)
            ax.set_aspect("equal")
            fig.colorbar(image, ax=ax, label=unit, shrink=0.8)

        axes[0].set_ylabel("Latitude (degrees north)")
        fig.suptitle(f"{label} | {valid_time} UTC")

        output = OUTPUT_DIR / f"{name}.png"
        fig.savefig(output, dpi=180)
        plt.close(fig)
        print(f"Saved: {output}")


if __name__ == "__main__":
    main()