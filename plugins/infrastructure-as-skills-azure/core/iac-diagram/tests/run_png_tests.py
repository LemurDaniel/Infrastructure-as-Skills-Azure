#!/usr/bin/env python3
"""Tests for the PNG and verification tooling of iac-diagram: drawio_png.py, verify_diagram.py,
export_diagram.py. Needs no draw.io except for the icon-path case, which is skipped without it.

    python3 run_png_tests.py

Exit 0 all passed, 1 a check failed, 2 could not run.
"""

import os
import struct
import subprocess
import sys
import tempfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, '..', 'scripts')
sys.path.insert(0, SCRIPTS)
import drawio_png as dp  # noqa: E402

FIXTURES = os.path.join(HERE, 'fixtures')
XML = ('<mxfile><diagram id="d"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
       '<mxCell id="title" value="Architektur" vertex="1" parent="1"/></root></mxGraphModel></diagram></mxfile>')


def chunk(t, p, crc=None):
    return struct.pack('>I', len(p)) + t + p + struct.pack('>I', zlib.crc32(t + p) if crc is None else crc)


def make_png(broken):
    """A 1x1 PNG with the diagram in a zTXt chunk written as raw deflate, like draw.io does.
    broken: the CRC of the zTXt chunk is wrong and IEND is missing - what the CLI produces."""
    import urllib.parse
    co = zlib.compressobj(wbits=-15)
    z = b'mxfile\0\0' + co.compress(urllib.parse.quote(XML, safe='').encode()) + co.flush()
    ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b'\0\xff\xff\xff')
    out = dp.SIG + chunk(b'IHDR', ihdr) + chunk(b'zTXt', z, 0xDEADBEEF if broken else None) + chunk(b'IDAT', idat)
    return out if broken else out + dp.IEND


def run(*argv):
    return subprocess.run([sys.executable, '-I', *argv], capture_output=True, text=True, encoding='utf-8',
                          env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})


def case_check_names_the_draw_io_bug(tmp):
    p = os.path.join(tmp, 'a.drawio.png')
    open(p, 'wb').write(make_png(True))
    r = run(os.path.join(SCRIPTS, 'drawio_png.py'), 'check', p)
    bad = []
    if r.returncode != 1 or 'zTXt bad CRC' not in r.stdout or 'missing IEND' not in r.stdout:
        bad.append(f"check did not name both faults: {r.stdout!r}")
    return bad


def case_repair_is_lossless(tmp):
    p = os.path.join(tmp, 'b.drawio.png')
    open(p, 'wb').write(make_png(True))
    before = dp.get_xml(open(p, 'rb').read())
    run(os.path.join(SCRIPTS, 'drawio_png.py'), 'repair', p)
    data = open(p, 'rb').read()
    bad = []
    if not dp.check(p):
        bad.append('still bad after repair')
    if dp.get_xml(data) != before or 'value="Architektur"' not in before:
        bad.append('the embedded XML changed or was unreadable')
    if not data.endswith(dp.IEND):
        bad.append('no IEND')
    return bad


def case_extract_embed_roundtrip(tmp):
    p = os.path.join(tmp, 'c.drawio.png')
    x = os.path.join(tmp, 'c.drawio')
    open(p, 'wb').write(make_png(False))
    run(os.path.join(SCRIPTS, 'drawio_png.py'), 'extract', p, x)
    open(x, 'w', encoding='utf-8').write(XML.replace('Architektur', 'Geändert'))
    run(os.path.join(SCRIPTS, 'drawio_png.py'), 'embed', p, x)
    r = run(os.path.join(SCRIPTS, 'drawio_png.py'), 'labels', p)
    return [] if r.stdout.strip() == 'Geändert' else [f"labels after embed: {r.stdout!r}"]


def case_export_without_file_is_exit_2(tmp):
    r = run(os.path.join(SCRIPTS, 'export_diagram.py'), os.path.join(tmp, 'missing.drawio'))
    return [] if r.returncode == 2 else [f"exit {r.returncode}, expected 2"]


def case_verify_catches_a_missing_resource(tmp):
    spec = os.path.join(FIXTURES, 'ten-resources.yaml')
    d = os.path.join(tmp, 'd.drawio')
    if run(os.path.join(SCRIPTS, 'new_diagram.py'), spec, '--language', 'de', '--out', d).returncode != 0:
        return ['new_diagram.py failed']
    bad = []
    ok = run(os.path.join(SCRIPTS, 'verify_diagram.py'), spec, d, '--language', 'de')
    if ok.returncode != 0:
        bad.append(f"a fresh diagram does not verify: {ok.stdout}")
    xml = open(d, encoding='utf-8').read().replace('id="res-key-vault"', 'id="res-gone"')
    open(d, 'w', encoding='utf-8').write(xml)
    r = run(os.path.join(SCRIPTS, 'verify_diagram.py'), spec, d)
    if r.returncode != 1 or "'key-vault' is in the spec but not drawn" not in r.stdout or "'gone' is drawn" not in r.stdout:
        bad.append(f"a renamed resource was not caught: {r.stdout!r}")
    return bad


