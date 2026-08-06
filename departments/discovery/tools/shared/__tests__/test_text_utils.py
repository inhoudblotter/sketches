import pytest

from ..text_utils import format_compact_number


@pytest.mark.parametrize(
    "value, decimals, small_decimals, expected",
    [
        (999, 1, 0, "999"),
        (1000, 1, 0, "1.0K"),
        (4_500, 1, 0, "4.5K"),
        (1_234_567, 1, 0, "1.2M"),
        (1_500_000_000, 1, 0, "1.5B"),
        (45.678, 1, 2, "45.68"),
        (0, 1, 0, "0"),
        (-2_500_000, 1, 0, "-2.5M"),
    ],
)
def test_format_compact_number(value, decimals, small_decimals, expected):
    assert (
        format_compact_number(value, decimals=decimals, small_decimals=small_decimals)
        == expected
    )
