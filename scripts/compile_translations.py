"""Compile the Django catalogs without requiring system gettext.

Supports named contexts and plural entries used by the deployed catalogs.
Usage: python scripts/compile_translations.py
"""

import ast
import re
import struct
from pathlib import Path


def read_catalog(path):
    messages = {}
    entry = {}
    field = None
    fuzzy = False
    for line in [*path.read_text().splitlines(), ""]:
        if line.startswith("#, ") and "fuzzy" in line:
            fuzzy = True
        match = re.match(r'(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?) (".*")$', line)
        if match:
            field = match[1]
            entry[field] = ast.literal_eval(match[2])
        elif line.startswith('"') and field:
            entry[field] += ast.literal_eval(line)
        elif not line.strip():
            if "msgid" in entry and not fuzzy:
                key = entry["msgid"]
                if "msgctxt" in entry:
                    key = entry["msgctxt"] + "\x04" + key
                if "msgid_plural" in entry:
                    key += "\0" + entry["msgid_plural"]
                    count = len([name for name in entry if name.startswith("msgstr[")])
                    value = "\0".join(entry[f"msgstr[{index}]"] for index in range(count))
                else:
                    value = entry.get("msgstr", "")
                if value or not key:
                    messages[key] = value
            entry, field, fuzzy = {}, None, False
    return messages


def compile_catalog(path):
    messages = read_catalog(path)
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
    for catalog in Path(__file__).resolve().parent.parent.glob("locale/*/LC_MESSAGES/*.po"):
        compile_catalog(catalog)
        print(f"Compiled {catalog.relative_to(Path(__file__).resolve().parent.parent)}")
