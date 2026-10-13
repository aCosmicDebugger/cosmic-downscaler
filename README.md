# Cosmic Downscaler

Multivariate atmospheric downscaling from GFS to a BRAMS reference grid over Northeast Brazil, with interpretable baselines, scientific evaluation and geographic visualization.

**Status:** foundations and architecture planning. One BRAMS GRIB2 sample has been inspected. GFS acquisition, paired data construction and model training are pending. No downscaling skill is claimed yet.

## Objective

Learn a mapping from coarse GFS atmospheric fields to higher-resolution BRAMS simulation fields at matching valid times. Export regional histories for forecast-forge, which learns temporal evolution and predicts up to 72 hours ahead. The downscaler can also refine future GFS forecast fields, providing a mandatory numerical-forecast baseline for the Forge.

The long-term direction is inspired by CorrDiff-style generative downscaling. The initial implementation starts with interpolation and deterministic models; generative modeling depends on demonstrated value and hardware feasibility.

## Initial scope

- Proposed domain: 1 degree N to 19 degrees S, 49 degrees W to 33 degrees W.
- GFS predictors paired with CPTEC/INPE BRAMS fields at matching valid times.
- Initial outputs: instantaneous 2 m temperature, 2 m dewpoint, 10 m wind components u/v, and mean sea-level pressure.
- Derived wind speed from u/v; direction with an explicit convention.
- Nearest-neighbor and bilinear interpolation baselines.
- Deterministic U-Net, patch-based training and full-field reconstruction.
- Temporal holdouts, physical-unit metrics, geographic maps and later spectral diagnostics.

Precipitation and additional atmospheric levels are extensions requiring verified field definitions, accumulation intervals and compatible data coverage. This project does not promise all atmospheric variables.

## Data

BRAMS source: [CPTEC/INPE archive](https://dataserver.cptec.inpe.br/dataserver_modelos/brams/ams_08km/brutos/2026/).

The inspected file `BRAMS_ams_08km_2026010100_2026010106.grib2` contains 268 messages on a regular latitude-longitude grid of 978 x 1009 points. Its selected surface fields are valid at 2026-01-01 06 UTC from a 00 UTC initialization. These findings apply to the inspected sample; archive consistency remains to be audited.

GFS historical and operational access routes, temporal coverage, BRAMS cycle/lead policy and source usage terms remain data-foundation tasks. Raw meteorological files stay outside Git.

## Interpretation

BRAMS is a simulation reference, not observational ground truth. A finer output grid does not guarantee accurate fine-scale weather. Comparisons with independent observations are needed before claims about real-world accuracy.

GFS is the primary training and operational source. ERA5 is an optional retrospective experiment; its checkpoints are not interchangeable with GFS checkpoints. The initial experiment is historical, followed by an availability-aware operational demonstration.

## Development setup

Python 3.11 and uv:

```bash
uv sync --locked
uv run --locked ruff check .
uv run --locked pytest
```

These commands validate engineering setup, not a trained model. Scientific dependencies are introduced as needed.

See [architecture](docs/architecture.md) and [decisions](docs/decisions.md).

## Integration and future applications

The initial Forge experiment uses only recent downscaled states available by issuance time, not future GFS fields as implicit input. Generated fields are model-derived data; retain provenance and evaluate against held-out references. Matching valid time is necessary but does not establish independent truth.

GOES is a future complementary observation input, not a 0.5 km reference for all meteorological variables. Energy generation, severe-weather guidance and power-outage risk are a separate future application layer requiring additional fields and validation. The initial grid remains nominal 8 km.

See the GFS access documentation at https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast. Archive overlap, field availability and publication latency must be audited before fixing the production policy.
