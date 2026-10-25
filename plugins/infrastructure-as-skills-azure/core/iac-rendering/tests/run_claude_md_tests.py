#!/usr/bin/env python3
"""Tests sync_claude_md.py: the section is written, replaced when older, and never
overwritten, downgraded or turned into a failure by what a repository already holds.

    python run_claude_md_tests.py
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_claude_md.py"
TEMPLATE = SCRIPT.parents[1] / "references" / "claude-md-block.md"
REV = int(re.search(r"begin rev=(\d+)", TEMPLATE.read_text(encoding="utf-8")).group(1))

END = "<!-- infrastructure-as-skills: end -->"


def section(rev_part, text="old text"):
    return f"<!-- infrastructure-as-skills: begin{rev_part} - regenerated -->\n{text}\n{END}"


def run(claude_md, *extra):
    """(exit code, output, CLAUDE.md after); claude_md None = no file"""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "CLAUDE.md"
        if claude_md is not None:
            f.write_text(claude_md, encoding="utf-8", newline="")
        p = subprocess.run([sys.executable, str(SCRIPT), d, "--root", "infra/", *extra],
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr, f.read_bytes().decode("utf-8") if f.exists() else None


def case(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL ") + name + ("" if ok else f"\n{detail}"))
    return ok


def main():
    mine = "# Customer\n\nTheir rules.\n"
    after = "\n## Later\n\nMore of theirs.\n"
    results = []

    code, out, text = run(None, "--write")
    results.append(case("no file: created with the section", code == 0 and f"rev={REV}" in text and "`infra/infra-spec.yaml`" in text, out))

    code, out, text = run(mine, "--write")
    results.append(case("no section: appended, the customer's text first and intact",
                        code == 0 and text.startswith(mine) and f"begin rev={REV}" in text, out))

    for label, marker in (("rev 0 (a 0.0.2 section without rev)", ""), (f"older rev", f" rev={max(REV - 1, 0)}")):
        if label == "older rev" and REV < 2:
            continue
        code, out, text = run(mine + section(marker) + after, "--write")
        results.append(case(f"{label}: replaced between the markers only",
                            code == 0 and "old text" not in text and text.startswith(mine) and text.endswith(after)
                            and f"begin rev={REV}" in text and text.count("infrastructure-as-skills: begin") == 1, out + (text or "")))

    code, out, text = run(mine + section(f" rev={REV}") + after, "--write")
    results.append(case("same rev: untouched", code == 0 and "old text" in text, out))

    code, out, text = run(mine + section(f" rev={REV + 5}") + after, "--write")
    results.append(case("newer rev: untouched, exit 0 (no downgrade)", code == 0 and "old text" in text and "newer" in out, out))

    stale = mine + section("") + after
    code, out, text = run(stale)
    results.append(case("report only: stale section is a message, exit 0, nothing written", code == 0 and text == stale, out))

    for label, broken in (("begin without end", "<!-- infrastructure-as-skills: begin rev=1 -->\nx\n"),
                          ("end before begin", END + "\n<!-- infrastructure-as-skills: begin rev=1 -->\n"),
                          ("two sections", section("") + "\n" + section(""))):
        code, out, text = run(mine + broken, "--write")
        results.append(case(f"damaged ({label}): untouched, exit 0", code == 0 and text == mine + broken, out))

    crlf = "# Customer\r\n\r\nTheirs.\r\n" + section("").replace("\n", "\r\n") + "\r\n"
    code, out, text = run(crlf, "--write")
    results.append(case("CRLF file stays CRLF", code == 0 and "\r\n" in text and "\n" not in text.replace("\r\n", ""), out))

    code, out, _ = run(None, "--verify-lock")
    results.append(case("lock matches the template", code == 0, out))

    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