def case_verify_catches_transliterated_umlauts(tmp):
    spec = os.path.join(FIXTURES, 'ten-resources.yaml')
    d = os.path.join(tmp, 'e.drawio')
    run(os.path.join(SCRIPTS, 'new_diagram.py'), spec, '--language', 'de', '--out', d)
    xml = open(d, encoding='utf-8').read().replace('Architektur', 'Architektur ueber oeffentlich', 1)
    open(d, 'w', encoding='utf-8').write(xml)
    r = run(os.path.join(SCRIPTS, 'verify_diagram.py'), spec, d, '--language', 'de')
    return [] if r.returncode == 1 and 'transliterated' in r.stdout else [f"not caught: {r.stdout!r}"]


def case_export_delivers_one_file(tmp):
    """The export leaves the PNG alone - the .drawio is deleted, --keep leaves it."""
    import shutil
    sys.path.insert(0, SCRIPTS)
    import export_diagram
    if not export_diagram.find_drawio():
        print('       (draw.io not installed - export not exercised)')
        return []
    spec = os.path.join(FIXTURES, 'ten-resources.yaml')
    bad = []
    for keep in (False, True):
        d = os.path.join(tmp, 'k' if keep else 'n', 'infra-diagram.drawio')
        os.makedirs(os.path.dirname(d))
        run(os.path.join(SCRIPTS, 'new_diagram.py'), spec, '--out', d)
        r = run(os.path.join(SCRIPTS, 'export_diagram.py'), d, '--scale', '1', *(['--keep'] if keep else []))
        if r.returncode != 0 or not dp.check(d + '.png'):
            bad.append(f"export failed (keep={keep}): {r.stdout}")
        elif os.path.exists(d) != keep:
            bad.append(f"keep={keep}: the .drawio {'was deleted' if keep else 'is still there'}")
    return bad


def case_icon_table_is_in_the_library(tmp):
    """Every path in ICONS must exist in draw.io's bundled library - else it exports a placeholder."""
    if dp.bundled_icons() is None:
        print('       (draw.io not installed - icon paths not verified)')
        return []
    import re
    src = open(os.path.join(SCRIPTS, 'new_diagram.py'), encoding='utf-8').read()
    paths = set(re.findall(r"'(img/lib/[^']+)'", src))
    return [f"not in the library: {p}" for p in sorted(paths - dp.bundled_icons())]


def case_every_question_set_has_an_icon(tmp):
    """Every resource with a question set has an icon, or is a child on its parent's label - a
    resource with neither is drawn as a bare box, and nothing else notices."""
    import glob
    import new_diagram as nd
    # A role assignment is a line on its target's label, never a shape of its own.
    not_drawn = {'role-assignment'}
    keys = {os.path.basename(os.path.dirname(p))
            for p in glob.glob(os.path.join(nd.PLUGIN_RESOURCES, '*', '*', 'questions.yaml'))}
    return [f"no icon and not a child: {k} - add it to ICONS (drawio_png.py icons <word>)"
            for k in sorted(keys - set(nd.ICONS) - set(nd.CHILD_KINDS) - not_drawn)]


CASES = [
    ('check names the draw.io bug', case_check_names_the_draw_io_bug),
    ('repair is lossless', case_repair_is_lossless),
    ('extract / embed round trip', case_extract_embed_roundtrip),
    ('export without a file exits 2', case_export_without_file_is_exit_2),
    ('verify catches a missing resource', case_verify_catches_a_missing_resource),
    ('verify catches transliterated umlauts', case_verify_catches_transliterated_umlauts),
    ('export delivers one file', case_export_delivers_one_file),
    ('icon table is in the library', case_icon_table_is_in_the_library),
    ('every question set has an icon', case_every_question_set_has_an_icon),
]


def main():
    try:
        import yaml  # noqa: F401
    except ImportError:
        print('[skip] no YAML parser - pip install pyyaml')
        return 2
    failed = 0
    for name, fn in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            problems = fn(tmp)
        if problems:
            failed += 1
            print(f"[FAIL] {name}")
            for p in problems:
                print(f"         - {p}")
        else:
            print(f"[ ok ] {name}")
    print('-' * 70)
    print(f"{failed} case(s) failed." if failed else 'All PNG and verification cases passed.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
