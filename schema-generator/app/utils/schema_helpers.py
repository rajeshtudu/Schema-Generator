import json


def clean_list(text):
    """
    Takes a textarea string and returns a cleaned list of non-empty lines.
    """
    if not text:
        return []
    lines = []
    for line in text.splitlines():
        l = (line or "").strip()
        if l:
            lines.append(l)
    return lines


def to_script_tag(schema_dict):
    """
    Wrap a JSON-serializable dict in a JSON-LD <script> tag.
    """
    return (
        '<script type="application/ld+json">\n'
        + json.dumps(schema_dict, indent=2)
        + "\n</script>"
    )