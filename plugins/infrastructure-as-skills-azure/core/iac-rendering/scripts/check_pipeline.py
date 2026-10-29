#!/usr/bin/env python3
"""Checks that a rendered pipeline holds the invariants of
core/iac-rendering/references/pipelines.md.

Read-only. Reads the infra-spec.yaml (stages, target, deploy_mechanism,
pipeline_auth, pipeline_approvals), finds the pipeline files the mechanism
renders under the root, and checks what a reviewer would otherwise check by eye:

  1. Every stage of context.environments has its jobs, in order, each waiting
     for the one before - and its stage file. A stage the spec still has `open:`
     entries for gets both with placeholders (the all-zero GUID, `OPEN-<what>`);
     a resolved stage's file holds none.
  2. Validate holds no Azure credential, and nothing else runs on a pull request.
  3. Terraform applies a saved plan file: `terraform apply` without one, or with
     -auto-approve, is a gate that is not one. No `terraform workspace`; the
     state key names the stage.
  4. The gate: exactly the stages pipeline_approvals names are gated, and an
     apply that is gated cannot run without the approval.
  5. One apply per stage at a time, queued and never cancelled.
  6. No secret: with pipeline_auth workload_identity no client secret and no
     `secrets.` reference; the login is federated.
  7. A plan artifact lives one day at most.
  8. Versions are pinned: no @main / latest, a Terraform constraint.
  9. The validate step of the target is there (fmt / validate, build / lint).
 10. Terraform: the root holds `backend "azurerm" {}`. `init -backend-config`
     without a backend block is ignored without an error - local state.
 11. A placeholder never deploys: the pipeline has a step that fails on a stage
     file holding a marker (the all-zero GUID, `OPEN-`, `ASSUMED:`), before any
     login. Every stage file marks each assumed value of the spec, and no other.
 12. Terraform: a plan that deletes a resource group does not reach apply - the
     plan job reads `terraform show -json` and fails on a `delete` of a group.
     Bicep deploys incrementally and never deletes, so there is nothing to refuse.

Platform-specific constructs are checked where the file can show them. What the
file cannot - an environment's approval check, a lock check, the federated
credential - is the platform's, listed in the pipeline's header, and reported
here as "not checkable" rather than silently passed.

Needs PyYAML (pip install pyyaml). Without it the script says so and exits 2.

Usage:
    python3 check_pipeline.py ./infra-spec.yaml [--root <dir>]

Exit 0 clean, 1 violations, 2 could not check.
"""

import argparse
import glob
import os
import re
import sys

COLORS = {'cyan': '36', 'green': '32', 'red': '31', 'yellow': '33', 'gray': '90'}
USE_COLOR = sys.stdout.isatty() and not os.environ.get('NO_COLOR')


def say(text, color=None):
    if color and USE_COLOR:
        print(f"\033[{COLORS[color]}m{text}\033[0m")
    else:
        print(text)


errors = []
notes = []


def err(msg):
    errors.append(msg)


def note(msg):
    notes.append(msg)


# ---------------------------------------------------------------- yaml helpers

def load_yaml(path):
    import yaml

    class Loader(yaml.SafeLoader):
        pass

    # GitLab's !reference [a, b] is a tag, not data; keep it as a marker list.
    Loader.add_constructor('!reference', lambda l, n: {'!reference': l.construct_sequence(n)})
    with open(path, encoding='utf-8') as f:
        text = f.read()
    return yaml.load(text, Loader), text


def key(d, name):
    """`on:` parses as the boolean True in YAML 1.1."""
    if name == 'on' and isinstance(d, dict):
        return d.get('on', d.get(True))
    return d.get(name) if isinstance(d, dict) else None


def walk_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_strings(v)


def scripts_of(node):
    """Every string under a script-bearing key, joined - what actually runs."""
    out = []

    def rec(n):
        if isinstance(n, dict):
            for k, v in n.items():
                if k in ('run', 'script', 'inlineScript', 'bash', 'before_script', 'after_script'):
                    out.extend(walk_strings(v))
                else:
                    rec(v)
        elif isinstance(n, list):
            for v in n:
                rec(v)

    rec(node)
    return '\n'.join(out)


