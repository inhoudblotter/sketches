import re
import yaml


def split_zones(text: str) -> tuple[dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not match:
        raise ValueError("Нет frontmatter")
    frontmatter = yaml.safe_load(match.group(1))
    body = match.group(2)
    return frontmatter, body


def extract_xml_block(body: str, tag: str) -> str:
    match = re.search(
        rf"^[ \t]*<{tag}>\s*(.*?)^[ \t]*</{tag}>", body, re.MULTILINE | re.DOTALL
    )
    if not match:
        # Fallback to loose search if strictly anchored fails, but require newlines around the tags
        match = re.search(rf"<{tag}>\n(.*?)\n[ \t]*</{tag}>", body, re.DOTALL)
    return match.group(1) if match else ""
