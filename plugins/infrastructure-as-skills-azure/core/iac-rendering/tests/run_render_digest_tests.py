#!/usr/bin/env python3
"""Tests for scripts/render_digest.py: the digest drops nothing a render acts on and sends a
run only to the lines that apply.

On tests/fixtures/render-digest.yaml (Terraform, AVM, per-family, GitHub):
  - every decision is printed under its key path, the one a test asserts, with the attribute
    and the literal its render-map.yaml gives the target (per stage for a stage map); the assumed
    value and the open entry are listed;
  - the reading list holds the Terraform idiom and the GitHub pipeline file and neither the
    Bicep idiom nor another platform's file; naming.md without its Bicep section;
  - an AVM resource reads its reference up to `## Authored rendering`, an authored one from
    there, and the AVM coordinate comes from the reference;
  - --target bicep uses the bicep_avm entry, quotes for Bicep and reads the Bicep idiom.
On tests/fixtures/render-digest-shapes.yaml: a literal composed from three answers per stage,
its pieces pointing at it, an entry picked by the resource's kind (and another kind picking
another), a format of code written unquoted. Then a `{group.question}` in a values expr, a list
answer in a format of code and a null in values, through render_lines directly.
Across the plugin: every heading SKIPS names exists in its file (a renamed heading fails here,
not as a silently longer reading), and every resource's rendering reference with an AVM part
has the `## Authored rendering` heading the split depends on. A resource kind without a question set
exits 1, a spec that cannot be read exits 2.

Usage:
    python3 run_render_digest_tests.py

Needs PyYAML. Exit 0 all pass, 1 a test failed, 2 could not run.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'scripts', 'render_digest.py')
FIXTURE = os.path.join(HERE, 'fixtures', 'render-digest.yaml')
SHAPES = os.path.join(HERE, 'fixtures', 'render-digest-shapes.yaml')
sys.path.insert(0, os.path.join(HERE, '..', 'scripts'))


def run(*args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, encoding='utf-8')


def main():
    try:
        import yaml
    except ImportError:
        print('[fail] no YAML parser available - pip install pyyaml')
        return 2
    import render_digest as d

    failures = []

    def expect(cond, what):
        if not cond:
            failures.append(what)

    r = run(FIXTURE)
    out = r.stdout
    expect(r.returncode == 0, f"fixture exited {r.returncode}: {r.stderr.strip()}")

    with open(FIXTURE, encoding='utf-8') as f:
        spec = yaml.safe_load(f)
    for key, node in spec['resources'].items():
        for path, _ in d.decisions_of(node, key):
            expect(f"   {path} = " in out, f"decision {path} missing")
    expect('storage-account.meta' not in out, 'meta printed as a decision')
    expect('renders: public_network_access_enabled = false' in out, 'render-map.yaml values not applied (terraform_avm)')
    expect('renders: account_sku_name = "Standard_LRS" (development), "Standard_ZRS" (production)' in out,
           'render-map.yaml format not applied per stage')
    expect('renders: min_tls_version = "TLS1_2"' in out, 'a passed-through answer not quoted for Terraform')
    expect('[per stage]' in out, 'stage map not tagged')
    expect('storage-account.data_protection.blob_soft_delete_days = 14' in out.split('-- assumed')[1],
           'assumed value not listed')
    expect('context.subscription_id  [production]' in out, 'open entry not listed')
    expect('role: Key Vault Crypto Service Encryption User' in out, 'wiring not listed')

    reads = out.split('-- read')[1].split('\n\n')[0]
    expect('terraform-idiom.md' in reads and 'bicep-idiom.md' not in reads, 'idiom of the wrong target in the reading list')
    expect('pipelines.github.md' in reads and 'pipelines.ado.md' not in reads, 'wrong pipeline file in the reading list')
    gh = os.path.join(d.REFS, 'pipelines.github.md')
    gh_bicep = next(l for l, lv, t in d.headings(gh)[0] if t == 'Stage workflow - Bicep')
    gh_line = next(l for l in reads.splitlines() if 'pipelines.github.md' in l)
    expect(f"-{gh_bicep - 1}" in gh_line, "pipelines.github.md: the Bicep stage workflow is not left out for Terraform")
    expect('private-dns-zones.md' not in reads, 'private-dns-zones.md read though the platform owns the zones')
    expect('resource-groups.md' not in reads, 'resource-groups.md read under a single layout')

    naming = os.path.join(d.REFS, 'naming.md')
    hs, total = d.headings(naming)
    bicep_line = next(l for l, lv, t in hs if lv == 2 and t == 'Bicep')
    keep, _ = d.ranges_without(naming, [t for t, c in d.SKIPS['naming.md'] if c({'target': 'terraform'})])
    expect(all(not (a <= bicep_line <= b) for a, b in keep), "naming.md: the Bicep section is not left out for Terraform")

    sa = os.path.join(d.RESOURCES, 'storage', 'storage-account', 'terraform.md')
    hs, total = d.headings(sa)
    cut = next(l for l, lv, t in hs if t == 'Authored rendering')
    expect(d.split_reference(sa, 'avm')[0] == [(1, cut - 1)], 'AVM part does not end before Authored rendering')
    expect(d.split_reference(sa, 'authored')[0][-1] == (cut, total), 'authored part does not run from Authored rendering')
    expect('avm: Azure/avm-res-storage-storageaccount/azurerm' in out, 'AVM coordinate not read from the reference')
    kv_line = next(l for l in out.splitlines() if l.startswith('## key-vault'))
    expect('implementation=authored' in kv_line, 'module implementation not applied to its resource')
    expect('/key-vault/terraform.md' in reads and '(authored part)' in reads, 'authored reference part not listed')

    r = run(FIXTURE, '--target', 'bicep')
    expect('bicep-idiom.md' in r.stdout and 'terraform-idiom.md' not in r.stdout, '--target bicep did not switch the idiom')
    expect("renders: publicNetworkAccess = 'Disabled'" in r.stdout, '--target bicep did not use the bicep_avm entry')
    expect("renders: skuName = 'Standard_LRS' (development), 'Standard_ZRS' (production)" in r.stdout,
           '--target bicep did not quote the literal for Bicep')

    # The shapes beyond one entry, on their own fixture.
    r = run(SHAPES)
    shapes = r.stdout
    expect(r.returncode == 0, f"shapes fixture exited {r.returncode}: {r.stderr.strip()}")
    expect('renders: databases.<key>.sku_name = "GP_S_Gen5_2" (development), "GP_S_Gen5_4" (production)' in shapes,
           'a composite format not filled from the other answers per stage')
    expect('renders: part of database.vcores' in shapes, 'a part_of decision printed a fragment as its value')
    expect('renders: severity = 2' in shapes, 'by_kind did not pick the entry of the resource kind')
    expect('renders: storage_mb = 128 * 1024' in shapes, 'a format of code not written unquoted')
    with open(SHAPES, encoding='utf-8') as f:
        shaped = yaml.safe_load(f)
    shaped['resources']['alert-rule']['rule']['kind']['value'] = 'activity_log'
    tmp = tempfile.mkdtemp()
    try:
        other = os.path.join(tmp, 'infra-spec.yaml')
        with open(other, 'w', encoding='utf-8') as f:
            yaml.safe_dump(shaped, f)
        expect('gap: activity log alerts carry no severity' in run(other).stdout,
               'by_kind did not follow the kind answer')
    finally:
        shutil.rmtree(tmp)
    ctx = {'answers': {'identity.user_assigned_identity_ids': ['a', 'b']}, 'decisions': {}, 'entry_key': 'terraform'}
    lines = d.render_lines({'attribute': 'mi', 'values': {'user_assigned': {'expr': '{ ids = {identity.user_assigned_identity_ids} }'}}},
                           'user_assigned', ['production'], 'terraform', ctx)
    expect(lines == ['renders: mi = { ids = ["a", "b"] }'], f"a placeholder in a values expr not filled: {lines}")
    lines = d.render_lines({'attribute': 'rules', 'format': {'expr': '[for ip in {value}: { value: ip }]'}},
                           ['10.0.0.1'], ['production'], 'bicep', ctx)
    expect(lines == ["renders: rules = [for ip in ['10.0.0.1']: { value: ip }]"], f"a list answer not put into a format of code: {lines}")
    lines = d.render_lines({'attribute': 'x', 'values': {True: 'on', False: None}}, False, ['production'], 'terraform', ctx)
    expect(lines == ['renders: x = (left out)'], f"null in values not printed as left out: {lines}")

    # Every heading a skip names must still exist, or the reading grows without anyone noticing.
    for name, rules in d.SKIPS.items():
        titles = ['#' * lv + ' ' + t for _, lv, t in d.headings(os.path.join(d.REFS, name))[0]]
        for title, _ in rules:
            expect(any(t.startswith(title) for t in titles), f"{name}: no heading '{title}' (SKIPS is stale)")

    refs = 0
    for root, _, files in os.walk(d.RESOURCES):
        for target in ('terraform', 'bicep'):
            if f"{target}.md" in files:
                refs += 1
                path = os.path.join(root, f"{target}.md")
                # A reference without an AVM part (no module for the type) is read whole.
                has_avm = any(lv == 2 and t.startswith(d.AVM_MARK[3:]) for _, lv, t in d.headings(path)[0])
                keep, _ = d.split_reference(path, 'avm')
                expect(keep is not None or not has_avm,
                       f"{os.path.relpath(root, d.RESOURCES)}/{target}.md: an AVM part but no '## Authored rendering' heading")

    tmp = tempfile.mkdtemp()
    try:
        bad = os.path.join(tmp, 'infra-spec.yaml')
        with open(bad, 'w', encoding='utf-8') as f:
            yaml.safe_dump({**spec, 'resources': {'no-such-kind': {'g': {'q': {'value': 1, 'source': 'default'}}}}}, f)
        expect(run(bad).returncode == 1, 'a resource without a question set did not exit 1')
        expect(run(os.path.join(tmp, 'missing.yaml')).returncode == 2, 'a missing spec did not exit 2')
    finally:
        shutil.rmtree(tmp)

    for f in failures:
        print(f"[fail] {f}")
    print(f"{refs} rendering reference(s) checked, {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