def apply_problems(script, where):
    """terraform apply must take a plan file and no -auto-approve."""
    for m in re.finditer(r'terraform\s+apply\b([^\n]*)', script):
        # the command ends at the first ; | & on the line - `apply -input=false; if (...)` has no file
        args = re.split(r'[;|&]', m.group(1))[0].replace('\\', ' ').split()
        if '-auto-approve' in args:
            err(f"{where}: `terraform apply -auto-approve` - the saved plan is the approval; the flag turns it back into a fresh apply")
        if not [a for a in args if not a.startswith('-')]:
            err(f"{where}: `terraform apply` without a plan file - it would plan again and apply what nobody read")


# ---------------------------------------------------------------- spec

def sv(spec, name, default=None):
    node = (spec.get('deployment') or {}).get(name)
    if isinstance(node, dict) and 'value' in node:
        return node['value']
    return node if node is not None else default


def gated_stages(stages, mode):
    if mode == 'every_stage':
        return list(stages)
    if mode == 'none':
        return []
    return ['production'] if 'production' in stages else [stages[-1]]


# ---------------------------------------------------------------- common text checks

def common_text(path, text, auth, rel):
    low = text
    if re.search(r'terraform\s+workspace\b', low):
        err(f"{rel}: `terraform workspace` - one state per stage is a backend key, a workspace is invisible in the file tree")
    if auth == 'workload_identity':
        for pat, what in [(r'\bsecrets\.', 'a `secrets.` reference'),
                          (r'AZURE_CREDENTIALS|AZURE_AUTH', 'a stored credential blob'),
                          (r'client[-_]?secret|ARM_CLIENT_SECRET', 'a client secret')]:
            if re.search(pat, low, re.I):
                err(f"{rel}: {what} - pipeline_auth is workload_identity, nothing secret exists to store")
    for m in re.finditer(r'\$\{\{\s*(github\.event\.|github\.head_ref)', low):
        err(f"{rel}: `{m.group(0)}...` in the file - attacker-controlled text must not reach a shell")
        break


def state_keys(text, rel, stage_ref):
    """Every backend key names the stage - plan and apply must agree, so each is checked."""
    keys = re.findall(r'-backend-config="key=([^"\n]*)"', text)
    keys += re.findall(r'-backend-config=key=([^\s"`;]*)', text.replace('"', ''))
    if not keys:
        err(f"{rel}: no `-backend-config=\"key=...\"` - the state key is not set per stage")
    for k in keys:
        if not re.search(stage_ref, k):
            err(f"{rel}: the state key `{k}` does not name the stage")


def pinned_actions(text, rel):
    for m in re.finditer(r'uses:\s*([\w.\-]+/[\w.\-/]+)@([\w.\-]+)', text):
        ref = m.group(2)
        if ref in ('main', 'master', 'latest', 'HEAD') or not re.match(r'^(v?\d+(\.\d+)*|[0-9a-f]{40})$', ref):
            err(f"{rel}: {m.group(1)}@{ref} is not pinned to a version or a commit")


# ---------------------------------------------------------------- github

