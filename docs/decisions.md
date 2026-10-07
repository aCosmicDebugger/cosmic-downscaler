# Project decisions

## Northeast multivariate reconstruction from ERA5

Date: 2026-10-06
Status: accepted

Use ERA5 as coarse retrospective input and CPTEC/INPE BRAMS as a simulation reference on its nominal 8 km grid. Proposed domain: 1 N to 19 S and 49 W to 33 W, subject to map verification.

Initial outputs are instantaneous 2 m temperature/dewpoint, 10 m u/v wind and mean sea-level pressure. Additional variables require compatible field and temporal definitions. Preserve u/v and derive speed.

Progress from interpolation to deterministic U-Net, residual learning and a conditional generative experiment inspired by CorrDiff. Preserve patch-based feasibility on a 16 GB GPU.

The inspected +6 h BRAMS file proves sample readability, not an accepted archive-wide lead policy. Temporal overlap, lead choice and ERA5 access remain pending.

Historical outputs may support a separately scoped 48-72-hour weather forecaster. Operational inputs require availability-aware backtesting and source-specific validation. This decision does not replace the existing forecast-forge laboratory scope.