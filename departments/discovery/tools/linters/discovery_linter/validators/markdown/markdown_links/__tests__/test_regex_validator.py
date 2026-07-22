import glob
import os

from ..rules.fixer import fix_markdown_content
from ..rules.regex_validator import validate_markdown_content

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *([".."] * 9)))
_WORKSPACE_DIR = os.path.join(_REPO_ROOT, "workspace")


def _workspace_markdown_files():
    return sorted(glob.glob(os.path.join(_WORKSPACE_DIR, "**", "*.md"), recursive=True))


def test_valid_single_line_citation_not_flagged():
    content = "See [market_context.md#L10] for detail."
    assert validate_markdown_content(content) == []


def test_valid_line_range_citation_not_flagged():
    content = "See [market_context.md#L10-L20] for detail."
    assert validate_markdown_content(content) == []


def test_valid_comma_line_list_citation_not_flagged():
    content = "See [market_context.md#L10,19,25-30] for detail."
    assert validate_markdown_content(content) == []


def test_valid_paragraph_citation_not_flagged():
    content = "See [market_context.md§5] for detail."
    assert validate_markdown_content(content) == []


def test_valid_paragraph_letter_citation_not_flagged():
    content = "See [market_context.md§5a] for detail."
    assert validate_markdown_content(content) == []


def test_valid_multi_ref_citation_not_flagged():
    content = "See [a.md#L1; b.md#L2-L5] for detail."
    assert validate_markdown_content(content) == []


def test_valid_real_markdown_link_not_flagged():
    content = "See [Ultralytics docs](https://docs.ultralytics.com/models/mobile-sam)."
    assert validate_markdown_content(content) == []


def test_valid_fixed_local_citation_not_flagged():
    # A generic [text](file.ext#L1) link produced by the fixer over a strict
    # citation used as its own target must not then be re-flagged.
    content = "See [market_context.md#L10](market_context.md#L10) for detail."
    assert validate_markdown_content(content) == []


def test_ordinary_prose_not_flagged():
    content = (
        "MinIO S3-совместимое (тех.карты) [MinIO S3-совместимое (тех.карты)] хранение."
    )
    assert validate_markdown_content(content) == []


def test_missing_anchor_citation_is_flagged():
    content = "See [dictionary.yaml] for the glossary."
    errors = validate_markdown_content(content)
    assert len(errors) == 1
    assert "Missing line/paragraph anchor" in errors[0]
    assert "dictionary.yaml" in errors[0]


def test_malformed_multi_ref_missing_filename_repeat_not_flagged():
    # Relaxed mode: a bracket whose text doesn't cleanly match a citation
    # shape end-to-end (e.g. a dangling range with no filename+anchor of its
    # own) is treated as "not citation-like" and left alone rather than
    # blocking validation over a formatting nitpick.
    content = "See [revenue_model.yaml#L12-24, #L38-45] for detail."
    errors = validate_markdown_content(content)
    assert errors == []


def test_generic_local_link_with_bad_anchor_is_flagged():
    content = "See [glossary](dictionary.yaml) for detail."
    errors = validate_markdown_content(content)
    assert len(errors) == 1
    assert "Invalid generic URL format" in errors[0]


def test_validator_over_fixed_real_workspace_files_reports_no_errors():
    files = _workspace_markdown_files()
    assert files, "expected at least one real .md file under workspace/"

    total_errors = []
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        fixed = fix_markdown_content(content)
        errors = validate_markdown_content(fixed)
        total_errors.extend((path, e) for e in errors)

    # Relaxed mode: the validator only blocks on the clear-cut cases (a
    # citation-shaped bracket missing its anchor entirely, or a generic
    # local link with a bad target) and otherwise stays out of the way — so
    # after auto-fixing, the real corpus should produce no errors at all.
    assert (
        total_errors == []
    ), f"unexpected validator errors over the fixed real workspace corpus: {total_errors}"