def check_github(root, stages, target, auth, gated, exempt):
    wf_dir = os.path.join(root, '.github', 'workflows')
    files = sorted(glob.glob(os.path.join(wf_dir, '*.y*ml')))
    if not files:
        err(f".github/workflows: no workflow under {root}")
        return
    entry = stage_wf = None
    docs = {}
    for f in files:
        d, text = load_yaml(f)
        docs[f] = (d, text)
        rel = os.path.relpath(f, root)
        common_text(f, text, auth, rel)
        pinned_actions(text, rel)
        on = key(d, 'on')
        if isinstance(on, dict) and 'workflow_call' in on:
            stage_wf = (f, d, text)
        elif any(isinstance(j, dict) and str(j.get('uses', '')).startswith('./.github/workflows/')
                 for j in (d.get('jobs') or {}).values()):
            entry = (f, d, text)
    if not entry or not stage_wf:
        err("github: expected one entry workflow calling a reusable stage workflow (workflow_call)")
        return
    ef, ed, etext = entry
    erel = os.path.relpath(ef, root)
    jobs = ed.get('jobs') or {}

    # 1 stages, order, chain
    called = {}
    for jid, j in jobs.items():
        if isinstance(j, dict) and 'uses' in j:
            w = j.get('with') or {}
            called[w.get('stage')] = (jid, j, w)
    expect = [s for s in stages if s not in exempt]
    if list(called) != expect:
        err(f"{erel}: stage jobs are {list(called)}, the spec's stages are {expect}")
    prev = 'validate'
    for s in expect:
        if s not in called:
            continue
        jid, j, w = called[s]
        needs = j.get('needs')
        needs = [needs] if isinstance(needs, str) else (needs or [])
        if prev not in needs:
            err(f"{erel}: stage {s} does not wait for {prev}")
        prev = jid
        # 4 gate flag
        want = s in gated
        if bool(w.get('gated')) != want:
            err(f"{erel}: stage {s} has gated: {w.get('gated')}, pipeline_approvals says {want}")
        # 7 token
        perms = j.get('permissions') or {}
        if auth == 'workload_identity' and perms.get('id-token') != 'write':
            err(f"{erel}: stage {s} has no `id-token: write` - the federated login cannot get a token")
    if 'validate' not in jobs:
        err(f"{erel}: no validate job")
    else:
        v = jobs['validate']
        if 'environment' in v or (v.get('permissions') or {}).get('id-token') == 'write':
            err(f"{erel}: validate holds an environment or id-token: write - it runs on pull requests and must hold no credential")
        vs = scripts_of(v)
        if target == 'terraform':
            for need in ('terraform fmt', 'terraform validate'):
                if need not in vs:
                    err(f"{erel}: validate does not run `{need}`")
        else:
            for need in ('bicep build', 'bicep lint'):
                if need not in vs:
                    err(f"{erel}: validate does not run `{need}`")
    top = ed.get('permissions')
    if isinstance(top, dict) and top.get('id-token') == 'write':
        err(f"{erel}: `id-token: write` at workflow level - grant it on the jobs that log in")
    if top == 'write-all':
        err(f"{erel}: permissions: write-all")
    # 2 pull request reaches no stage
    on = key(ed, 'on') or {}
    if isinstance(on, dict) and 'pull_request' in on and expect and expect[0] in called:
        cond = str(called[expect[0]][1].get('if', ''))
        if 'pull_request' not in cond:
            err(f"{erel}: the first stage has no `if` excluding pull_request - a PR run would reach Azure")

    # stage workflow
    sf, sd, stext = stage_wf
    srel = os.path.relpath(sf, root)
    sj = sd.get('jobs') or {}
    for need in ('plan', 'apply'):
        if need not in sj:
            err(f"{srel}: no `{need}` job")
    conc = sd.get('concurrency') or {}
    if not conc.get('group') or conc.get('cancel-in-progress') is not False:
        err(f"{srel}: concurrency needs a per-stage group and `cancel-in-progress: false` - queue an apply, never cancel one")
    elif 'stage' not in str(conc.get('group')):
        err(f"{srel}: the concurrency group does not name the stage - all stages would queue behind each other")
    if gated:
        appr = sj.get('approve')
        if not appr:
            err(f"{srel}: stages are gated but there is no `approve` job")
        else:
            if not str(appr.get('environment', '')).endswith('-approval'):
                err(f"{srel}: approve runs in {appr.get('environment')!r}, not a <stage>-approval environment - the approval check has nothing to hang on")
            if 'if' not in appr or 'changes' not in str(appr['if']):
                err(f"{srel}: approve is not conditional on the plan having changes - nobody should approve an empty plan")
        ap = sj.get('apply') or {}
        needs = ap.get('needs')
        needs = [needs] if isinstance(needs, str) else (needs or [])
        if 'approve' not in needs:
            err(f"{srel}: apply does not need approve")
    # a job without a checkout has no deployable root on its runner
    wd = ((sd.get('defaults') or {}).get('run') or {}).get('working-directory')
    if wd and str(wd).strip('./') != '':
        for jid, j in sj.items():
            steps = j.get('steps') or []
            if any(str(st.get('uses', '')).startswith('actions/checkout') for st in steps):
                continue
            own = ((j.get('defaults') or {}).get('run') or {}).get('working-directory')
            if own is None or str(own).strip('./') != '':
                err(f"{srel}: job {jid} has no checkout but inherits working-directory {wd!r}, "
                    f"which is not on a fresh runner - set `defaults.run.working-directory: .` on it")
    ap = sj.get('apply') or {}
    if 'changes' not in str(ap.get('if', '')):
        err(f"{srel}: apply is not conditional on the plan having changes")
    if 'environment' not in ap:
        err(f"{srel}: apply runs in no environment - the stage's identity and branch policy are bound to it")
    allscripts = scripts_of(sd)
    if target == 'terraform':
        apply_problems(allscripts, srel)
        if 'upload-artifact' in stext:
            for j in sj.values():
                for st in (j.get('steps') or []):
                    if str(st.get('uses', '')).startswith('actions/upload-artifact'):
                        days = (st.get('with') or {}).get('retention-days')
                        if days is None or int(days) > 1:
                            err(f"{srel}: the plan artifact keeps {days} days - a plan file can hold sensitive values; one day")
        else:
            err(f"{srel}: no plan artifact is uploaded - apply would have no saved plan")
        if 'download-artifact' not in stext:
            err(f"{srel}: apply does not download the plan artifact")
        versions = re.findall(r'terraform_version:\s*(\S+)', stext)
        if not versions or not all(v.strip('"\'').startswith('~>') for v in versions):
            err(f"{srel}: every setup-terraform needs a `~>` constraint on terraform_version, found {versions}")
        state_keys(stext, srel, r'\$\{?STAGE\}?|inputs\.stage')
    else:
        if not re.search(r'az deployment \w+ what-if', allscripts):
            err(f"{srel}: no `az deployment ... what-if` before the deployment")
        elif 'NestedDeploymentShortCircuited' not in allscripts:
            err(f"{srel}: the what-if step does not report the modules what-if short-circuits - "
                f"the approver would take a partial list for the whole plan")
    if auth == 'workload_identity':
        if target == 'terraform' and not re.search(r'ARM_USE_OIDC:\s*["\']?true', stext):
            err(f"{srel}: ARM_USE_OIDC is not true - Terraform would look for a secret")
        if target == 'bicep' and 'azure/login' not in stext:
            err(f"{srel}: no azure/login - the Azure CLI has no session")
    note("github: the <stage> and <stage>-approval environments, their reviewers and the federated credential are the platform's - not checkable here")


