#!/usr/bin/env python3
"""Tests for scripts/check_render_map.py: each rule of the render-map.yaml format fails alone.

The storage account's render-map.yaml and questions.yaml are copied to a scratch directory; the
copy must pass, then each case breaks one rule in a fresh copy and asserts the check exits 1
naming it: a question missing, a key that is no question, an `_avm` entry where modules lists
none, a missing `_avm` entry, attribute and gap together, a `values` key the question does
not accept, `format` without {value}, `format` beside `values`, an unknown field, a module
not in modules, a coordinate in the wrong form, not_rendered beside an entry - and for the
extensions: a module in modules and companions, an authored entry naming a module that is no
companion, a list over several modules with an entry naming none, `by_kind` without `kinds`, `kinds` on a question
that is no enum, a `by_kind` key no answer, a sketch (`...`) instead of code, a format naming no question, a `part_of` whose
format does not name it, values missing an answer, a scalar entry without values, format or
passthrough, a passthrough that is not true or stands beside values. A companion, a list per
module, `by_kind`, a composite format, format beside values, format as code, null in values
and a composite format with part_of used correctly must pass. Every render-map.yaml in the
plugin must pass.

Usage:
    python3 run_render_map_tests.py

Needs PyYAML. Exit 0 all pass, 1 a test failed, 2 could not run.
"""

import copy
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'scripts', 'check_render_map.py')
PILOT = os.path.join(HERE, '..', '..', '..', 'resources', 'storage', 'storage-account')
TF_MODULE = 'Azure/avm-res-storage-storageaccount/azurerm'
PE_MODULE = 'Azure/avm-res-network-privateendpoint/azurerm'


def run(*args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, encoding='utf-8')


