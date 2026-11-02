"""Reads what an import (iac-unclick) leaves in a spec, shared by check_spec.py and the render.

A spec written from what already runs in Azure carries three things an interview's does not
(references/spec.md, "Imported resources"):

  spec.imported_from                      where it was read: scopes, tag filter, when
  resources.<key>.adopt.{id, lock_id, diagnostic_setting_id, parts}
                                          the resource exists; each a stage map of ids the
                                          render imports instead of creating a second one -
                                          parts a list per stage, of the types the set's
                                          render-map.yaml lists under import_parts
  wiring.role_assignments[].adopt_id      the same for one role assignment
  unmapped: [{type, id, reason, note?}]   found, not rendered - said out loud, never dropped

An id is checked for its form and its type, not looked up: the check never reads Azure.
"""

import datetime
import re

GUID = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
SCOPE = re.compile(rf'^/subscriptions/{GUID}(/resourceGroups/[^/]+)?$', re.IGNORECASE)
RESOURCE_ID = re.compile(rf'^/subscriptions/{GUID}/resourceGroups/[^/]+/providers/[^/]+/[^/]+/[^/]+(/[^/]+/[^/]+)*$',
                         re.IGNORECASE)
ROLE_ASSIGNMENT_ID = re.compile(rf'^(/subscriptions/{GUID}(/resourceGroups/[^/]+(/providers/.+)?)?)?'
                                rf'/providers/Microsoft\.Authorization/roleAssignments/{GUID}$', re.IGNORECASE)
TIMESTAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$')

# The keys of the adopt group, and for the two children the extension path below the resource.
# `parts` holds the other resources the set renders (a plan, a private endpoint), a list per stage.
ADOPT_KEYS = {
    'id': None,
    'lock_id': 'Microsoft.Authorization/locks',
    'diagnostic_setting_id': 'Microsoft.Insights/diagnosticSettings',
    'parts': None,
}
# Who may have put an id there: the import, or a person naming it.
ADOPT_SOURCES = ('imported', 'stated', 'asked')
UNMAPPED_REASONS = ('no_question_set', 'outside_lock_policy', 'destination_not_supported', 'scope_not_adopted',
                    'not_readable')
UNMAPPED_KEYS = ('type', 'id', 'reason', 'note')


def resource_type(rid):
    """Microsoft.Storage/storageAccounts for a resource's id (child types joined), None otherwise.
    An extension resource (a lock, a diagnostic setting) reads as its own type, after the last
    /providers/."""
    if not isinstance(rid, str):
        return None
    low = rid.lower()
    at = low.rfind('/providers/')
    if at < 0:
        return None
    tail = rid[at + len('/providers/'):].split('/')
    if len(tail) < 3 or len(tail) % 2 == 0:
        return None
    return '/'.join([tail[0]] + tail[1::2])


def stage_values(v, environments):
    """[(stage, value)] of a stage map; None when v is not one."""
    if isinstance(v, dict) and v and all(k in environments for k in v):
        return list(v.items())
    return None