# ---------------------------------------------------------------- azure devops

def check_ado(root, stages, target, auth, gated, exempt):
    entry_path = os.path.join(root, 'azure-pipelines.yml')
    if not os.path.isfile(entry_path):
        err("azure-pipelines.yml: missing")
        return
    ed, etext = load_yaml(entry_path)
    common_text(entry_path, etext, auth, 'azure-pipelines.yml')
    tdir = os.path.join(root, '.azure-pipelines')
    tmpl = {}
    for f in sorted(glob.glob(os.path.join(tdir, '*.yml'))):
        d, t = load_yaml(f)
        tmpl[os.path.basename(f)] = (d, t)
        common_text(f, t, auth, os.path.join('.azure-pipelines', os.path.basename(f)))
    if 'stage.yml' not in tmpl:
        err(".azure-pipelines/stage.yml: missing")
        return

    items = ed.get('stages') or []
    called = []
    validate = None
    for it in items:
        if isinstance(it, dict) and it.get('stage') == 'validate':
            validate = it
        elif isinstance(it, dict) and 'template' in it:
            called.append(it.get('parameters') or {})
    expect = [s for s in stages if s not in exempt]
    got = [p.get('stage') for p in called]
    if got != expect:
        err(f"azure-pipelines.yml: stages are {got}, the spec's are {expect}")
    prev = 'validate'
    conns = []
    for p in called:
        s = p.get('stage')
        if p.get('dependsOn') != prev:
            err(f"azure-pipelines.yml: stage {s} dependsOn {p.get('dependsOn')!r}, expected {prev!r}")
        prev = s
        if bool(p.get('gated')) != (s in gated):
            err(f"azure-pipelines.yml: stage {s} has gated: {p.get('gated')}, pipeline_approvals says {s in gated}")
        conns.append(p.get('serviceConnection'))
    if len(set(conns)) != len(conns) or None in conns:
        err("azure-pipelines.yml: each stage needs its own service connection - one identity per stage")
    if validate is None:
        err("azure-pipelines.yml: no validate stage")
    else:
        vtext = str(list(walk_strings(validate)))
        if 'azureSubscription' in vtext or 'AzureCLI' in vtext:
            err("azure-pipelines.yml: validate uses a service connection - it runs on pull requests and must hold no credential")
        vs = scripts_of(validate)
        needs = ('terraform fmt', 'terraform validate') if target == 'terraform' else ('bicep build', 'bicep lint')
        for n in needs:
            if n not in vs:
                err(f"azure-pipelines.yml: validate does not run `{n}`")
    if 'pr' not in ed and 'trigger' not in ed:
        err("azure-pipelines.yml: no trigger and no pr")

    sd, stext = tmpl['stage.yml']
    st = (sd.get('stages') or [{}])[0]
    if 'PullRequest' not in str(st.get('condition', '')):
        err(".azure-pipelines/stage.yml: the stage condition does not exclude a pull request build - it would reach the service connection")
    jobs = st.get('jobs') or []
    dep = [j for j in jobs if 'deployment' in j]
    if not dep:
        err(".azure-pipelines/stage.yml: no `deployment` job - an environment approval check only fires for one")
    else:
        d = dep[0]
        if not d.get('environment'):
            err(".azure-pipelines/stage.yml: the apply job names no environment")
        if 'changes' not in str(d.get('condition', '')):
            err(".azure-pipelines/stage.yml: apply is not conditional on the plan having changes - an empty stage would still ask for approval")
    if 'ManualValidation' in stext:
        err(".azure-pipelines/stage.yml: ManualValidation - use an environment check; the task's approver list is unreliable")
    all_scripts = scripts_of(sd)
    if target == 'terraform':
        apply_problems(all_scripts, '.azure-pipelines/stage.yml')
        if 'PublishPipelineArtifact' not in stext:
            err(".azure-pipelines/stage.yml: no plan artifact published")
        state_keys(stext, '.azure-pipelines/stage.yml', r'\$\(STAGE\)')
        if 'terraform-install.yml' not in tmpl:
            err(".azure-pipelines/terraform-install.yml: missing")
        else:
            if 'sha256sum' not in tmpl['terraform-install.yml'][1]:
                err(".azure-pipelines/terraform-install.yml: the download is not checksum-verified")
        tfv = [v for v in (ed.get('variables') or []) if isinstance(v, dict) and v.get('name') == 'TF_VERSION']
        if not tfv or not re.match(r'^\d+\.\d+\.\d+$', str(tfv[0].get('value'))):
            err("azure-pipelines.yml: TF_VERSION is missing or not an exact version")
    else:
        if 'what-if' not in all_scripts:
            err(".azure-pipelines/stage.yml: no `az deployment ... what-if` before the deployment")
    if auth == 'workload_identity' and 'AzureCLI@2' in stext:
        # every Terraform task that logs in needs the token, not just the first
        if target == 'terraform' and (stext.count('addSpnToEnvironment: true') != stext.count('AzureCLI@2')
                                      or 'ARM_USE_OIDC' not in stext):
            err(".azure-pipelines/stage.yml: Terraform does not receive the federated token in every AzureCLI task (addSpnToEnvironment + ARM_USE_OIDC)")
    note("azure_devops: the service connections, the environments' approval checks, the exclusive lock and the variable groups are the platform's - not checkable here")


