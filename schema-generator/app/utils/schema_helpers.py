import json

def clean_list(text: str):
    if not text:
        return []
    lines = [line.strip() for line in text.split("\n")]
    return [line for line in lines if line]


def to_script_tag(schema: dict) -> str:
    return (
        '<script type="application/ld+json">\n'
        f'{json.dumps(schema, ensure_ascii=False, indent=2)}\n'
        '</script>'
    )
