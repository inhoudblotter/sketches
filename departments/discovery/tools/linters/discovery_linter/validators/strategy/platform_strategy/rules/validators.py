import re
from pathlib import Path
from typing import Any, Dict
from departments.discovery.tools.shared.dict_utils import walk_strings

BANNED_WORDS_REGEX = re.compile(
    r"(?i)\b(UUID|varchar|Twilio|Moderator)\b|crypto/ed25519"
)


def validate_banned_words(data: Any) -> None:
    for _path, text in walk_strings(data):
        match = BANNED_WORDS_REGEX.search(text)
        if match:
            raise ValueError(
                f"Found banned word/pattern: '{match.group(0)}'. SaaS solutions, manual roles, and specific DB/crypto types are restricted."
            )


def validate_no_shared_context(file_path: Path, data: Dict[str, Any]) -> None:
    if "shared" in [p.lower() for p in file_path.parts]:
        raise ValueError(
            f"Banned directory name: 'shared' is not allowed in path {file_path}"
        )

    if isinstance(data, dict):
        platforms = data.get("platforms", [])
        if isinstance(platforms, list):
            for platform in platforms:
                if isinstance(platform, dict):
                    supported_domains = platform.get("supported_domains", [])
                    if isinstance(supported_domains, list):
                        for domain in supported_domains:
                            if (
                                isinstance(domain, str)
                                and domain.strip().lower() == "shared"
                            ):
                                raise ValueError(
                                    "Banned boundary context: 'shared' is not allowed as a supported domain."
                                )
