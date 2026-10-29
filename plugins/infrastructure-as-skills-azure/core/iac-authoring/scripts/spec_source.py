"""Reads a decision's `source`, shared by check_spec.py and export_decisions.py.

A source is a word (stated, asked, platform, pattern, deployment, default, carried,
assumed) or a map of one key that names the kind and where it points:

  {forced_by: <key or list>}         forced, by another answer
  {derived_from: deployment.<id>}    requirement, from a customer's answer
  {overridden: <reason>}             overridden, and why
"""

WORDS = ['stated', 'asked', 'platform', 'pattern', 'deployment', 'default', 'carried', 'assumed']
POINTERS = {'forced_by': 'forced', 'derived_from': 'requirement', 'overridden': 'overridden'}
KINDS = WORDS + list(POINTERS.values())


def kind(src):
    """(kind, pointer) of a source; kind None when it is neither a known word nor one known key."""
    if isinstance(src, str):
        return (src if src in WORDS else None), None
    if isinstance(src, dict) and len(src) == 1:
        (key, ref), = src.items()
        if key in POINTERS:
            return POINTERS[key], ref
    return None, None