def check(spec, set_types, set_parts, environments, source_kind):
    """(errors, warnings, adopted count) for the import parts of a spec. set_types: set name -> the
    ARM type of its question set's `resource`; set_parts: set name -> its render-map.yaml's
    import_parts; source_kind: spec_source.kind."""
    errors, warnings = [], []
    get = lambda m, k: m.get(k) if isinstance(m, dict) else None

    # --- where it was read ----------------------------------------------------------------
    src = get(get(spec, 'spec'), 'imported_from')
    if src is not None:
        if not isinstance(src, dict):
            errors.append("spec.imported_from is not a map of scopes, tag_filter and read_at")
        else:
            extra = sorted(set(src) - {'scopes', 'tag_filter', 'read_at'})
            if extra:
                errors.append(f"spec.imported_from holds {', '.join(extra)} - only scopes, tag_filter and read_at")
            scopes = src.get('scopes')
            if not isinstance(scopes, list) or not scopes:
                errors.append("spec.imported_from.scopes is not a list of the subscriptions or resource groups read")
            else:
                for s in scopes:
                    if not isinstance(s, str) or not SCOPE.match(s):
                        errors.append(f"spec.imported_from.scopes has '{s}', which is no subscription or resource group id")
            if 'tag_filter' in src and not isinstance(src['tag_filter'], dict):
                errors.append("spec.imported_from.tag_filter is not a map of tag name to value")
            read_at = src.get('read_at')  # YAML reads an unquoted one as a datetime
            if not (isinstance(read_at, datetime.datetime) or TIMESTAMP.match(str(read_at or ''))):
                errors.append("spec.imported_from.read_at is not a UTC time (2026-11-01T09:58:12Z) - when Azure was read")

    # --- adopted resources ----------------------------------------------------------------
    adopted = 0
    for rkey, rnode in (get(spec, 'resources') or {}).items():
        adopt = get(rnode, 'adopt')
        if adopt is None:
            continue
        where = f"resources.{rkey}.adopt"
        if not isinstance(adopt, dict):
            errors.append(f"{where} is not a group of {', '.join(ADOPT_KEYS)}")
            continue
        extra = sorted(set(adopt) - set(ADOPT_KEYS))
        if extra:
            errors.append(f"{where} holds {', '.join(extra)} - only {', '.join(ADOPT_KEYS)}")
        if 'id' not in adopt:
            errors.append(f"{where} has no id - its lock, diagnostic setting and parts belong to an adopted resource")
            continue
        adopted += 1
        ids = {}
        for key, ext in ADOPT_KEYS.items():
            d = adopt.get(key)
            if d is None:
                continue
            if not isinstance(d, dict) or 'value' not in d:
                errors.append(f"{where}.{key} is not {{ value, source }}")
                continue
            kind, _ = source_kind(d.get('source'))
            if kind not in ADOPT_SOURCES:
                errors.append(f"{where}.{key} is {kind or d.get('source')!r} - an id is read from Azure or named by a "
                              f"person ({', '.join(ADOPT_SOURCES)}), never defaulted or assumed")
            staged = stage_values(d['value'], environments)
            if staged is None:
                errors.append(f"{where}.{key} is not a map keyed by stage - an id differs per stage like any value "
                              f"outside the spec")
                continue
            for e in [e for e in environments if e not in d['value']]:
                errors.append(f"{where}.{key} has no id for stage '{e}'")
            if key == 'parts':
                kind = str(rkey).split('__')[0]
                allowed = set_parts.get(kind) or []
                for stage, part_ids in staged:
                    if not isinstance(part_ids, list) or not part_ids:
                        errors.append(f"{where}.parts (stage {stage}) is not a list of ids")
                        continue
                    for rid in part_ids:
                        t = resource_type(rid) if isinstance(rid, str) and RESOURCE_ID.match(rid) else None
                        if t is None:
                            errors.append(f"{where}.parts (stage {stage}) has '{rid}', which is no resource id")
                        elif t.lower() not in {a.lower() for a in allowed}:
                            errors.append(f"{where}.parts (stage {stage}) has a {t}, which the {kind} set does not "
                                          f"render (import_parts: {', '.join(allowed) or 'none'})")
                continue
            for stage, rid in staged:
                if key == 'id':
                    ids[stage] = rid
                    want = set_types.get(str(rkey).split('__')[0])
                    if not isinstance(rid, str) or not RESOURCE_ID.match(rid):
                        errors.append(f"{where}.id (stage {stage}) is '{rid}', which is no resource id")
                    elif want and (resource_type(rid) or '').lower() != want.lower():
                        errors.append(f"{where}.id (stage {stage}) is a {resource_type(rid)}, but the {rkey.split('__')[0]} "
                                      f"set creates a {want}")
                    continue
                parent = ids.get(stage)
                prefix = f"{parent}/providers/{ext}/".lower() if isinstance(parent, str) else None
                if not isinstance(rid, str) or not prefix or not rid.lower().startswith(prefix) or '/' in rid[len(prefix):]:
                    errors.append(f"{where}.{key} (stage {stage}) is '{rid}', which is no {ext} of the adopted "
                                  f"resource ({parent}/providers/{ext}/<name>)")

    # --- adopted role assignments ---------------------------------------------------------
    ra = get(get(spec, 'wiring'), 'role_assignments')
    for i, a in enumerate((ra.get('value') or []) if isinstance(ra, dict) and isinstance(ra.get('value'), list) else []):
        if not isinstance(a, dict) or 'adopt_id' not in a:
            continue
        where = f"wiring.role_assignments[{i}] ({a.get('from')} -> {a.get('to')})"
        staged = stage_values(a['adopt_id'], environments)
        if staged is None:
            errors.append(f"{where}.adopt_id is not a map keyed by stage")
            continue
        for stage, rid in staged:
            if not isinstance(rid, str) or not ROLE_ASSIGNMENT_ID.match(rid):
                errors.append(f"{where}.adopt_id (stage {stage}) is '{rid}', which is no role assignment id "
                              f"(<scope>/providers/Microsoft.Authorization/roleAssignments/<guid>)")

    # --- found, not rendered --------------------------------------------------------------
    unmapped = get(spec, 'unmapped')
    if unmapped is not None:
        if not isinstance(unmapped, list):
            errors.append("unmapped is not a list of { type, id, reason }")
            unmapped = []
        for i, u in enumerate(unmapped):
            if not isinstance(u, dict):
                errors.append(f"unmapped[{i}] is not {{ type, id, reason }}")
                continue
            extra = sorted(set(u) - set(UNMAPPED_KEYS))
            if extra:
                errors.append(f"unmapped[{i}] holds {', '.join(extra)} - only {', '.join(UNMAPPED_KEYS)}")
            t, rid, reason = u.get('type'), u.get('id'), u.get('reason')
            if not isinstance(t, str) or '/' not in t:
                errors.append(f"unmapped[{i}] has no type (Microsoft.Databricks/workspaces)")
            elif (resource_type(rid) or '').lower() != t.lower():
                errors.append(f"unmapped[{i}] ({t}) has id '{rid}', which is no {t}")
            if reason not in UNMAPPED_REASONS:
                errors.append(f"unmapped[{i}] ({t}) has reason '{reason}', not one of {', '.join(UNMAPPED_REASONS)}")
        if unmapped:
            warnings.append(f"{len(unmapped)} unmapped item(s) - found in Azure and not rendered: "
                            + ', '.join(sorted({str(u.get('type')) for u in unmapped if isinstance(u, dict)})))
    return errors, warnings, adopted
