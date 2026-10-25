#!/usr/bin/env python3
"""Keeps the plugin's section in a repository's CLAUDE.md current.

The section is references/claude-md-block.md, between two markers; the begin marker
carries `rev=<n>`, bumped whenever the text changes. Only the part between the markers is
ever touched - the rest of the file is the customer's.

    python sync_claude_md.py <repo-root> [--root infra/] [--write]
    python sync_claude_md.py --verify-lock      # plugin repo: text changed without a new rev

Without --write it only reports. It never fails a run over the state of the section: a
missing, older, newer or damaged section is a message, exit 0. A section with a higher rev
than this plugin knows was written by a newer plugin and is left alone - a downgrade must
not overwrite it. Exit 1 only for --verify-lock, which is the plugin repo's own check.
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

REFS = Path(__file__).resolve().parents[1] / "references"
TEMPLATE = REFS / "claude-md-block.md"
LOCK = REFS / "claude-md-block.lock"

BEGIN = re.compile(r"^<!-- infrastructure-as-skills: begin\b[^\n]*-->[ \t]*$", re.M)
END = re.compile(r"^<!-- infrastructure-as-skills: end\b[^\n]*-->[ \t]*$", re.M)
REV = re.compile(r"\brev=(\d+)\b")


def read(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def template():
    """(rev, body without the marker lines, whole block)"""
    text = read(TEMPLATE).strip("\n")
    b, e = BEGIN.search(text), END.search(text)
    if not b or not e:
        sys.exit(f"{TEMPLATE} has no begin/end markers")
    m = REV.search(b.group(0))
    if not m:
        sys.exit(f"{TEMPLATE}: the begin marker carries no rev=<n>")
    return int(m.group(1)), text[b.end():e.start()].strip("\n"), text


def body_hash(body):
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def verify_lock():
    rev, body, _ = template()
    now = f"rev={rev} sha256={body_hash(body)}"
    locked = read(LOCK).strip() if LOCK.is_file() else ""
    if locked == now:
        print(f"claude-md-block: {now}")
        return 0
    m = re.match(r"rev=(\d+) ", locked)
    if m and int(m.group(1)) == rev:
        print(f"The text of references/claude-md-block.md changed but rev={rev} did not: bump rev "
              f"in the begin marker, then run --verify-lock again for the line {LOCK.name} needs.")
    else:
        print(f"{LOCK.name} is stale: write `{now}` into it.")
    return 1


def section_of(text):
    """(start, end, rev) of the plugin's section in a CLAUDE.md, None when there is none,
    'broken' when a marker is missing or the end comes first."""
    b, e = BEGIN.search(text), END.search(text)
    if not b and not e:
        return None
    if not b or not e or e.start() < b.start() or len(BEGIN.findall(text)) > 1:
        return "broken"
    m = REV.search(b.group(0))
    return b.start(), e.end(), int(m.group(1)) if m else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", help="repository root holding (or getting) CLAUDE.md")
    ap.add_argument("--root", default=".", help="the IaC root relative to the repository root (infra/ or .)")
    ap.add_argument("--write", action="store_true", help="create or update the section")
    ap.add_argument("--verify-lock", action="store_true", help="plugin repo: the lock matches the template")
    args = ap.parse_args()

    if args.verify_lock:
        return verify_lock()
    if not args.repo:
        ap.error("repo is required")

    rev, _, block = template()
    root = args.root.strip().replace("\\", "/").rstrip("/") or "."
    block = block.replace("<root>", root)
    target = Path(args.repo) / "CLAUDE.md"
    text = read(target) if target.is_file() else ""
    found = section_of(text) if text else None

    if found == "broken":
        print("CLAUDE.md: the plugin's markers are damaged (one missing, reversed or doubled) - "
              "left untouched, fix by hand.")
        return 0
    if found is None:
        if not args.write:
            print(f"CLAUDE.md: no plugin section; the next render writes rev={rev}.")
            return 0
        new = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block + "\n"
        action = "created" if not text else "appended"
    else:
        start, end, have = found
        if have > rev:
            print(f"CLAUDE.md: section rev={have} is newer than this plugin's rev={rev} - left untouched.")
            return 0
        if have == rev:
            print(f"CLAUDE.md: section is current (rev={rev}).")
            return 0
        if not args.write:
            print(f"CLAUDE.md: section rev={have or 'none'}, plugin has rev={rev}; "
                  "the next run replaces it.")
            return 0
        new = text[:start] + block + text[end:]
        action = f"replaced rev={have or 'none'} with rev={rev}"

    crlf = target.is_file() and b"\r\n" in target.read_bytes()
    target.write_text(new.replace("\n", "\r\n") if crlf else new, encoding="utf-8", newline="")
    print(f"CLAUDE.md: section {action} (rev={rev}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