# ---------------------------------------------------------------- gitlab

def resolve(jobs, name, seen=()):
    j = dict(jobs.get(name) or {})
    ext = j.get('extends')
    if ext:
        merged = {}
        for p in ([ext] if isinstance(ext, str) else ext):
            if p in seen:
                continue
            merged.update(resolve(jobs, p, seen + (name,)))
        merged.update({k: v for k, v in j.items() if k != 'extends'})
        return merged
    return j


def check_gitlab(root, stages, target, auth, gated, exempt):
    path = os.path.join(root, '.gitlab-ci.yml')
    if not os.path.isfile(path):
        err(".gitlab-ci.yml: missing")
        return
    d, text = load_yaml(path)
    common_text(path, text, auth, '.gitlab-ci.yml')
    expect = [s for s in stages if s not in exempt]
    if (d.get('stages') or []) != ['validate'] + expect:
        err(f".gitlab-ci.yml: stages are {d.get('stages')}, expected {['validate'] + expect}")
    jobs = {k: v for k, v in d.items() if isinstance(v, dict)}
    v = resolve(jobs, 'validate')
    if not v:
        err(".gitlab-ci.yml: no validate job")
    else:
        vs = scripts_of(v)
        if 'id_tokens' in v:
            err(".gitlab-ci.yml: validate requests an OIDC token - it must hold no credential")
        needs = ('terraform fmt', 'terraform validate') if target == 'terraform' else ('bicep build', 'bicep lint')
        for n in needs:
            if n not in vs:
                err(f".gitlab-ci.yml: validate does not run `{n}`")
    prev = 'validate'
    for s in expect:
        plan, apply = resolve(jobs, f'{s}:plan'), resolve(jobs, f'{s}:apply')
        if not plan or not apply:
            err(f".gitlab-ci.yml: stage {s} needs {s}:plan and {s}:apply")
            continue
        for nm, j in ((f'{s}:plan', plan), (f'{s}:apply', apply)):
            rules = j.get('rules') or []
            if not rules or not all('$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH' in str(r.get('if', '')) for r in rules if isinstance(r, dict)):
                err(f".gitlab-ci.yml: {nm} is not restricted to the default branch - a merge request pipeline would reach Azure")
            if auth == 'workload_identity' and 'id_tokens' not in j:
                err(f".gitlab-ci.yml: {nm} has no id_tokens - the federated login has no token")
        pneeds = plan.get('needs') or []
        want_prev = prev
        if want_prev not in pneeds:
            err(f".gitlab-ci.yml: {s}:plan does not wait for {want_prev}")
        if f'{s}:plan' not in (apply.get('needs') or []):
            err(f".gitlab-ci.yml: {s}:apply does not need {s}:plan")
        prev = f'{s}:apply'
        manual = any(isinstance(r, dict) and r.get('when') == 'manual' for r in (apply.get('rules') or []))
        if manual != (s in gated):
            err(f".gitlab-ci.yml: {s}:apply is {'manual' if manual else 'automatic'}, pipeline_approvals says {'gated' if s in gated else 'ungated'}")
        if manual and any(isinstance(r, dict) and r.get('when') == 'manual' and r.get('allow_failure') is not False for r in apply.get('rules')):
            err(f".gitlab-ci.yml: {s}:apply is manual with allow_failure not false - the pipeline would run on past the gate")
        if apply.get('resource_group') != s:
            err(f".gitlab-ci.yml: {s}:apply has resource_group {apply.get('resource_group')!r}, expected {s!r} - two applies would race for the state")
        env = (apply.get('environment') or {})
        if (env.get('name') if isinstance(env, dict) else env) != s:
            err(f".gitlab-ci.yml: {s}:apply is not in the {s} environment")
        if target == 'terraform':
            apply_problems(scripts_of(apply), f'{s}:apply')
            exp = str((plan.get('artifacts') or {}).get('expire_in', ''))
            if not re.match(r'^(1 day|1 days|\d+ hours?|\d+ min\w*)$', exp) or (exp.endswith('hours') and int(exp.split()[0]) > 24):
                err(f".gitlab-ci.yml: {s}:plan artifact expires in {exp or 'never'!r} - a plan file can hold sensitive values; one day")
    if target == 'terraform':
        img = (d.get('default') or {}).get('image')
        img = img.get('name') if isinstance(img, dict) else img
        if not img or img.endswith(':latest') or ':' not in str(img):
            err(f".gitlab-ci.yml: image {img!r} is not pinned to a version")
        state_keys(text, '.gitlab-ci.yml', r'\$CI_ENVIRONMENT_NAME')
    else:
        img = (d.get('default') or {}).get('image')
        if not img or str(img).endswith(':latest'):
            note(".gitlab-ci.yml: the Azure CLI image is :latest - pin a dated tag")
    note("gitlab: the protected environments, their scoped variables and the federated credential are the platform's - the subject names the branch, not the stage")


