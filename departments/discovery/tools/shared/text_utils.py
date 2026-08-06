import re

_CITATION_PATTERN = re.compile(r"\s*\[[^\[\]]*(?:\.(?:md|yaml)\b|#L\d+|§)[^\[\]]*\]\s*")


def clean_links(text):
    """Strips inline source-reference brackets from narrative text meant for
    investor-facing output (pitch deck slides) — traceability citations belong
    in strategy files, not on stage. Matches any single-level bracket group that
    contains a citation marker (file.md/.yaml, #Lxx, or a §-section ref), however
    it's punctuated inside: '[file.md#L12-L34]', '[a.yaml#L10-11, #L33-43]',
    '[ux_vision.md#L16; other.md §Calm Tech Test]', '[market_context.md §5a Worst]'.
    """
    if not isinstance(text, str):
        return text
    stripped = _CITATION_PATTERN.sub(" ", text)
    stripped = re.sub(r"\s+([.,;:])", r"\1", stripped)
    return re.sub(r"\s{2,}", " ", stripped).strip()


def clean_list(lst):
    if not isinstance(lst, list):
        return lst
    return [clean_links(item) for item in lst]


_COMPACT_THRESHOLDS = ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K"))


def format_compact_number(value, decimals: int = 1, small_decimals: int = 0) -> str:
    """Abbreviates large dashboard figures (MRR, break-even users, ...) with K/M/B
    suffixes so pitch-deck metric cards stay legible at any scale, e.g.
    1234567 -> '1.2M'. Values under 1000 keep full precision with a thousands
    separator instead (e.g. 42.5 -> '42.50' with small_decimals=2)."""
    value = float(value)
    abs_value = abs(value)
    for threshold, suffix in _COMPACT_THRESHOLDS:
        if abs_value >= threshold:
            return f"{value / threshold:,.{decimals}f}{suffix}"
    return f"{value:,.{small_decimals}f}"
