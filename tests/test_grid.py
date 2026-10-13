import numpy as np
import pytest

from cosmic_downscaler.preprocessing.grid import build_regional_field


def test_reorders_coordinates_and_preserves_point_values():
    field = build_regional_field(
        [0, 0, -1, -1],
        [311, 312, 311, 312],
        [10, 20, 30, 40],
    )

    np.testing.assert_array_equal(field.latitude.values, [-1, 0])
    np.testing.assert_array_equal(field.longitude.values, [-49, -48])
    np.testing.assert_array_equal(field.values, [[30, 40], [10, 20]])


def test_crop_includes_bounds_and_preserves_missing_values():
    values = np.array([1.0, 2.0, 3.0, 4.0])
    field = build_regional_field(
        [-1, -1, 0, 0],
        [-49, -48, -49, -48],
        values,
        bitmap=[1, 0, 1, 1],
        south=-1,
        north=0,
        west=-48,
        east=-47,
    )

    assert field.shape == (2, 1)
    assert np.isnan(field.sel(latitude=-1, longitude=-48).item())
    assert field.sel(latitude=0, longitude=-48).item() == 4
    np.testing.assert_array_equal(values, [1, 2, 3, 4])


def test_rejects_duplicate_coordinate_pairs():
    with pytest.raises(ValueError, match="complete regular grid"):
        build_regional_field(
            [-1, -1, 0, 0],
            [-49, -49, -49, -48],
            [1, 2, 3, 4],
        )


def test_rejects_empty_crop():
    with pytest.raises(ValueError, match="Empty regional crop"):
        build_regional_field(
            [10, 10, 11, 11],
            [0, 1, 0, 1],
            [1, 2, 3, 4],
        )


def test_rejects_invalid_bitmap():
    with pytest.raises(ValueError, match="Invalid bitmap"):
        build_regional_field(
            [-1, -1, 0, 0],
            [-49, -48, -49, -48],
            [1, 2, 3, 4],
            bitmap=[1, 2, 1, 1],
        )