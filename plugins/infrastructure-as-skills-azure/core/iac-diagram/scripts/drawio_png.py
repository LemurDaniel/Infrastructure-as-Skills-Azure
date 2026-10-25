"""Inspect, extract, repair and re-embed the draw.io XML inside a *.drawio.png.

Standard library only. export_diagram.py calls repair() and check() after every embedded
export: the draw.io desktop CLI (21.5.1) writes a bad zTXt CRC and no IEND chunk with
--embed-diagram, reproducibly. Browsers still show such a PNG; strict decoders, and
Claude's image reader, reject it.

    python3 -I drawio_png.py check   PNG [PNG ...]   # PNG structure + embedded XML + icon paths
    python3 -I drawio_png.py labels  FILE            # every cell label of a .drawio or .drawio.png
    python3 -I drawio_png.py extract PNG OUT.drawio
    python3 -I drawio_png.py repair  PNG             # bad CRCs, missing IEND; pixels and XML untouched
    python3 -I drawio_png.py embed   PNG IN.drawio   # swaps the XML only - pixels stay stale
    python3 -I drawio_png.py icons   [WORD ...]      # icon paths in draw.io's bundled library

Exit 0 ok, 1 problem found, 2 could not run (no draw.io for `icons`, no input).
"""
import argparse
import base64
import glob
import html
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import urllib.parse
import zlib

def _read(path, mode="rb", **kw):
    with open(path, mode, **kw) as f:
        return f.read()


def _write(path, data, mode="wb", **kw):
    with open(path, mode, **kw) as f:
        f.write(data)


SIG = b"\x89PNG\r\n\x1a\n"
IEND = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND"))


def chunks(data):
    """Yield (offset, type, payload, crc_ok, complete) tolerating truncated files."""
    i = 8
    while i + 8 <= len(data):
        n, t = struct.unpack(">I4s", data[i:i + 8])
        payload = data[i + 8:i + 8 + n]
        crc = data[i + 8 + n:i + 12 + n]
        complete = len(payload) == n and len(crc) == 4
        ok = complete and struct.unpack(">I", crc)[0] == zlib.crc32(t + payload)
        yield i, t, payload, ok, complete
        i += 12 + n
        if t == b"IEND":
            break


def inflate(raw):
    # draw.io writes zTXt with raw deflate (no zlib header); standard writers use zlib.
    for wbits in (15, -15):
        try:
            return zlib.decompress(raw, wbits)
        except zlib.error:
            pass
    raise ValueError("cannot inflate text chunk")


def text_value(t, payload):
    key, _, rest = payload.partition(b"\0")
    if t == b"tEXt":
        val = rest
    elif t == b"zTXt":
        val = inflate(rest[1:])
    else:  # iTXt
        flag, rest = rest[0], rest[2:]
        val = rest.split(b"\0", 2)[2]
        if flag:
            val = inflate(val)
    return key.decode("latin1"), urllib.parse.unquote(val.decode("utf-8", "replace"))


def get_xml(data):
    for _, t, p, _, complete in chunks(data):
        if t in (b"tEXt", b"zTXt", b"iTXt") and complete:
            key, val = text_value(t, p)
            if "<mxfile" in val or "<mxGraphModel" in val:
                return val
    return None


def graph_models(xml):
    """Return the uncompressed <mxGraphModel> of every page."""
    if "<mxfile" not in xml:
        return [xml]
    out = []
    for body in re.findall(r"<diagram[^>]*>(.*?)</diagram>", xml, re.S):
        if "<mxGraphModel" not in body:
            body = urllib.parse.unquote(zlib.decompress(base64.b64decode(body), -15).decode())
        out.append(body)
    return out


def labels(xml):
    res = []
    for model in graph_models(xml):
        for v in re.findall(r'value="([^"]*)"', model):
            v = re.sub(r"<[^>]+>", " ", html.unescape(v))
            v = re.sub(r"\s+", " ", html.unescape(v)).strip()
            if v:
                res.append(v)
    return res


def check(path):
    data = _read(path)
    problems = []
    if not data.startswith(SIG):
        problems.append("no PNG signature")
    last, w, h, idat = None, 0, 0, b""
    for off, t, p, ok, complete in chunks(data):
        if t == b"IHDR":
            w, h = struct.unpack(">II", p[:8])
        if t == b"IDAT":
            idat += p
        if not complete:
            problems.append(f"{t.decode('latin1')} truncated at {off}")
        elif not ok:
            problems.append(f"{t.decode('latin1')} bad CRC at {off}")
        last = t
    if last != b"IEND":
        problems.append("missing IEND")
    try:
        zlib.decompress(idat)
    except zlib.error as e:
        problems.append(f"image data: {e}")
    xml = None
    try:
        xml = get_xml(data)
    except Exception as e:  # noqa: BLE001
        problems.append(f"embedded XML unreadable: {e}")
    cells = sum(len(re.findall("<mxCell", m)) for m in graph_models(xml)) if xml else 0
    if xml is None and not any("XML" in p for p in problems):
        problems.append("no embedded draw.io XML")
    status = "OK " if not problems else "BAD"
    print(f"{status} {path}  {w}x{h}  {cells} cells" + ("" if not problems else "  -> " + "; ".join(problems)))
    for ic in (unknown_icons(xml) if xml else []):
        print(f"    warn: icon not in draw.io's bundled library (renders as a placeholder): {ic}")
    return not problems


