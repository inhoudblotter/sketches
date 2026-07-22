import re
import os

from .regex_validator import _REF as _CITATION_REF
from .regex_validator import _is_citation_like

_SINGLE_REF_RE = re.compile(_CITATION_REF)


def _replace_generic(match: re.Match) -> str:
    """Step 1: [text](url) -> [basename(url)#L1], unless url is a scheme
    link or already a well-formed strict citation used as its own target."""
    text = match.group(1)
    url = match.group(2)
    if url.startswith(("http://", "https://", "mailto:", "#")):
        return match.group(0)
    if _SINGLE_REF_RE.fullmatch(url):
        return match.group(0)

    basename = os.path.basename(url)
    if "#" not in basename:
        basename += "#L1"

    if text == url or text == os.path.basename(url):
        return f"[{basename}]"
    return f"{text} [{basename}]"


def _replace_strict(match: re.Match) -> str:
    """Step 2: fill in missing anchors on bracket-only citations."""
    text = match.group(1)
    if text.startswith(("http://", "https://")):
        return match.group(0)
    if not _is_citation_like(text):
        return match.group(0)

    if "#L" not in text and "§" not in text:
        return f"[{text}#L1]"
    return match.group(0)


def fix_markdown_content(content: str) -> str:
    content = re.sub(r"\[(.*?)\]\((.*?)\)", _replace_generic, content)
    return re.sub(r"\[([^\]]+)\](?!\()", _replace_strict, content)
