from collections import Counter
from pathlib import Path

from eccodes import (
    KeyValueNotFoundError,
    codes_get,
    codes_grib_new_from_file,
    codes_release,
)

GRIB_PATH = (
    Path("data/raw/brams")
    / "BRAMS_ams_08km_2026010100_2026010106.grib2"
)

METADATA_KEYS = [
    "shortName",
    "name",
    "paramId",
    "units",
    "typeOfLevel",
    "level",
    "dataDate",
    "dataTime",
    "stepType",
    "stepUnits",
    "startStep",
    "endStep",
    "validityDate",
    "validityTime",
]

GRID_KEYS = [
    "gridType",
    "Ni",
    "Nj",
    "numberOfPoints",
    "latitudeOfFirstGridPointInDegrees",
    "longitudeOfFirstGridPointInDegrees",
    "latitudeOfLastGridPointInDegrees",
    "longitudeOfLastGridPointInDegrees",
    "iDirectionIncrementInDegrees",
    "jDirectionIncrementInDegrees",
    "iScansNegatively",
    "jScansPositively",
    "jPointsAreConsecutive",
]


def read_key(message, key):
    try:
        return codes_get(message, key)
    except KeyValueNotFoundError:
        return None


def main():
    if not GRIB_PATH.is_file():
        raise FileNotFoundError(GRIB_PATH)

    fields = Counter()
    surface_candidates = []
    grid_signatures = Counter()

    print(f"File: {GRIB_PATH}")
    print(f"Size: {GRIB_PATH.stat().st_size / 1024**2:.1f} MiB")

    with GRIB_PATH.open("rb") as stream:
        message_number = 0

        while True:
            message = codes_grib_new_from_file(stream)
            if message is None:
                break

            message_number += 1

            try:
                metadata = {
                    key: read_key(message, key)
                    for key in METADATA_KEYS
                }
                grid = {
                    key: read_key(message, key)
                    for key in GRID_KEYS
                }

                fields[
                    (
                        metadata["shortName"],
                        metadata["typeOfLevel"],
                        metadata["stepType"],
                    )
                ] += 1

                grid_signatures[tuple(grid.items())] += 1

                # Inspect every 2 m and 10 m field, including duplicates.
                if (
                    metadata["typeOfLevel"] == "heightAboveGround"
                    and metadata["level"] in (2, 10)
                ):
                    surface_candidates.append(
                        (message_number, metadata)
                    )
            finally:
                codes_release(message)

    print(f"\nTotal messages: {message_number}")

    print("\nGrids:")
    for signature, count in grid_signatures.items():
        print(f"\nUsed by {count} messages:")
        for key, value in signature:
            print(f"  {key}: {value}")

    print("\nField inventory:")
    for (variable, level_type, step_type), count in sorted(
        fields.items(), key=lambda item: str(item[0])
    ):
        print(
            f"  {variable} | {level_type} | "
            f"{step_type} | {count} messages"
        )

    print("\nDetailed fields at 2 m and 10 m:")
    for number, metadata in surface_candidates:
        print(f"\nMessage {number}:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()