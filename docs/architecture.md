# Architecture and scope

Date: 2026-10-10
Status: accepted direction; temporal coverage and pairing policy pending validation.

## 1. Research question

Can a reproducible multivariate model reconstruct regional BRAMS simulation fields from GFS at matching valid times better than spatial interpolation, while preserving useful spatial structure and cross-variable consistency?

Users are scientific ML reviewers and researchers developing regional weather experiments. A later consumer is a weather forecaster using sequences of generated historical fields. forecast-forge is the companion temporal weather predictor: it consumes recent regional histories and predicts subsequent fields up to 72 hours ahead.

## 2. Domain and field contract

Use a proposed bounding box of north 1 N, south 19 S, west 49 W and east 33 W. Verify coverage of all nine Northeast states against a documented boundary source. Keep surrounding land and ocean as context, and report separate metrics over the state mask and full domain. Exact cell selection and boundary padding must be recorded.

Use the actual BRAMS latitude-longitude coordinates as the output grid. The archive's nominal 8 km label is not a constant physical spacing: longitudinal cell size varies with latitude.

| Initial output | BRAMS sample identifier | Contract |
| --- | --- | --- |
| Temperature at 2 m | 2t | Instantaneous, Kelvin |
| Dewpoint at 2 m | 2d | Instantaneous, Kelvin |
| Wind u at 10 m | 10u | Instantaneous eastward component, m/s |
| Wind v at 10 m | 10v | Instantaneous northward component, m/s |
| Mean sea-level pressure | prmsl | Instantaneous; verify unit and parameter metadata |

Confirm GFS counterparts, units, level definitions and coordinate conventions before pairing. Keep u and v as learned outputs; derive speed as sqrt(u^2 + v^2). Define meteorological wind-direction convention and mask calm-wind direction where appropriate. Temperature minima/maxima over an interval are not substitutes for instantaneous temperature.

Predictor channels can exceed output channels, but additions require availability and ablation evidence. Static elevation and land/sea information are candidates after the simplest baseline. No atmospheric level or precipitation variable enters by name alone: identify parameter, level, time statistic and accumulation boundaries.

## 3. Source evidence and pending choices

User inspection of `BRAMS_ams_08km_2026010100_2026010106.grib2` confirmed a regular_ll grid, Ni=978, Nj=1009, latitudes approximately -51.7434 to 15.6279 and longitudes 267.1327 to 340.8670. Initial temperature, dewpoint and wind fields are instantaneous at +6 hours, valid 2026-01-01 06 UTC. Temperature maxima/minima span +5 to +6 hours.

This is a single sample. It does not establish archive completeness, latency, consistency or optimal forecast lead. Audit multiple cycles and dates before freezing a BRAMS lead policy. Start with a fixed lead candidate such as +6 h, but choose and justify it after checking availability and spin-up behavior. Never silently mix different leads for the same valid time.

Choose the period only after verifying overlapping GFS/BRAMS coverage. One year may limit seasonal and interannual generalization; document the actual limits rather than promising coverage.

## 4. Pipeline and responsibilities

```mermaid
flowchart TD
    E[GFS fields] --> A[Time and field alignment]
    B[BRAMS fields] --> A
    A --> G[Grid and unit validation]
    G --> S[Temporal split]
    S --> P[Training patches and normalization]
    P --> M[Interpolation and neural models]
    M --> R[Full-field reconstruction]
    R --> V[Metrics and geographic reports]
    R --> H[Versioned historical output]
```

| Module | Responsibility |
| --- | --- |
| data | Source discovery, download, manifests and GRIB/NetCDF reads |
| preprocessing | Time matching, units, coordinates, regridding and masks |
| datasets | Temporal partitions, normalization application and patches |
| models | Interpolation wrappers, U-Net and later residual/generative models |
| training | Reproducible training, checkpoints and validation |
| evaluation | Physical-unit metrics, uncertainty and spatial diagnostics |
| visualization | Geographic comparisons, errors and later spectra |

Authoritative code lives under src/cosmic_downscaler. Notebooks support exploration. No API or orchestration service is required by the first batch experiment.

## 5. Alignment and reproducibility

Record initialization time, forecast lead, valid time and download time independently. Pair GFS with BRAMS using valid time in UTC. Resolve duplicate valid times according to the frozen cycle/lead rule.

Normalize longitude convention, sort coordinates consistently, verify scan orientation and check land/sea boundaries. Any interpolation of GFS to the target grid must be explicit and identical for baseline and neural comparisons. Do not interpolate BRAMS onto a coarser grid and then claim retained native high-resolution targets.

Version source files by hashes, field selection, grid, domain, masks, units and pairing policy. Record source/model changes and missing dates. Build a manifest with one entry per paired timestamp and required variable set. Reject or explicitly flag incomplete pairs; no silent temporal interpolation across missing fields.

Processed formats may be NetCDF or chunked Zarr; choose after I/O measurements. Stream/select fields instead of keeping the continental archive in RAM. Record code revision, configuration, seeds and actual dependencies.

## 6. Model progression

1. Nearest-neighbor and bilinear interpolation for each compatible field.
2. Deterministic multichannel U-Net with documented predictor/output grid handling.
3. Residual learning relative to a declared interpolation or deterministic reference; compare whether it adds measurable value.
4. Lightweight conditional generative residual experiment, inspired by CorrDiff, only after deterministic evaluation and resource profiling.

