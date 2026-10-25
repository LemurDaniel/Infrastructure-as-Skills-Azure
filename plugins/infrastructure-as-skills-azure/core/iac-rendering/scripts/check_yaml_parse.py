#!/usr/bin/env python3
"""Checks that YAML files parse - the rendered pipeline files, before anything runs them.

    python check_yaml_parse.py <file> [<file> ...]

Exit 0 when every file parses, 1 when one does not, 2 without PyYAML or without files.
It reads the files and prints one line each; it changes nothing.
"""
import sys

try:
    import yaml
except ImportError:
    print("PyYAML is required: pip install pyyaml")
    sys.exit(2)


def main(paths):
    if not paths:
        print("usage: check_yaml_parse.py <file> [<file> ...]")
        return 2
    failed = 0
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                list(yaml.safe_load_all(handle))
            print(f"[ ok ] {path}")
        except (OSError, yaml.YAMLError) as error:
            failed += 1
            print(f"[fail] {path}: {str(error).splitlines()[0] if str(error) else error!r}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
