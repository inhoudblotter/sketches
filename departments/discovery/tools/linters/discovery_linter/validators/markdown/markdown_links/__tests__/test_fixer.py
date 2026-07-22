import glob
import os

from ..rules.fixer import fix_markdown_content

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *([".."] * 9)))
_WORKSPACE_DIR = os.path.join(_REPO_ROOT, "workspace")


def _workspace_markdown_files():
    return sorted(glob.glob(os.path.join(_WORKSPACE_DIR, "**", "*.md"), recursive=True))


def test_workspace_has_markdown_files():
    # Sanity check the corpus this idempotency test relies on actually exists.
    assert len(_workspace_markdown_files()) > 0


def test_fix_markdown_content_is_idempotent_over_real_workspace():
    files = _workspace_markdown_files()
    assert files, "expected at least one real .md file under workspace/"

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            original = f.read()

        first_pass = fix_markdown_content(original)
        second_pass = fix_markdown_content(first_pass)

        assert second_pass == first_pass, (
            f"fix_markdown_content is not idempotent for {path}: "
            "running it twice produced different output"
        )


def test_bare_filename_citation_gets_line_one_anchor_appended():
    content = "See [dictionary.yaml] for the glossary."
    fixed = fix_markdown_content(content)
    assert fixed == "See [dictionary.yaml#L1] for the glossary."
    # Not wrapped into a markdown link.
    assert "](" not in fixed


def test_bare_url_citation_left_untouched():
    # Relaxed mode: bare-URL-shaped bracket text isn't citation-like (no
    # filename.ext+anchor shape), so the fixer leaves it as-is rather than
    # wrapping it into a markdown link.
    content = "Reference: [docs.ultralytics.com/models/mobile-sam]"
    fixed = fix_markdown_content(content)
    assert fixed == content


def test_multi_domain_citation_left_untouched():
    content = "Sources: [a.com/x, b.com/y]"
    fixed = fix_markdown_content(content)
    assert fixed == content


def test_already_valid_citation_left_untouched():
    content = "See [market_context.md#L10] for detail."
    fixed = fix_markdown_content(content)
    assert fixed == content


def test_already_valid_multi_ref_citation_left_untouched():
    content = "See [a.md#L1; b.md#L2-L5] for detail."
    fixed = fix_markdown_content(content)
    assert fixed == content


def test_already_valid_paragraph_citation_left_untouched():
    content = "See [market_context.md§5a] for detail."
    fixed = fix_markdown_content(content)
    assert fixed == content


def test_ordinary_prose_with_dots_and_brackets_not_corrupted():
    content = (
        "MinIO S3-совместимое (тех.карты) [MinIO S3-совместимое (тех.карты)] хранение."
    )
    fixed = fix_markdown_content(content)
    assert fixed == content


def test_ordinary_prose_with_russian_domain_like_text_not_corrupted():
    content = "Source: comply.ru локализация ПДн [comply.ru локализация ПДн]"
    fixed = fix_markdown_content(content)
    assert fixed == content


def test_generic_markdown_link_to_local_file_gets_flattened():
    content = "[revenue_model.yaml](revenue_model.yaml)"
    fixed = fix_markdown_content(content)
    assert fixed == "[revenue_model.yaml#L1]"


def test_generic_markdown_link_to_http_url_untouched():
    content = "[Ultralytics docs](https://docs.ultralytics.com/models/mobile-sam)"
    fixed = fix_markdown_content(content)
    assert fixed == content
