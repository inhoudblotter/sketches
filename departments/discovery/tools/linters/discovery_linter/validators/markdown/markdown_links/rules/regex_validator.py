import re

_MIN_MULTI_PARTS = 2

# A single line-spec: "L10", "L10-20", "L10-L20", or a comma-separated list of
# those ("L10,19" / "L16-18,44,50") — citations frequently cite several lines
# or ranges within the same source file.
_LINESPEC = r"L\d+(?:-L?\d+)?(?:,\d+(?:-L?\d+)?)*"
# A single paragraph-spec: "§5", "§5a", "§5-7", "§5a-9b", or a comma-separated
# list/slice of those — mirrors _LINESPEC but addresses prose by paragraph/
# section number instead of exact line (markdown reflows, so line numbers
# drift; author-assigned §-numbers in strategy docs like market_context.md
# stay stable across edits).
_PARASPEC = r"§\d+[a-zA-Z]?(?:-§?\d+[a-zA-Z]?)?(?:,§?\d+[a-zA-Z]?(?:-§?\d+[a-zA-Z]?)?)*"
# A single anchor: a line-spec after "#", or a paragraph-spec (which carries
# its own "§" delimiter, no "#" needed).
_ANCHOR = r"(?:#" + _LINESPEC + r"|" + _PARASPEC + r")"
# The filename charset used by both a full ref and a bare (anchor-less) file
# mention — deliberately excludes whitespace/Cyrillic/punctuation so it never
# matches ordinary prose that happens to contain a "." (e.g. "тех.карты",
# "Source: comply.ru локализация ПДн").
_FILENAME = r"[a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]+"
# A single file reference: "filename.ext#<linespec>" or "filename.ext§<paraspec>"
_REF = _FILENAME + _ANCHOR
# One or more refs in the same bracket, separated by "," or ";" (with optional
# surrounding whitespace) — e.g. "[a.md#L1, b.md#L2-L5]", "[a.md§5a, b.md§3]".
_STRICT_CITATION_RE = re.compile(r"^" + _REF + r"(?:\s*[;,]\s*" + _REF + r")*$")
_REF_RE = re.compile(r"^" + _REF + r"$")
_BARE_FILE_RE = re.compile(r"^" + _FILENAME + r"$")
# A citation attempt that starts like a real ref (filename.ext immediately
# followed by an anchor delimiter) but doesn't contain spaces. This catches
# malformed anchors like file.ext#5 without accidentally capturing prose.
_CITATION_PREFIX_RE = re.compile(r"^" + _FILENAME + r"(?:#|§)[^\s]*$")


def _is_citation_like(text: str) -> bool:
    """Gate for "does this bracket look like a source-reference citation
    attempt at all", separate from "is it well-formed". Only text shaped
    like one of the recognized citation forms gets validated/auto-fixed —
    anything else (ordinary prose brackets that happen to contain a dot,
    like "[MinIO S3-совместимое (тех.карты)]") is left untouched.
    """
    parts = re.split(r"\s*;\s*", text)
    return all(
        _REF_RE.fullmatch(p)
        or _BARE_FILE_RE.fullmatch(p)
        or _CITATION_PREFIX_RE.match(p)
        for p in parts
    )


def validate_markdown_content(content: str) -> list[str]:
    errors = []

    # 1. Check for standard markdown links pointing to local files (Generic URL format)
    # Catch [text](url) where url is not http/https/mailto/# and isn't itself a
    # well-formed strict citation used as its own link target — the fixer turns
    # "[file.md#L10]" into the clickable "[file.md#L10](file.md#L10)", which
    # must not then be flagged as an invalid generic link.
    for match in re.finditer(r"\[.*?\]\((.*?)\)", content):
        url = match.group(1)
        if url.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if _REF_RE.match(url):
            continue
        errors.append(
            f"Invalid generic URL format for source file: '{match.group(0)}'. "
            "Use strict format [filename.ext#L10]"
        )

    # 2. Check strict format for source references in brackets
    # Matches [filename.ext] or [filename.ext#L10]
    for match in re.finditer(r"\[([^\]]+)\](?!\()", content):
        text = match.group(1)

        # Ignore external URLs just in brackets
        if text.startswith(("http://", "https://")):
            continue

        if not _is_citation_like(text):
            continue

        if "#L" not in text and "§" not in text:
            errors.append(
                f"Missing line/paragraph anchor in source reference: '[{text}]'. "
                "Use format [filename.ext#L10] or [filename.ext§5]"
            )

    return errors
