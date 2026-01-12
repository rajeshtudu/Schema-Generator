from utils.schema_helpers import to_script_tag

import json


def clean_list(text: str):
    """
    Converts multiline text input into a clean list.
    """
    if not text:
        return []
    return [line.strip() for line in text.split("\n") if line.strip()]


def to_script_tag(schema: dict) -> str:
    """
    Wraps a schema dict in a JSON-LD <script> tag.
    """
    return (
        '<script type="application/ld+json">\n'
        + json.dumps(schema, ensure_ascii=False, indent=2)
        + '\n</script>'
    )