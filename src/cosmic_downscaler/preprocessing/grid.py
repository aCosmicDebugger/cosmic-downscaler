import numpy as np
import xarray as xr


def build_regional_field(
    latitudes,
    longitudes,
    values,
    *,
    bitmap=None,
    south=-19,
    north=1,
    west=-49,
    east=-33,
):
    """Reconstruct and crop a complete regular latitude-longitude grid."""
    lat = np.asarray(latitudes, dtype=float)
    lon = np.asarray(longitudes, dtype=float)
    data = np.array(values, dtype=float, copy=True)

    if not (
        lat.ndim == lon.ndim == data.ndim == 1
        and lat.size == lon.size == data.size
        and data.size > 0
    ):
        raise ValueError("Expected equally sized, non-empty 1D arrays")

    if not (np.isfinite(lat).all() and np.isfinite(lon).all()):
        raise ValueError("Coordinates must be finite")

    if not (-90 <= south < north <= 90):
        raise ValueError("Invalid latitude bounds")
    if not (-180 <= west < east <= 180):
        raise ValueError("Invalid longitude bounds")

    lon = (lon + 180) % 360 - 180

    if bitmap is not None:
        mask = np.asarray(bitmap)
        if mask.shape != data.shape or not np.isin(mask, [0, 1]).all():
            raise ValueError("Invalid bitmap")
        data[mask == 0] = np.nan

    latitude = np.unique(lat)
    longitude = np.unique(lon)
    order = np.lexsort((lon, lat))

    expected_lat = np.repeat(latitude, longitude.size)
    expected_lon = np.tile(longitude, latitude.size)

    if not (
        np.array_equal(lat[order], expected_lat)
        and np.array_equal(lon[order], expected_lon)
    ):
        raise ValueError("Coordinates do not form a complete regular grid")

    field = xr.DataArray(
        data[order].reshape(latitude.size, longitude.size),
        dims=("latitude", "longitude"),
        coords={"latitude": latitude, "longitude": longitude},
    )
    region = field.sel(
        latitude=slice(south, north),
        longitude=slice(west, east),
    )

    if not region.size:
        raise ValueError("Empty regional crop")

    return region