# ---------------------------------------------------------------- local

def check_local(root, stages, target, auth, gated, exempt):
    path = os.path.join(root, 'deploy.ps1')
    if not os.path.isfile(path):
        err("deploy.ps1: missing")
        return
    with open(path, encoding='utf-8') as f:
        text = f.read()
    common_text(path, text, 'workload_identity', 'deploy.ps1')
    m = re.search(r"ValidateSet\(([^)]*)\)", text)
    got = re.findall(r"'([^']+)'", m.group(1)) if m else []
    expect = [s for s in stages if s not in exempt]
    if got != expect:
        err(f"deploy.ps1: ValidateSet is {got}, the spec's stages are {expect}")
    if 'Read-Host' not in text:
        err("deploy.ps1: no confirmation before the change")
    if target == 'terraform':
        apply_problems(text, 'deploy.ps1')
        state_keys(text, 'deploy.ps1', r'\$Stage')
        if 'Remove-Item' not in text:
            err("deploy.ps1: the plan file is not removed - it can hold sensitive values")
    else:
        if 'what-if' not in text:
            err("deploy.ps1: no what-if before the deployment")
    note("local: no pipeline - the person at the keyboard is the approval; no record of who applied what")


# ---------------------------------------------------------------- the code beside the pipeline

def check_backend(root):
    """`init -backend-config` is ignored without a backend block - the state would be local."""
    tf = glob.glob(os.path.join(root, '*.tf'))
    if not tf:
        note("terraform: no .tf beside the pipeline - the backend block was not checked")
        return
    for f in tf:
        with open(f, encoding='utf-8') as fh:
            if re.search(r'^\s*backend\s+"azurerm"\s*\{', fh.read(), re.M):
                return
    err("terraform: no `backend \"azurerm\" {}` block - `terraform init -backend-config=...` ignores its values "
        "without an error when there is none, and the state would be local and gone with the runner")


