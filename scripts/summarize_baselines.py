import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from statistics import mean

FIELDS = ["t2m", "d2m", "u10", "v10", "msl"]
POLICY_KEYS = [
    "schema_version",
    "method",
    "difference",
    "weighting",
    "domain",
    "reference_kind",
]


def aggregate_reports(reports):
    summary = {}

    for name in FIELDS:
        metrics = [report["metrics"][name] for report in reports]
        summary[name] = {
            "mae": mean(metric["mae"] for metric in metrics),
            "rmse": math.sqrt(
                mean(metric["rmse"] ** 2 for metric in metrics)
            ),
            "bias": mean(metric["bias"] for metric in metrics),
            "units": metrics[0]["units"],
            "n_cells_per_time": metrics[0]["n_cells"],
        }

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Summarize baseline metrics with equal weight per time"
    )
    parser.add_argument(
        "--input-dir", type=Path, default=Path("reports/metrics")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/metrics/baseline_summary.json"),
    )
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError(args.output)

    files = sorted(args.input_dir.glob("gfs_linear_*.json"))
    if not files:
        raise FileNotFoundError("No baseline metric files found")
    if args.output.resolve() in {path.resolve() for path in files}:
        raise ValueError("Output must not be an input file")

    reports = []
    seen_times = set()

    for path in files:
        report = json.loads(path.read_text(encoding="utf-8"))
        valid_time = report["valid_time_utc"]

        if valid_time in seen_times:
            raise ValueError(f"Duplicate valid time: {valid_time}")
        seen_times.add(valid_time)

        if reports:
            for key in POLICY_KEYS:
                if report[key] != reports[0][key]:
                    raise ValueError(f"{path}: incompatible {key}")

            for key in ["source_end_step", "source_step_units_code"]:
                if (
                    report["source_metadata"][key]
                    != reports[0]["source_metadata"][key]
                ):
                    raise ValueError(f"{path}: incompatible {key}")

        for name in FIELDS:
            metric = report["metrics"][name]
            for key in ["mae", "rmse", "bias"]:
                if not math.isfinite(metric[key]):
                    raise ValueError(f"{path}: non-finite {name}/{key}")

            if metric["mae"] < 0 or metric["rmse"] < 0:
                raise ValueError(f"{path}: negative error metric")
            if metric["n_cells"] <= 0:
                raise ValueError(f"{path}: invalid cell count")

            if reports:
                first = reports[0]["metrics"][name]
                if (
                    metric["units"] != first["units"]
                    or metric["n_cells"] != first["n_cells"]
                ):
                    raise ValueError(f"{path}: incompatible {name}")

        reports.append(report)

    reports.sort(key=lambda report: report["valid_time_utc"])
    summary = aggregate_reports(reports)

    groups = {}
    for report in reports:
        valid_time = datetime.fromisoformat(report["valid_time_utc"])
        hour = valid_time.strftime("%H:%M")
        groups.setdefault(hour, []).append(report)

    by_hour = {
        hour: {
            "n_times": len(group),
            "metrics": aggregate_reports(group),
        }
        for hour, group in sorted(groups.items())
    }
    print("Per-time metrics: MAE / RMSE / bias")
    for report in reports:
        print(f"\n{report['valid_time_utc']} UTC")
        for name in FIELDS:
            metric = report["metrics"][name]
            print(
                f"  {name}: {metric['mae']:.3f} / "
                f"{metric['rmse']:.3f} / {metric['bias']:.3f} "
                f"{metric['units']}"
            )

    print(f"\nAggregate: {len(reports)} equally weighted times")
    for name, metric in summary.items():
        print(
            f"{name}: MAE={metric['mae']:.3f}, "
            f"RMSE={metric['rmse']:.3f}, bias={metric['bias']:.3f}, "
            f"units={metric['units']}"
        )
    
    for hour, group in by_hour.items():
        print(f"\nValid time {hour} UTC: {group['n_times']} samples")
        for name, metric in group["metrics"].items():
            print(
                f"{name}: MAE={metric['mae']:.3f}, "
                f"RMSE={metric['rmse']:.3f}, bias={metric['bias']:.3f}, "
                f"units={metric['units']}"
            )

    output = {
        "schema_version": 2,
        "aggregation": "equal weight per valid time",
        "spatial_policy": {
            key: reports[0][key] for key in POLICY_KEYS
        },
        "n_times": len(reports),
        "valid_times_utc": [
            report["valid_time_utc"] for report in reports
        ],
        "input_files": [str(path) for path in files],
        "aggregate_metrics": summary,
        "per_time": reports,
        "metrics_by_valid_hour_utc": by_hour,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()