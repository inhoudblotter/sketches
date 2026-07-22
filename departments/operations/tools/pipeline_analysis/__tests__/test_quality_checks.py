from departments.operations.tools.pipeline_analysis.engine.validation.quality_checks import (
    _strip_ansi,
)


def test_strip_ansi_removes_color_codes() -> None:
    """Regression: when pytest is invoked (by run_tests) under an environment
    that forces color (e.g. FORCE_COLOR=1), its captured stdout carries raw
    ANSI escape codes straight into ERRORS.md. _strip_ansi must clean them."""
    colored = "\x1b[32m\x1b[32m\x1b[1m53 passed\x1b[0m\x1b[32m in 11.46s\x1b[0m\x1b[0m"

    assert _strip_ansi(colored) == "53 passed in 11.46s"


def test_strip_ansi_is_noop_on_plain_text() -> None:
    assert _strip_ansi("53 passed in 4.93s") == "53 passed in 4.93s"
