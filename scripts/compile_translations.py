"""Compile the checked-in Django catalogs without requiring system gettext.

Usage: python scripts/compile_translations.py
The catalogs use singular messages; plural UI text uses explicit counts.
"""

import ast
import struct
from pathlib import Path


def compile_catalog(path):
    messages = {}
    key = value = ""
    field = None
    for line in [*path.read_text().splitlines(), ""]:
        if line.startswith("msgid "):
            key = ast.literal_eval(line[6:])
            field = "key"
        elif line.startswith("msgstr "):
            value = ast.literal_eval(line[7:])
            field = "value"
        elif line.startswith('"'):
            if field == "key":
                key += ast.literal_eval(line)
            elif field == "value":
                value += ast.literal_eval(line)
        elif not line.strip() and field:
            messages[key] = value
            key = value = ""
            field = None
    pairs = sorted((key.encode(), value.encode()) for key, value in messages.items())
    count = len(pairs)
    keys = b"\0".join(key for key, _ in pairs) + b"\0"
    values = b"\0".join(value for _, value in pairs) + b"\0"
    key_offset = 28 + count * 16
    value_offset = key_offset + len(keys)
    key_table, value_table = [], []
    for key, value in pairs:
        key_table.extend((len(key), key_offset))
        value_table.extend((len(value), value_offset))
        key_offset += len(key) + 1
        value_offset += len(value) + 1
    header = [0x950412DE, 0, count, 28, 28 + count * 8, 0, 0]
    numbers = header + key_table + value_table
    path.with_suffix(".mo").write_bytes(
        struct.pack("<" + "I" * len(numbers), *numbers) + keys + values
    )


if __name__ == "__main__":
    for catalog in Path(__file__).resolve().parent.parent.glob("locale/*/LC_MESSAGES/django.po"):
        compile_catalog(catalog)
        print(f"Compiled {catalog.relative_to(Path(__file__).resolve().parent.parent)}")
