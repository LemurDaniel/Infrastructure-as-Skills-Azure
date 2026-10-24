#!/usr/bin/env python3
"""Exports an infra-diagram.drawio to infra-diagram.drawio.png with the diagram
embedded, so the PNG opens as an editable diagram in draw.io.

Uses the draw.io desktop CLI. Looks for it on PATH (drawio, draw.io), then in
the default install locations on Windows, macOS and Linux.

Clears ELECTRON_RUN_AS_NODE for the call. VS Code sets it for its own child
processes, and with it set draw.io starts as plain Node and rejects every
export flag as a "bad option".

An embedded export is repaired and checked afterwards: the draw.io desktop CLI writes
a bad zTXt CRC and no IEND chunk with --embed-diagram, every time. See drawio_png.py.

After a successful embedded export the .drawio is deleted: the PNG carries it, so one file is
delivered, not two. --keep leaves it.

Without draw.io the script exits 2 and leaves the .drawio file in place. That
file is the diagram; the PNG is a convenience, and a missing exporter is said
out loud rather than papered over.

Usage:
    python3 export_diagram.py ./infra-diagram.drawio
    python3 export_diagram.py ./infra-diagram.drawio --out ./preview.png --no-embed
    python3 export_diagram.py ./infra-diagram.drawio --scale 1 --border 10
    python3 export_diagram.py ./infra-diagram.drawio --keep

Exit 0 written, 1 export failed or the PNG is still bad after the repair, 2 could not export (no file, no draw.io).
"""

import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drawio_png  # noqa: E402

COLORS = {'green': '32', 'red': '31', 'yellow': '33'}
USE_COLOR = sys.stdout.isatty() and not os.environ.get('NO_COLOR')


def say(text, color=None):
    if color and USE_COLOR:
        print(f"\033[{COLORS[color]}m{text}\033[0m")
    else:
        print(text)


def find_drawio():
    candidates = [shutil.which('drawio'), shutil.which('draw.io')]
    if os.environ.get('ProgramFiles'):
        candidates.append(os.path.join(os.environ['ProgramFiles'], 'draw.io', 'draw.io.exe'))
    if os.environ.get('LOCALAPPDATA'):
        candidates.append(os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'draw.io', 'draw.io.exe'))
    candidates += [
        '/Applications/draw.io.app/Contents/MacOS/draw.io',
        '/usr/bin/drawio',
        '/opt/drawio/drawio',
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def main():
    ap = argparse.ArgumentParser(description='Export a .drawio file to a PNG with the diagram embedded.')
    ap.add_argument('path', help='the .drawio file to export')
    ap.add_argument('--out', help='the PNG to write (default: <path>.png, i.e. infra-diagram.drawio.png)')
    ap.add_argument('--no-embed', action='store_true',
                    help='write a plain PNG without the diagram inside - for a visual check only, never for the deliverable')
    ap.add_argument('--scale', type=int, default=2, help='export scale (default 2, legible when pasted into a document)')
    ap.add_argument('--border', type=int, default=20, help='border in px around the diagram (default 20)')
    ap.add_argument('--keep', action='store_true', help='keep the .drawio after an embedded export (it is deleted by default; the PNG carries it)')
    args = ap.parse_args()

    if not os.path.isfile(args.path):
        say(f"[skip] {args.path} not found.", 'yellow')
        return 2
    path = os.path.abspath(args.path)
    out = args.out or f"{path}.png"

    drawio = find_drawio()
    if not drawio:
        say('[skip] draw.io desktop not found - the .drawio file is the deliverable.', 'yellow')
        print('       Install it from https://www.drawio.com or open the file at app.diagrams.net.')
        return 2

    env = dict(os.environ)
    env.pop('ELECTRON_RUN_AS_NODE', None)
    # --embed-diagram keeps the XML inside the PNG.
    cmd = [drawio, '--export', '--format', 'png', '--scale', str(args.scale), '--border', str(args.border)]
    if not args.no_embed:
        cmd.append('--embed-diagram')
    cmd += ['--output', out, path]
    # The old PNG goes first: draw.io has exited 0 and left an existing file untouched (seen
    # 2026-10-24, the file open elsewhere), and an "ok" over a stale picture is the one result
    # the review loop cannot afford.
    if os.path.isfile(out):
        try:
            os.remove(out)
        except OSError as e:
            say(f"[fail] {out} cannot be replaced ({e.strerror}) - is it open in another program?", 'red')
            return 1
    try:
        proc = subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        code = proc.returncode
    except OSError as e:
        say(f"[fail] could not start draw.io: {e}", 'red')
        return 1

    if code != 0 or not os.path.isfile(out):
        say(f"[fail] draw.io exited {code}, no PNG written.", 'red')
        return 1

    if not args.no_embed:
        drawio_png.repair(out)
        if not drawio_png.check(out):
            say(f"[fail] {out} is still not a valid PNG with the diagram embedded.", 'red')
            return 1
        if not args.keep and os.path.abspath(out) != path:
            os.remove(path)
    say(f"[ ok ] {out}", 'green')
    return 0


if __name__ == '__main__':
    sys.exit(main())