def main():
    try:
        import yaml
    except ImportError:
        print('[fail] no YAML parser available - pip install pyyaml')
        return 2
    with open(os.path.join(PILOT, 'render-map.yaml'), encoding='utf-8') as f:
        base = yaml.safe_load(f)

    def drop(d, k):
        del d['decisions'][k]

    def add_avm(d):
        d['modules']['bicep'] = []

    cases = [
        ('a question missing', lambda d: drop(d, 'security.min_tls_version'), 'security.min_tls_version missing'),
        ('a key that is no question', lambda d: d['decisions'].__setitem__('security.no_such', {'not_rendered': 'x'}),
         'security.no_such is not a question'),
        ('an _avm entry without a module', add_avm, 'bicep_avm not expected'),
        ('an _avm entry missing', lambda d: d['decisions']['security.min_tls_version'].pop('terraform_avm'),
         'terraform_avm missing'),
        ('attribute and gap together',
         lambda d: d['decisions']['security.min_tls_version']['terraform'].__setitem__('gap', 'x'),
         'exactly one of attribute or gap'),
        ('a values key the question does not accept',
         lambda d: d['decisions']['networking.public_network_access']['terraform']['values'].__setitem__('private', 'X'),
         "'private' is not an answer"),
        ('format without {value}',
         lambda d: d['decisions']['data_protection.replication']['bicep'].__setitem__('format', 'Standard_ZRS'),
         'format carries no {value}'),
        ('values missing an answer',
         lambda d: d['decisions']['networking.public_network_access']['terraform']['values'].pop('enabled'),
         "values has no literal for 'enabled'"),
        ('a scalar answer without values, format or passthrough',
         lambda d: d['decisions']['security.min_tls_version']['terraform'].pop('passthrough'),
         'needs values, format, or passthrough: true'),
        ('passthrough that is not true',
         lambda d: d['decisions']['security.min_tls_version']['terraform'].__setitem__('passthrough', 'yes'),
         'passthrough is true or absent'),
        ('passthrough beside values',
         lambda d: d['decisions']['networking.public_network_access']['terraform'].__setitem__('passthrough', True),
         'passthrough stands beside none of'),
        ('an unknown field',
         lambda d: d['decisions']['security.min_tls_version']['bicep'].__setitem__('default', 'x'),
         'unknown field(s) default'),
        ('a module not in modules',
         lambda d: d['decisions']['security.min_tls_version']['terraform_avm'].__setitem__('module', 'Azure/avm-res-x-y/azurerm'),
         'is neither in modules nor in companions'),
        ('a coordinate in the wrong form',
         lambda d: d['modules'].__setitem__('bicep', ['br/public:avm/res/storage/storage-account:0.33.1']),
         'is not a bicep AVM coordinate'),
        ('not_rendered beside an entry',
         lambda d: d['decisions']['placement.environments'].__setitem__('terraform', {'attribute': 'x'}),
         'not_rendered stands alone'),
        ('a module in modules and companions',
         lambda d: d.__setitem__('companions', {'terraform': [TF_MODULE]}), 'is in modules and in companions'),
        ('an authored entry naming a module that is no companion',
         lambda d: d['decisions']['security.min_tls_version']['terraform'].__setitem__('module', TF_MODULE),
         'is neither in modules nor in companions'),
        ('a list over several modules with an entry naming none',
         lambda d: d['decisions']['security.min_tls_version'].__setitem__(
             'terraform_avm', [{'attribute': 'a', 'passthrough': True, 'module': TF_MODULE},
                               {'attribute': 'b', 'passthrough': True}]),
         'names the module on every entry'),
        ('by_kind without kinds',
         lambda d: d['decisions']['security.min_tls_version'].__setitem__(
             'terraform', {'by_kind': {'Hot': {'attribute': 'a'}}}),
         'by_kind without a top-level kinds'),
        ('kinds on a question that is no enum',
         lambda d: d.__setitem__('kinds', {'question': 'networking.firewall_ip_rules'}), 'is not an enum'),
        ('a by_kind key that is no answer', lambda d: (
            d.__setitem__('kinds', {'question': 'data_protection.access_tier'}),
            d['decisions']['security.min_tls_version'].__setitem__(
                'terraform', {'by_kind': {'Warm': {'attribute': 'a'}}})),
         "by_kind key 'Warm'"),
        ('a sketch instead of code',
         lambda d: d['decisions']['networking.allow_azure_services_bypass']['terraform']['values'].__setitem__(
             True, {'expr': '{ bypass = ... }'}),
         "'...' in code"),
        ('a format naming no question',
         lambda d: d['decisions']['data_protection.replication']['bicep'].__setitem__('format', '{no.such}_{value}'),
         'not another question of the set'),
        ('a part_of whose format does not name it',
         lambda d: d['decisions']['data_protection.access_tier']['terraform'].__setitem__(
             'part_of', 'data_protection.replication'),
         'whose format does not name'),
    ]
    good = [
        ('a list of attributes of one call', lambda d: d['decisions']['security.min_tls_version'].__setitem__(
            'terraform', [{'attribute': 'a', 'passthrough': True}, {'attribute': 'b', 'passthrough': True}])),
        ('a companion on an authored entry', lambda d: (
            d.__setitem__('companions', {'terraform': [PE_MODULE]}),
            d['decisions']['networking.private_endpoint_subnet']['terraform'].__setitem__('module', PE_MODULE))),
        ('a list with a module on each', lambda d: d['decisions']['security.min_tls_version'].__setitem__(
            'terraform_avm', [{'module': TF_MODULE, 'attribute': 'a', 'passthrough': True},
                              {'module': TF_MODULE, 'attribute': 'b', 'passthrough': True}])),
        ('by_kind with kinds', lambda d: (
            d.__setitem__('kinds', {'question': 'data_protection.access_tier'}),
            d['decisions']['security.min_tls_version'].__setitem__(
                'terraform', {'by_kind': {'Hot': {'attribute': 'a', 'passthrough': True}, 'Cool': {'gap': 'none'}}}))),
        ('format beside values', lambda d: d['decisions']['data_protection.replication']['bicep'].__setitem__(
            'values', {'LRS': 'L', 'ZRS': 'Z', 'GRS': 'G', 'GZRS': 'GZ'})),
        ('format as code', lambda d: d['decisions']['data_protection.blob_soft_delete_days'].__setitem__(
            'terraform', {'attribute': 'x', 'format': {'expr': '{value} * 1'}})),
        ('null in values', lambda d: d['decisions']['networking.allow_azure_services_bypass']['bicep']['values'].__setitem__(
            False, None)),
        ('a composite format with part_of', lambda d: (
            d['decisions']['data_protection.replication'].__setitem__(
                'terraform', {'attribute': 'x', 'format': '{data_protection.access_tier}_{value}'}),
            d['decisions']['data_protection.access_tier'].__setitem__(
                'terraform', {'attribute': 'x', 'part_of': 'data_protection.replication'}))),
    ]

    failures = []
    tmp = tempfile.mkdtemp()
    try:
        shutil.copy(os.path.join(PILOT, 'questions.yaml'), tmp)
        target = os.path.join(tmp, 'render-map.yaml')

        def write(doc):
            with open(target, 'w', encoding='utf-8') as f:
                yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True)

        write(base)
        r = run(target)
        if r.returncode != 0:
            failures.append(f"the unbroken copy fails:\n{r.stdout}")
        for name, mutate, expected in cases:
            doc = copy.deepcopy(base)
            mutate(doc)
            write(doc)
            r = run(target)
            if r.returncode != 1 or expected not in r.stdout:
                failures.append(f"{name}: exit {r.returncode}, expected '{expected}' in:\n{r.stdout}")
        for name, mutate in good:
            doc = copy.deepcopy(base)
            mutate(doc)
            write(doc)
            r = run(target)
            if r.returncode != 0:
                failures.append(f"{name} should pass:\n{r.stdout}")
    finally:
        shutil.rmtree(tmp)

    r = run()
    if r.returncode != 0:
        failures.append(f"a render-map.yaml in the plugin fails:\n{r.stdout}")

    for f in failures:
        print(f"[fail] {f}")
    print(f"{len(cases)} failing and {len(good)} passing case(s), {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
