#!/usr/bin/env python3
"""Fails unless the version in plugin.json is newer than every released one.

A merge to master publishes the version in plugin.json as a release, so a pull
request must raise it: past the last v* tag and past the version on the base
branch. The pull request workflow runs this; run it locally before opening one.

Usage: check_version_bump.py [--base <ref>]   (default: origin/master)
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MANIFEST = "plugins/infrastructure-as-skills-azure/.claude-plugin/plugin.json"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")


def key(version):
    match = SEMVER.match(version)
    if not match:
        return None
    major, minor, patch, suffix = match.groups()
    # A suffixed version precedes its release: 1.0.0-rc1 < 1.0.0.
    return (int(major), int(minor), int(patch), suffix is None, suffix or "")


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="origin/master")
    args = parser.parse_args()

    version = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))["version"]
    if key(version) is None:
        print(f"error: plugin.json version {version!r} is not <major>.<minor>.<patch>[-suffix]")
        return 1

    released = []
    for tag in (git("tag", "--list", "v*") or "").split():
        if key(tag[1:]):
            released.append((tag[1:], f"tag {tag}"))
    base = git("show", f"{args.base}:{MANIFEST}")
    if base is None:
        print(f"warning: {args.base} not found, compared against the tags only")
    else:
        released.append((json.loads(base)["version"], args.base))

    if not released:
        print(f"ok: {version}, nothing released yet")
        return 0
    newest, where = max(released, key=lambda item: key(item[0]))
    if key(version) <= key(newest):
        print(f"error: plugin.json version {version} is not newer than {newest} ({where}); "
              "a merge to master releases, raise the version in this branch")
        return 1
    print(f"ok: {version} > {newest} ({where})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