# ---------------------------------------------------------------- placeholders

ZERO_GUID = '00000000-0000-0000-0000-000000000000'
MARKER_RE = re.compile(ZERO_GUID + r'|OPEN-')
# An assumed value is a parameter whose working value stands in every stage file, marked with the
# decision it stands for: `vm_instance_count = 3  # ASSUMED: resources.virtual-machine.machine.instance_count`.
ASSUMED_RE = re.compile(r'ASSUMED:\s*([A-Za-z0-9_.\-]+)')


def assumed_keys(spec):
    # Every decision of the spec whose source is assumed, by its key path.
    out = set()

    def walk(node, path):
        if isinstance(node, dict):
            if 'value' in node and node.get('source') == 'assumed':
                out.add(path)
                return
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k))
    for section in ('deployment', 'resources', 'wiring'):
        walk(spec.get(section), section)
    return out


def pipeline_files(root, mech):
    pats = {'github': ['.github/workflows/*.y*ml'], 'azure_devops': ['azure-pipelines.yml', '.azure-pipelines/*.yml'],
            'gitlab': ['.gitlab-ci.yml'], 'local': ['deploy.ps1']}[mech]
    out = []
    for p in pats:
        out.extend(sorted(glob.glob(os.path.join(root, p))))
    return out


def check_guard(root, mech):
    """A placeholder never deploys: the pipeline refuses a stage file that still holds one."""
    text = ''
    for f in pipeline_files(root, mech):
        with open(f, encoding='utf-8') as fh:
            text += fh.read() + '\n'
    searches = 'grep' in text or 'Select-String' in text
    if not (ZERO_GUID in text and 'OPEN-' in text and 'ASSUMED:' in text and searches):
        err("no step that refuses placeholder values - a stage file holding the all-zero GUID, `OPEN-` or an "
            "`ASSUMED:` value must fail before any login (pipelines.md, invariant 11)")


def check_group_guard(root, mech):
    """Terraform only: a plan that deletes a resource group is refused before apply."""
    text = ''
    for f in pipeline_files(root, mech):
        with open(f, encoding='utf-8') as fh:
            text += fh.read() + '\n'
    if not ('show -json' in text and 'azurerm_resource_group' in text and 'delete' in text):
        err("no step that refuses a plan deleting a resource group - the plan job must read "
            "`terraform show -json` and fail on a `delete` of a group before the plan is saved or approved "
            "(pipelines.md, invariant 12)")


def check_stage_files(root, stages, target, open_stages, assumed=frozenset()):
    """Every stage has its file; an open stage's file holds placeholders, a resolved stage's none;
    every file marks each assumed value of the spec, and nothing else, as ASSUMED."""
    code = root
    if target == 'terraform':
        names = {s: os.path.join('environments', f'{s}.tfvars') for s in stages}
        present = bool(glob.glob(os.path.join(root, '*.tf')))
    else:
        names = {s: f'main.{s}.bicepparam' for s in stages}
        # the Bicep root may sit in a directory of the repository (bicep/, infra/)
        for d in (root, os.path.join(root, 'bicep'), os.path.join(root, 'infra')):
            if glob.glob(os.path.join(d, '*.bicep')):
                code = d
                break
        present = bool(glob.glob(os.path.join(code, '*.bicep')))
    if not present:
        note("no code beside the pipeline - the stage files were not checked")
        return
    for s in stages:
        path = os.path.join(code, names[s])
        if not os.path.isfile(path):
            err(f"{os.path.relpath(path, root)}: missing - every stage gets its file, with placeholders while its values are open")
            continue
        with open(path, encoding='utf-8') as f:
            text = f.read()
        has = bool(MARKER_RE.search(text))
        marked = set(ASSUMED_RE.findall(text))
        for k in sorted(assumed - marked):
            err(f"{names[s]}: {k} is assumed in the spec but not marked here - an assumed value is a parameter "
                f"in every stage file with `ASSUMED: {k}` beside it, so the pipeline refuses it")
        for k in sorted(marked - assumed):
            err(f"{names[s]}: marks {k} as ASSUMED, but the spec does not assume it - drop the marker")
        if s in open_stages and not has:
            err(f"{names[s]}: stage {s} is open in the spec but its file holds no placeholder - "
                f"either the values were given (drop the open: entries) or they were guessed")
        if s not in open_stages and has:
            err(f"{names[s]}: stage {s} is resolved in the spec but its file still holds a placeholder")


