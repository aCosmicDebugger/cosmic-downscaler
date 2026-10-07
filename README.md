# Cosmic Downscaler

Multivariate atmospheric downscaling from ERA5 to a BRAMS reference grid over Northeast Brazil, with interpretable baselines, scientific evaluation and geographic visualization.

**Status:** foundations and architecture planning. One BRAMS GRIB2 sample has been inspected. ERA5 acquisition, paired data construction and model training are pending. No downscaling skill is claimed yet.

## Objective

Learn a mapping from coarse ERA5 atmospheric fields to higher-resolution BRAMS simulation fields at matching valid times. Produce a reproducible regional historical dataset that can later support a separately evaluated weather-forecasting experiment.

The long-term direction is inspired by CorrDiff-style generative downscaling. The initial implementation starts with interpolation and deterministic models; generative modeling depends on demonstrated value and hardware feasibility.

## Initial scope

- Proposed domain: 1 degree N to 19 degrees S, 49 degrees W to 33 degrees W.
- ERA5 predictors paired with CPTEC/INPE BRAMS fields at matching valid times.
- Initial outputs: instantaneous 2 m temperature, 2 m dewpoint, 10 m wind components u/v, and mean sea-level pressure.
- Derived wind speed from u/v; direction with an explicit convention.
- Nearest-neighbor and bilinear interpolation baselines.
- Deterministic U-Net, patch-based training and full-field reconstruction.
- Temporal holdouts, physical-unit metrics, geographic maps and later spectral diagnostics.

Precipitation and additional atmospheric levels are extensions requiring verified field definitions, accumulation intervals and compatible data coverage. This project does not promise all ERA5 variables.

## Data

BRAMS source: [CPTEC/INPE archive](https://dataserver.cptec.inpe.br/dataserver_modelos/brams/ams_08km/brutos/2026/).

The inspected file `BRAMS_ams_08km_2026010100_2026010106.grib2` contains 268 messages on a regular latitude-longitude grid of 978 x 1009 points. Its selected surface fields are valid at 2026-01-01 06 UTC from a 00 UTC initialization. These findings apply to the inspected sample; archive consistency remains to be audited.

ERA5 access route, temporal coverage, BRAMS cycle/lead policy and source usage terms remain data-foundation tasks. Raw meteorological files stay outside Git.

## Interpretation

BRAMS is a simulation reference, not observational ground truth. A finer output grid does not guarantee accurate fine-scale weather. Comparisons with independent observations are needed before claims about real-world accuracy.

ERA5-based reconstruction is retrospective. Operational use of BRAMS, GFS or IFS inputs requires source-specific validation or adaptation; matching variable names and grids alone is insufficient.

## Development setup

Python 3.11 and uv:

```bash
uv sync --locked
uv run --locked ruff check .
uv run --locked pytest
```

These commands validate engineering setup, not a trained model. Scientific dependencies are introduced as needed.

See [architecture](docs/architecture.md) and [decisions](docs/decisions.md).