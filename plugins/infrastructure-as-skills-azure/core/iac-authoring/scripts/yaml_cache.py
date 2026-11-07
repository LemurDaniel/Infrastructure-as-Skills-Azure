#!/usr/bin/env python3
"""Parsed YAML, cached as JSON by the hash of its text.

The checks read every question set and render-map on every run - 70-odd files, about 0.8 s of
building Python objects even through libyaml's C parser, and a test runner starts a check a
hundred times. The parsed document is written once as JSON under the user's cache directory,
keyed by the SHA-256 of the file's text: a changed file has another key, so nothing goes
stale, and nothing is executed on load (JSON, never pickle). A map with a key that is no
string - `true:` in plain_values, `3072:` - is stored as its pairs, `{"__pairs__": [[k, v]]}`, so
the key keeps its type; a document that still does not survive the round trip (a date) is not
cached and is parsed every time.

    data = yaml_cache.load(yaml, f)        # f: an open text file

IAS_YAML_CACHE=off parses every time; IAS_YAML_CACHE=<dir> moves the cache.
"""

#
#   Chapters:
#     LOAD   The cached document, or the parsed one written to the cache.
#

import hashlib
import json
import os

FORMAT = b'v2\0'  # part of the key: a change in how documents are stored drops the old entries
PAIRS = '__pairs__'


# ===========================================================================
# ===============================   LOAD   ==================================
# ===========================================================================
#
#   cache_dir   Where the entries live.
#   encode      A document with every map whose keys are not all strings as its pairs.
#   decode      The document back from that form.
#   load        The document of an open YAML file, from the cache where it is.
#

def cache_dir():
    """Returns the cache directory, None when caching is off.

    cache_dir()  => 'C:/Users/me/AppData/Local/infrastructure-as-skills-azure/yaml'
    """
    setting = os.environ.get('IAS_YAML_CACHE', '')
    if setting.lower() == 'off':
        return None
    if setting:
        return setting
    base = (os.environ.get('LOCALAPPDATA') or os.environ.get('XDG_CACHE_HOME')
            or os.path.join(os.path.expanduser('~'), '.cache'))
    return os.path.join(base, 'infrastructure-as-skills-azure', 'yaml')


def encode(node):
    """Returns the node with every map whose keys are not all strings written as its pairs.

    encode({True: 'on'})  => {'__pairs__': [[True, 'on']]}
    """
    if isinstance(node, dict):
        if all(isinstance(k, str) for k in node) and PAIRS not in node:
            return {k: encode(v) for k, v in node.items()}
        return {PAIRS: [[k, encode(v)] for k, v in node.items()]}
    if isinstance(node, list):
        return [encode(v) for v in node]
    return node


def decode(node):
    """Returns the document from its encoded form.

    decode({'__pairs__': [[True, 'on']]})  => {True: 'on'}
    """
    if isinstance(node, dict):
        if PAIRS in node and len(node) == 1:
            return {k: decode(v) for k, v in node[PAIRS]}
        return {k: decode(v) for k, v in node.items()}
    if isinstance(node, list):
        return [decode(v) for v in node]
    return node


def load(yaml, f):
    """Returns the document of an open YAML file, read from the cache where an entry exists.

    yaml  (Required) The PyYAML module the caller imported.
    f     (Required) An open text file.

    load(yaml, open('questions.yaml', encoding='utf-8'))  => {'schema_version': 1, ...}
    """
    text = f.read()
    loader = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
    folder = cache_dir()
    if folder is None:
        return yaml.load(text, Loader=loader)

    key = hashlib.sha256(FORMAT + text.encode('utf-8')).hexdigest()
    entry = os.path.join(folder, key + '.json')
    try:
        with open(entry, encoding='utf-8') as cached:
            return decode(json.load(cached))
    except (OSError, ValueError):
        pass

    data = yaml.load(text, Loader=loader)
    try:
        blob = json.dumps(encode(data), ensure_ascii=False)
        if decode(json.loads(blob)) != data:
            return data  # a key or value JSON would change: parsed every time instead
        os.makedirs(folder, exist_ok=True)
        part = f"{entry}.{os.getpid()}.part"
        with open(part, 'w', encoding='utf-8') as out:
            out.write(blob)
        os.replace(part, entry)  # atomic: a parallel run reads the whole entry or none
    except (TypeError, ValueError, OSError):
        pass
    return data
