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
