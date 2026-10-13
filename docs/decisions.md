# Project decisions

## Northeast multivariate reconstruction from ERA5

Date: 2026-10-06
Status: superseded by the GFS-first decision below

Use ERA5 as coarse retrospective input and CPTEC/INPE BRAMS as a simulation reference on its nominal 8 km grid. Proposed domain: 1 N to 19 S and 49 W to 33 W, subject to map verification.

Initial outputs are instantaneous 2 m temperature/dewpoint, 10 m u/v wind and mean sea-level pressure. Additional variables require compatible field and temporal definitions. Preserve u/v and derive speed.

Progress from interpolation to deterministic U-Net, residual learning and a conditional generative experiment inspired by CorrDiff. Preserve patch-based feasibility on a 16 GB GPU.

The inspected +6 h BRAMS file proves sample readability, not an accepted archive-wide lead policy. Temporal overlap, lead choice and ERA5 access remain pending.

Historical outputs may support a separately scoped 48-72-hour weather forecaster. Operational inputs require availability-aware backtesting and source-specific validation. This decision does not replace the existing forecast-forge laboratory scope.

## GFS-first downscaling and connected regional forecasting

Date: 2026-10-10
Status: accepted

GFS replaces ERA5 as the principal coarse source for historical training and production. BRAMS remains the nominal 8 km regional simulation reference. ERA5 is an optional retrospective experiment requiring a separate adapter and source-specific evaluation. This supersedes the ERA5-first decision above.

Retain the Northeast domain, five initial fields, interpolation/U-Net/residual/generative progression and hardware constraints. Finer grids alone do not establish improved accuracy.

Pair by valid time while recording initialization, lead and availability for both models. Audit historical overlap and freeze causal cycle/lead policies before training. Evaluate analysis, short-lead and longer-lead regimes explicitly; do not silently mix them.

Export recent downscaled histories for forecast-forge, a temporal regional predictor up to 72 hours ahead. Downscaled future GFS forecasts are a required comparison, not an implicit future input to the first Forge model. GFS lead-dependent downscaler performance must be evaluated.

Train the downscaler without held-out downstream targets. Use time-blocked cross-fitting for Forge training data when feasible so the Forge does not train only on unrealistically easy in-sample downscaler outputs. Record fitting periods for every checkpoint. Evaluate against held-out BRAMS and independent observations where available.

GOES multimodal integration and a future energy/extreme-weather/outage application remain extensions. No 0.5 km all-variable product or operational outage capability is claimed.