Train with patches on the available 16 GB GPU and 64 GB RAM. Select patch size and batch size empirically. Maintain spatial alignment between coarse predictors and fine targets. If using upsampled inputs, record that architectural choice.

Fit per-channel normalization on training periods only. Use channel-scaled losses so Kelvin, Pa and m/s do not compete solely because of unit magnitude. State weights and validate cross-variable consistency, including dewpoint exceeding temperature and wind speed consistency. Do not hide violations using post-processing without reporting its effect.

## 7. Temporal evaluation

Split complete timestamps and their patches chronologically. Keep all overlapping patches, all variables and outputs from a common meteorological event within the same partition. Use temporal gaps chosen from window length and dependence diagnostics. A later forecaster additionally requires windows whose inputs and future targets do not cross split boundaries.

Choose model settings on validation and freeze final test periods. Report overall, seasonal and regional results with actual sample counts. Estimate uncertainty using temporal blocks rather than treating correlated pixels or adjacent hours as independent observations.

Evaluate reconstructed fields, not only individual patches. Use overlapping-patch blending and report edge/seam effects. RMSE, MAE and signed bias are reported in physical units, with area weighting and a documented state mask. Evaluate u/v and derived speed; direction needs circular treatment and a calm-wind rule.

Use maps of inputs, interpolation, BRAMS reference, predictions and errors. Later add spectra and distribution/extreme diagnostics with consistent masks and preprocessing. Generative models require ensemble calibration, spread and proper probabilistic scores in addition to point errors; low sample RMSE alone is insufficient.

Primary metrics and practical improvement criteria must be frozen before inspecting final test results. Independent station or other observation comparisons are a separate validation requirement for real-world accuracy claims, including representativeness and elevation differences.

## 8. Historical output interface

Export versioned fields with valid_time, latitude, longitude and explicit named variables/units. Retain input source, downscaler version, reference-grid version, lead policy, masks and quality flags. A stochastic extension also needs ensemble member and sampling metadata.

Future weather-model training may use sequences of these fields to predict 48-72 hours ahead. This is synthetic/model-derived training data and can propagate downscaler and BRAMS biases. Evaluate future predictions against held-out BRAMS and independent observations where available; agreement with the same generator alone is not evidence of weather skill.

For downstream validation/test periods, fit the downscaler without those periods. Use chronological fitting or cross-fitting for downstream development so generated outputs are not misleadingly evaluated on dates seen during downscaler training.

## 9. Operational integration

GFS is the primary source for both historical training and production. ERA5 remains an optional retrospective experiment with a separate source adapter and checkpoint. Do not substitute sources solely because names or grids match.

Audit GFS/BRAMS historical overlap, model upgrades and operational publication latency. Record each source initialization, lead, valid time and availability independently. Match valid times, retain both models' leads, and condition on GFS lead or train/evaluate separate lead regimes. An analysis and a +72-hour forecast are not interchangeable predictors.

Two exports have different uses:

- Recent downscaled GFS analysis or short-lead states, available at issuance, initialize forecast-forge. Freeze a causal cycle/lead policy and train on the same policy.
- Future GFS forecasts downscaled to the regional grid provide a competing forecast trajectory. Validate downscaler skill at each supported lead before using this baseline.

For operational backtests, use only inputs published by issuance and never later cycles or revised fields. If an input is a forecast-derived state, label it accordingly. Publication time cannot be inferred from valid time. Report latency, missing cycles and fallback behavior.

Compare Forge forecasts with persistence and native/downscaled GFS forecasts using the same issuance and target times. The Forge initially learns temporal evolution without ingesting future GFS trajectories; a future conditioned variant is a separate experiment.

## 9a. GOES and energy extensions

GOES observations are candidate additional inputs for convection and short-term extreme-weather experiments. They are not equivalent to surface temperature, wind or pressure references; no universal 0.5 km target grid is adopted. Source geometry, bands, day/night availability, latency and target definitions require a separate contract.

A future application project can consume outputs for wind energy and outage risk. Wind at turbine height, gusts, lightning targets, power curves, generation records and grid/interruption data require separate acquisition and validation. The five-field MVP does not claim these capabilities.

## 10. Completion criteria and open decisions

Documentation is complete when scope, contracts and pending choices are explicit. Data foundations require source terms, GFS access, verified regional coverage, overlap period, field matches, BRAMS lead/cycle policy and temporal partitions.

The first baseline release requires reproducible paired data, meaningful tests of alignment and patch reconstruction, interpolation reports in physical units and geographic comparisons. The deterministic release adds reproducible training, held-out improvement analysis and limitations. Generative and operational extensions require separate evidence and are not prerequisites for a useful first release.

## References

- [CPTEC/INPE BRAMS archive](https://dataserver.cptec.inpe.br/dataserver_modelos/brams/ams_08km/brutos/2026/)
- [Inspected sample descriptor](https://dataserver.cptec.inpe.br/dataserver_modelos/brams/ams_08km/brutos/2026/01/01/00/BRAMS_ams_08km_2026010100_2026010106.ctl)
- [NOAA GFS data access](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast)

Record exact dataset documentation and selected release/version during ingestion. These links do not substitute for verification of download rights or variable contracts.
