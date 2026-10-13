import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(path):
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def run_script(name, arguments):
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / name),
            *arguments,
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Run interpolation baselines from a paired manifest"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--method",
        choices=["linear", "nearest"],
        default="linear",
    )
    args = parser.parse_args()

    manifest_path = project_path(args.manifest)
    run_dir = project_path(args.run_dir)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["schema_version"] != 1:
        raise ValueError("Unsupported manifest schema")

    samples = manifest["samples"]
    if not samples or manifest["n_pairs"] != len(samples):
        raise ValueError("Invalid manifest sample count")

    seen_ids = set()
    for sample in samples:
        sample_id = sample["sample_id"]
        if re.fullmatch(r"\d{10}", sample_id) is None:
            raise ValueError(f"Invalid sample ID: {sample_id}")
        if sample_id in seen_ids:
            raise ValueError(f"Duplicate sample ID: {sample_id}")
        seen_ids.add(sample_id)

        for model in ["gfs", "brams"]:
            path = project_path(sample[model]["path"])
            if not path.is_file():
                raise FileNotFoundError(path)

    run_dir.mkdir(parents=True, exist_ok=False)
    datasets_dir = run_dir / "datasets"
    metrics_dir = run_dir / "metrics"
    datasets_dir.mkdir()
    metrics_dir.mkdir()

    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    for index, sample in enumerate(samples, start=1):
        sample_id = sample["sample_id"]
        print(
            f"\n[{index}/{len(samples)}] Processing {sample_id}",
            flush=True,
        )

        run_script(
            "baseline_interpolation.py",
            [
                "--gfs",
                str(project_path(sample["gfs"]["path"])),
                "--brams",
                str(project_path(sample["brams"]["path"])),
                "--output",
                str(datasets_dir / f"gfs_{args.method}_{sample_id}.nc"),
                "--metrics",
                str(metrics_dir / f"gfs_{args.method}_{sample_id}.json"),
                "--method",
                args.method,
            ],
        )

    run_script(
        "summarize_baselines.py",
        [
            "--input-dir",
            str(metrics_dir),
            "--output",
            str(run_dir / "summary.json"),
        ],
    )

    print(f"\nCompleted {len(samples)} baselines: {run_dir}", flush=True)


if __name__ == "__main__":
    main()