def repair(path):
    data = _read(path)
    out = bytearray(SIG)
    fixed = []
    for off, t, p, ok, complete in chunks(data):
        if t == b"IEND":
            break
        if not complete:
            if t != b"IDAT":
                fixed.append(f"dropped truncated {t.decode('latin1')}")
                continue
            fixed.append("rebuilt truncated IDAT")
        elif not ok:
            fixed.append(f"recomputed CRC of {t.decode('latin1')}")
        out += struct.pack(">I", len(p)) + t + p + struct.pack(">I", zlib.crc32(t + p))
    out += IEND
    if out == data:
        print(f"unchanged {path}")
        return False
    _write(path, bytes(out))
    print(f"repaired {path}: " + ", ".join(fixed + ["IEND ok"]))
    return True


def embed(path, drawio):
    xml = _read(drawio, "r", encoding="utf-8")
    data = _read(path)
    payload = b"mxfile\0" + urllib.parse.quote(xml, safe="").encode("ascii")
    new_chunk = struct.pack(">I", len(payload)) + b"tEXt" + payload + struct.pack(">I", zlib.crc32(b"tEXt" + payload))
    out = bytearray(SIG)
    for _, t, p, _, _ in chunks(data):
        if t in (b"tEXt", b"zTXt", b"iTXt") and ("<mx" in text_value(t, p)[1]):
            continue
        out += struct.pack(">I", len(p)) + t + p + struct.pack(">I", zlib.crc32(t + p))
        if t == b"IHDR":
            out += new_chunk
    _write(path, bytes(out))
    print(f"embedded {drawio} into {path} (pixels unchanged - re-render via draw.io)")


# ------------------------------------------------------------------ draw.io installation

def find_drawio():
    """draw.io desktop: PATH first, then the default install locations."""
    cands = [shutil.which("drawio"), shutil.which("draw.io")]
    if os.environ.get("ProgramFiles"):
        cands.append(os.path.join(os.environ["ProgramFiles"], "draw.io", "draw.io.exe"))
    if os.environ.get("LOCALAPPDATA"):
        cands.append(os.path.join(os.environ["LOCALAPPDATA"], "Programs", "draw.io", "draw.io.exe"))
    cands += ["/Applications/draw.io.app/Contents/MacOS/draw.io", "/usr/bin/drawio", "/opt/drawio/drawio"]
    return next((c for c in cands if c and os.path.isfile(c)), None)


_ICONS = None


def bundled_icons():
    """Every img/lib/... file inside draw.io's app.asar (None if draw.io or the asar is not found).

    A wrong icon path does not fail an export - it silently renders a broken-image placeholder.
    """
    global _ICONS
    if _ICONS is not None:
        return _ICONS or None
    exe = find_drawio()
    asar = os.path.join(os.path.dirname(exe), "resources", "app.asar") if exe else None
    if not asar or not os.path.isfile(asar):
        _ICONS = set()
        return None
    with open(asar, "rb") as f:
        _, _, _, n = struct.unpack("<IIII", f.read(16))
        tree = json.loads(f.read(n))
    found = set()

    def walk(node, prefix):
        for name, child in node.get("files", {}).items():
            path = prefix + name
            if "files" in child:
                walk(child, path + "/")
            else:
                found.add(path)

    walk(tree, "")
    root = "drawio/src/main/webapp/"
    _ICONS = {p[len(root):] for p in found if p.startswith(root + "img/lib/")}
    return _ICONS


def unknown_icons(xml):
    icons = bundled_icons()
    if icons is None:
        return []
    refs = set()
    for model in graph_models(xml):
        refs |= set(re.findall(r"image=(img/lib/[^;\"]+)", html.unescape(model)))
    return sorted(r for r in refs if r not in icons)


def cmd_icons(words):
    icons = bundled_icons()
    if icons is None:
        print("draw.io desktop not found - cannot list icons")
        return 2
    words = [w.lower() for w in words]
    hits = sorted(i for i in icons if all(w in i.lower() for w in words))
    print("\n".join(hits[:200]) or "no match")
    if len(hits) > 200:
        print(f"... {len(hits) - 200} more - narrow the query")
    return 0


def read_xml(path):
    """The draw.io XML of a .drawio file or of a .drawio.png."""
    data = _read(path)
    if data.startswith(SIG):
        xml = get_xml(data)
        if xml is None:
            raise ValueError(f"{path}: no embedded draw.io XML")
        return xml
    return data.decode("utf-8")


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # labels carry ●, ä, → ; a Windows console is cp1252
    cmd, args = (argv[0], argv[1:]) if argv else ("", [])
    if cmd == "check" and args:
        return 0 if all([check(f) for f in args]) else 1
    if cmd == "labels" and args:
        print("\n".join(labels(read_xml(args[0]))))
    elif cmd == "extract" and len(args) == 2:
        _write(args[1], get_xml(_read(args[0])), "w", encoding="utf-8")
        print(f"wrote {args[1]}")
    elif cmd == "repair" and args:
        for f in args:
            if repair(f):
                check(f)
    elif cmd == "embed" and len(args) == 2:
        embed(args[0], args[1])
    elif cmd == "icons":
        return cmd_icons(args)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