# ---------------------------------------------------------------- main

def deployment_scope(spec):
    """The spec's deployment_scope; a spec written before the key: subscription when a group is created."""
    scope = sv(spec, 'deployment_scope')
    if scope:
        return scope
    dep = spec.get('deployment') or {}
    created = (dep.get('resource_groups_created') or {})
    created = created.get('value') if isinstance(created, dict) else created
    return 'subscription' if created else 'resource_group'


def check_scope(root, mech, scope):
    """Bicep only: the deployment command matches deployment_scope (pipelines.md, invariant 13)."""
    text = ''
    for f in pipeline_files(root, mech):
        with open(f, encoding='utf-8') as fh:
            text += fh.read() + '\n'
    used = set(re.findall(r'az deployment (group|sub) (?:what-if|create)', text))
    want = 'sub' if scope == 'subscription' else 'group'
    for verb in sorted(used - {want}):
        err(f"deploys with `az deployment {verb}`, but deployment_scope is {scope} - the command is "
            f"`az deployment {want}` (pipelines.md, invariant 13)")
    if want == 'sub' and want in used and '--location' not in text:
        err("`az deployment sub` without --location - a subscription-scope deployment names where its record lives")


def main():
    ap = argparse.ArgumentParser(description='Check a rendered pipeline against the invariants of pipelines.md.')
    ap.add_argument('spec', help='the infra-spec.yaml')
    ap.add_argument('--root', help='directory holding the pipeline files (default: the spec directory)')
    args = ap.parse_args()

    if not os.path.isfile(args.spec):
        say(f"[fail] no such file: {args.spec}", 'red')
        return 2
    try:
        import yaml  # noqa: F401
    except ImportError:
        say('[fail] no YAML parser available (pip install pyyaml)', 'red')
        return 2
    spec_path = os.path.abspath(args.spec)
    root = os.path.abspath(args.root or os.path.dirname(spec_path))
    try:
        spec, _ = load_yaml(spec_path)
    except Exception as e:  # noqa: BLE001
        say(f"[fail] the spec does not parse: {e}", 'red')
        return 1

    mech = sv(spec, 'deploy_mechanism')
    target = (spec.get('spec') or {}).get('target')
    stages = (spec.get('context') or {}).get('environments') or ['development', 'test', 'production']
    auth = sv(spec, 'pipeline_auth', 'workload_identity')
    approvals = sv(spec, 'pipeline_approvals', 'production')
    if mech is None:
        say('[fail] the spec has no deployment.deploy_mechanism - nothing to check', 'red')
        return 2
    if target not in ('terraform', 'bicep'):
        say(f"[fail] spec.target is {target!r}, expected terraform or bicep", 'red')
        return 2
    # A stage with open: entries is not left out: it has its job and its file, with
    # placeholders, and the pipeline refuses to run it.
    open_stages = set()
    for o in spec.get('open') or []:
        if isinstance(o, dict):
            open_stages.update(o.get('environments') or [])
    open_stages &= set(stages)
    gated = gated_stages(stages, approvals) if mech != 'local' else []

    fns = {'github': check_github, 'azure_devops': check_ado, 'gitlab': check_gitlab, 'local': check_local}
    if mech not in fns:
        say(f"[fail] deploy_mechanism {mech!r} is not one of {sorted(fns)}", 'red')
        return 2
    fns[mech](root, stages, target, auth, gated, set())
    check_guard(root, mech)
    check_stage_files(root, stages, target, open_stages, assumed_keys(spec))
    if target == 'terraform':
        check_backend(root)
        check_group_guard(root, mech)
    else:
        check_scope(root, mech, deployment_scope(spec))

    say(f"Pipeline check - {mech}, {target}, stages {', '.join(stages)}, gated {', '.join(gated) or 'none'}", 'cyan')
    say('-' * 70, 'gray')
    for e in errors:
        say(f"[fail] {e}", 'red')
    for n in notes:
        say(f"[note] {n}", 'yellow')
    say('-' * 70, 'gray')
    if errors:
        say(f"{len(errors)} violation(s)", 'red')
        return 1
    say('Every invariant the file can show holds.', 'green')
    return 0


if __name__ == '__main__':
    sys.exit(main())
