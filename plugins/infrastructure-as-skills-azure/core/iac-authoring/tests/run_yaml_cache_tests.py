#!/usr/bin/env python3
"""Tests scripts/yaml_cache.py: a cached document is the parsed one, and nothing goes stale.

    python run_yaml_cache_tests.py

A document with a boolean and an integer key (as `plain_values` and `key_size` carry) comes
back from the cache with those keys intact; a second load reads the entry and returns the same
document; a changed text gets its own entry; a document JSON cannot hold (a date) is returned
parsed and never cached; IAS_YAML_CACHE=off writes nothing; and every question set of the
plugin loads from the cache exactly as PyYAML parses it.
"""

#
#   Chapters:
#     CHECK THE CACHE   Round trip, reuse, a changed text, a date, off, the plugin's sets.
#

import io
import os
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import yaml_cache  # noqa: E402

PLUGIN = HERE.parents[2]
DOC = "plain_values:\n  true: on\n  false: off\nkey_size:\n  3072: default\nname: x\n"


# ===========================================================================
# ==========================   CHECK THE CACHE   ============================
# ===========================================================================

def main():
    failures = []

    def expect(ok, what):
        if not ok:
            failures.append(what)

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["IAS_YAML_CACHE"] = tmp
        parsed = yaml.safe_load(DOC)
        first = yaml_cache.load(yaml, io.StringIO(DOC))
        entries = os.listdir(tmp)
        second = yaml_cache.load(yaml, io.StringIO(DOC))
        expect(first == parsed and second == parsed, "a cached document differs from the parsed one")
        expect(True in second["plain_values"] and 3072 in second["key_size"], "a boolean or integer key lost its type")
        expect(len(entries) == 1, f"one document, {len(entries)} entries")

        yaml_cache.load(yaml, io.StringIO(DOC + "extra: 1\n"))
        expect(len(os.listdir(tmp)) == 2, "a changed text did not get its own entry")

        dated = yaml_cache.load(yaml, io.StringIO("at: 2026-11-07\n"))
        expect(str(dated["at"]) == "2026-11-07" and len(os.listdir(tmp)) == 2, "a date was cached or changed")

        sets = sorted((PLUGIN / "resources").glob("*/*/questions.yaml")) + [HERE.parent / "questions" / "deployment.yaml"]
        for path in sets:
            text = path.read_text(encoding="utf-8")
            yaml_cache.load(yaml, io.StringIO(text))
            if yaml_cache.load(yaml, io.StringIO(text)) != yaml.safe_load(text):
                failures.append(f"{path.parent.name}: the cached set differs from the parsed one")

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["IAS_YAML_CACHE"] = "off"
        expect(yaml_cache.load(yaml, io.StringIO(DOC)) == yaml.safe_load(DOC) and not os.listdir(tmp),
               "IAS_YAML_CACHE=off did not parse directly")

    for f in failures:
        print(f"[fail] {f}")
    print(f"{len(sets)} set(s) through the cache, {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
