#!/usr/bin/env python3
"""Pre-commit consistency checks for the Infrastructure-as-Skills-Azure repo.

Read-only. Verifies the things that can actually go wrong in a Claude Code
plugin repo whose content is Markdown and YAML:

  1. Secrets in tracked files. The repo is public and the origin URL embeds
     a PAT, so a pasted token is the realistic leak here.
  2. Skill structure: every skill directory carries a SKILL.md whose
     frontmatter name matches the directory and which has a description.
  3. The skill listing budget: each description within the 1,536-character
     cap, and the repo's total listing cost reported. This is the constraint
     that silently breaks skill triggering.
  4. Plugin manifest paths: every path in plugin.json's skills array exists,
     and every group directory holding a SKILL.md is declared. A missing
     path fails to load the plugin.
  5. Question sets: both naming identifier forms and the abbreviation, which
     must equal the type's ::default entry in naming.default.yaml
     declared, the Bicep one without an Azure:: prefix, unique ids,
     required/default not both set, why and renders present. A
     scope: deployment set names no resource and is exempt from the
     naming checks.
  6. Routing coverage: every resource's questions.yaml reachable from its
     family's routing.md (or the SKILL.md of the skill holding it), every
     family's routing.md linked from core/azure-resources, and no row
     pointing at a missing file.
  7. No CLAUDE.md inside the plugin directory - it is not loaded as context
     there and claude plugin validate warns about it. Every tracked
     infra-spec.yaml is in the canonical form write_spec.py lays out.
  8. Relative Markdown links resolve, and no tracked path contains a space.
  9. `claude plugin validate` on the plugin and on the marketplace. It is the
     only check that reads the manifest the way the loader does. If the CLI
     cannot be found it warns rather than passing quietly.

Usage:
    python3 .claude/skills/git-commit-conventions/scripts/check_repo_consistency.py
    python3 .../check_repo_consistency.py --skip-links --skip-secrets --listing-budget 2000

Exit code 0 = ok (warnings allowed), 1 = at least one error.
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote

COLORS = {'cyan': '36', 'green': '32', 'red': '31', 'yellow': '33', 'gray': '90', 'darkyellow': '33'}
USE_COLOR = sys.stdout.isatty() and not os.environ.get('NO_COLOR')


def say(text, color=None):
    # The CLI's output carries UTF-8 glyphs; a cp1252 console on Windows would
    # otherwise die printing them.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')
    if color and USE_COLOR:
        print(f"\033[{COLORS[color]}m{text}\033[0m")
    else:
        print(text)


def read(path):
    with open(path, encoding='utf-8-sig') as f:
        return f.read()


def rel(repo, path):
    return os.path.relpath(path, repo).replace('\\', '/')


def find_files(root, name):
    hits = []
    for d, _, files in os.walk(root):
        for f in files:
            if f == name:
                hits.append(os.path.join(d, f))
    return sorted(hits)


# Parse a SKILL.md frontmatter into name/description.
def skill_frontmatter(path):
    raw = read(path)
    fm = re.match(r'---\r?\n(.*?)\r?\n---', raw, re.S)
    if not fm:
        return None
    block = fm.group(1)
    name = re.search(r'^name:[ \t]*(\S[^\r\n]*?)[ \t]*\r?$', block, re.M)
    # description may wrap across lines; take everything up to the next top-level key.
    desc = re.search(r'^description:[ \t]*(.+?)(?=\r?\n[A-Za-z_][A-Za-z0-9_-]*:|\Z)', block, re.S | re.M)
    return {
        'name': name.group(1) if name else '',
        'description': re.sub(r'\s+', ' ', desc.group(1)).strip() if desc else '',
    }


SECRET_PATTERNS = [
    ('private key block', r'-----BEGIN (RSA |OPENSSH |EC |PGP )?PRIVATE KEY'),
    ('bearer token', r'(?i)\bbearer\s+[A-Za-z0-9\-_\.=]{20,}'),
    ('JWT', r'\beyJ[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}\.'),
    # The value has to look like a credential, not like the next word in a
    # sentence: prose such as "anything else secret: deployment outputs are
    # readable" otherwise matches. So require a digit, a symbol common in
    # encoded secrets, or real length.
    ('assigned secret', r'(?i)\b(password|passwd|pwd|secret|client_secret|api[_-]?key|access[_-]?key)\b\s*[:=]\s*["\']?(?=[^\s"\'<>{}$]*(?:\d|[+/=_.\-]))[^\s"\'<>{}$]{8,}|\b(password|passwd|pwd|secret|client_secret|api[_-]?key|access[_-]?key)\b\s*[:=]\s*["\']?[^\s"\'<>{}$]{16,}'),
    ('Azure storage key', r'(?i)AccountKey\s*=\s*[A-Za-z0-9+/=]{20,}'),
    ('GitHub token', r'\bgh[pousr]_[A-Za-z0-9]{20,}'),
    ('remote URL w/ creds', r'(?i)https://[^\s/@:]+:[^\s/@]+@(github|dev\.azure)\.com'),
    ('connection string', r'(?i)(mongodb|postgres(ql)?|mysql|amqps?)://[^\s:/@]+:[^\s/@]+@'),
    ('real subscription', r'(?i)\bsubscription_id\s*[:=]\s*["\']?(?!0{8})[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'),
]
# Placeholders the skills legitimately contain. Applied to the matched span,
# not the whole line, so a real secret beside the word "example" is still
# caught. A GUID whose every segment is one repeated character
# (00000000-0000-..., 11111111-2222-..., aaaaaaaa-bbbb-...) is the shape the
# eval prompts and the examples use; no real subscription looks like that.
PLACEHOLDER = re.compile(
    r'(?i)(\{\{?\s*\w+\s*\}?\}|<[^>\r\n]{1,40}>|\$\{?\w+\}?|xxx+|\*\*\*+|REDACTED|PLACEHOLDER|CHANGEME'
    r'|\b([0-9a-f])\2{7}-([0-9a-f])\3{3}-([0-9a-f])\4{3}-([0-9a-f])\5{3}-([0-9a-f])\6{11}\b)')
TEXT_EXT = {'.md', '.json', '.yml', '.yaml', '.ps1', '.sh', '.py', '.txt', '.env', '.ini', '.cfg', '.toml', '.tf', '.bicep'}


def main():
    ap = argparse.ArgumentParser(description='Pre-commit consistency checks for the plugin repo.')
    ap.add_argument('--skip-links', action='store_true', help='skip the link check (it reads every tracked Markdown file)')
    ap.add_argument('--skip-secrets', action='store_true', help='skip the secret scan (it reads every tracked text file)')
    ap.add_argument('--listing-budget', type=int, default=2000,
                    help='character budget to report the skill listing against (default 2000, 1%% of a 200k context window)')
    args = ap.parse_args()

    try:
        repo = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        say('Not inside a git repository.', 'red')
        return 1
    os.chdir(repo)

    errors, warnings = [], []
    say(f"\nPlugin repo consistency check - {repo}", 'cyan')
    print('-' * 70)

    tracked = [t for t in subprocess.run(['git', 'ls-files'], capture_output=True, text=True).stdout.splitlines() if t]
    if not tracked:
        say('[info] nothing tracked yet - checks run against the index only', 'darkyellow')

    plugin_root = os.path.join(repo, 'plugins', 'infrastructure-as-skills-azure')

    # Every SKILL.md shipped in the plugin (repo-maintenance skills under
    # .claude/ are not part of the listing a consumer gets).
    skill_files = find_files(plugin_root, 'SKILL.md') if os.path.isdir(plugin_root) else []

    # --- 1. secrets in tracked files ---------------------------------------
    if args.skip_secrets:
        print('[skip] secret scan')
    else:
        compiled = [(n, re.compile(p)) for n, p in SECRET_PATTERNS]
        candidates = [f for f in tracked if os.path.splitext(f)[1].lower() in TEXT_EXT]
        hits = []
        for f in candidates:
            if not os.path.isfile(f):
                continue
            with open(f, encoding='utf-8', errors='replace') as fh:
                for line_no, line in enumerate(fh, 1):
                    for name, pat in compiled:
                        m = pat.search(line)
                        if m:
                            if PLACEHOLDER.search(m.group(0)):
                                continue
                            hits.append(f"{f}:{line_no}  [{name}]")
                            break
        if not hits:
            say(f"[ ok ] secret scan - {len(candidates)} text file(s), nothing found", 'green')
        else:
            say(f"[fail] secret scan - {len(hits)} suspicious line(s)", 'red')
            for h in hits:
                say(f"         {h}", 'gray')
            errors.append(f"{len(hits)} line(s) look like a committed credential. Replace with a placeholder and rotate the real value.")

    # --- 2. skill structure ------------------------------------------------
    if not skill_files:
        say('[info] no skills in the plugin yet', 'darkyellow')
    else:
        structure_ok = True
        for sf in skill_files:
            dir_name = os.path.basename(os.path.dirname(sf))
            r = rel(repo, sf)
            meta = skill_frontmatter(sf)
            if meta is None:
                say(f"[fail] {r} has no YAML frontmatter", 'red')
                errors.append(f"{r} has no frontmatter - name and description decide when the skill triggers.")
                structure_ok = False
                continue
            if meta['name'] != dir_name:
                say(f"[fail] {r} - name '{meta['name']}' does not match directory '{dir_name}'", 'red')
                errors.append(f"{r} frontmatter name '{meta['name']}' must equal its directory name '{dir_name}'.")
                structure_ok = False
            if not meta['description'].strip():
                say(f"[fail] {r} has no description", 'red')
                errors.append(f"{r} needs a description - it is the triggering mechanism.")
                structure_ok = False
        if structure_ok:
            say(f"[ ok ] skill structure - {len(skill_files)} skill(s)", 'green')

    # --- 3. the skill listing budget ---------------------------------------
    if skill_files:
        cap = 1536
        total = 0
        over_cap, rows = [], []
        for sf in skill_files:
            meta = skill_frontmatter(sf)
            if meta is None:
                continue
            n = len(meta['description'])
            total += len(meta['name']) + n
            rows.append(f"         {meta['name']:<20} {n:>5}")
            if n > cap:
                over_cap.append(f"{meta['name']} ({n} chars)")
        if over_cap:
            say(f"[fail] {len(over_cap)} description(s) over the {cap}-character cap", 'red')
            for o in over_cap:
                say(f"         {o}", 'gray')
            errors.append(f"A description past {cap} characters is truncated regardless of budget. Put the key use case first and cut the rest.")

        pct = round(100 * total / args.listing_budget)
        msg = f"listing cost - {total} chars across {len(skill_files)} skill(s), {pct}% of a {args.listing_budget} budget"
        if total > args.listing_budget:
            say(f"[warn] {msg}", 'yellow')
            for r in rows:
                say(r, 'gray')
            warnings.append('The listing exceeds the assumed budget, so Claude Code may drop descriptions - which silently stops those skills from triggering. Check /context and /doctor, shorten descriptions, or move resource terms into the azure-resources description rather than adding skills - the iac-authoring description is the entry and stays short.')
        elif pct >= 70:
            say(f"[warn] {msg}", 'yellow')
            warnings.append('The listing is near its budget. Shorten descriptions before adding a skill - families are not skills and should not become them.')
        else:
            say(f"[ ok ] {msg}", 'green')

    # --- 4. plugin manifest paths ------------------------------------------
    manifest = os.path.join(plugin_root, '.claude-plugin', 'plugin.json')
    if not os.path.isfile(manifest):
        say('[info] no plugin.json', 'darkyellow')
    else:
        data = None
        try:
            data = json.loads(read(manifest))
        except json.JSONDecodeError as e:
            say(f"[fail] plugin.json does not parse: {e}", 'red')
            errors.append('plugin.json is not valid JSON, so the plugin cannot load.')
        if data is not None:
            declared = list(data.get('skills', [])) if isinstance(data, dict) else []
            missing = [d for d in declared if not os.path.exists(os.path.join(plugin_root, re.sub(r'^\./', '', d)))]
            # Any directory directly under the plugin root that holds skills but
            # is not declared would not be scanned.
            norm = [re.sub(r'/$', '', re.sub(r'^\./', '', d)) for d in declared]
            undeclared = []
            for entry in sorted(os.listdir(plugin_root)):
                full = os.path.join(plugin_root, entry)
                if not os.path.isdir(full) or entry in ('.claude-plugin', 'skills'):
                    continue
                if find_files(full, 'SKILL.md') and entry not in norm:
                    undeclared.append(entry)
            if not missing and not undeclared:
                say(f"[ ok ] plugin manifest - {len(declared)} declared scan path(s), all present", 'green')
            if missing:
                say(f"[fail] {len(missing)} declared skills path(s) do not exist", 'red')
                for m in missing:
                    say(f"         {m}", 'gray')
                errors.append('A declared skills path that does not exist fails to load the whole plugin. Remove the entry, or add it in the same commit as the first skill in that group.')
            if undeclared:
                say(f"[fail] {len(undeclared)} group director(ies) hold skills but are not declared", 'red')
                for u in undeclared:
                    say(f"         {u}/", 'gray')
                errors.append("The skills/ scan is one level deep and does not recurse, so an undeclared group directory loads nothing. Add it to plugin.json's skills array.")

    # --- 5. question sets --------------------------------------------------
    # Two shapes: a resource directory holding questions.yaml
    # (resources/<family>/<resource>/questions.yaml), and a set held by a
    # skill (core/iac-authoring/questions/deployment.yaml). Missing the first
    # shape makes every resource check pass vacuously.
    question_sets = []
    if os.path.isdir(plugin_root):
        for d, _, files in os.walk(plugin_root):
            for f in files:
                p = os.path.join(d, f).replace('\\', '/')
                if re.search(r'/questions/[^/]+\.ya?ml$', p) or re.search(r'/[^/]+/questions\.ya?ml$', p):
                    question_sets.append(os.path.join(d, f))
        question_sets.sort()

    if not question_sets:
        say('[info] no question sets yet', 'darkyellow')
    else:
        q_errors, q_warnings = [], []
        q_count = 0
        convention_file = os.path.join(plugin_root, 'core', 'iac-rendering', 'references', 'naming.default.yaml')
        convention = read(convention_file) if os.path.isfile(convention_file) else None
        if not convention:
            q_errors.append('core/iac-rendering/references/naming.default.yaml missing - the naming convention every question set mirrors')

        for qs in question_sets:
            r = rel(repo, qs)
            raw = read(qs)
            # A deployment-scoped set answers for the whole deployment and names
            # no resource, so the naming identifiers do not apply to it.
            is_deployment = re.search(r'^\s*scope:\s*deployment\s*$', raw, re.M) is not None

            if not is_deployment:
                tf = re.search(r'^\s*terraform:\s*"?([^"\r\n]+)"?\s*$', raw, re.M)
                bc = re.search(r'^\s*bicep:\s*"?([^"\r\n]+)"?\s*$', raw, re.M)
                ab = re.search(r'^\s*abbreviation:\s*"?([^"\r\n]+)"?\s*$', raw, re.M)
                if not tf:
                    q_errors.append(f"{r} - naming.terraform not declared")
                if not bc:
                    q_errors.append(f"{r} - naming.bicep not declared")
                if not ab:
                    q_errors.append(f"{r} - naming.abbreviation not declared; the Bicep side assembles the name from vars and has no other source for the prefix")
                if bc and re.match(r'^\s*\w+::', bc.group(1)):
                    q_errors.append(f"{r} - naming.bicep carries a cloud prefix ('{bc.group(1).strip()}'); the Bicep resource type takes none")
                if tf and '::' not in tf.group(1):
                    q_errors.append(f"{r} - naming.terraform is missing the '<Provider>::' prefix ('{tf.group(1).strip()}')")
                # The abbreviation mirrors the convention. Drift here means Bicep renders
                # one prefix and the Terraform provider another for the same resource.
                if ab and bc and convention:
                    t = re.escape(bc.group(1).strip())
                    conv = re.search(rf'^\s*{t}::default:\s*(\S*)\s*$', convention, re.M)
                    if not conv:
                        q_warnings.append(f"{r} - {bc.group(1).strip()} has no ::default abbreviation in naming.default.yaml")
                    elif conv.group(1) != ab.group(1).strip() and not re.search(
                            rf'^\s*{t}::\w+:\s*{re.escape(ab.group(1).strip())}\s*$', convention, re.M):
                        # A set may declare a per-kind variant (Microsoft.Web/sites::function)
                        # instead of the default; only an abbreviation no entry carries is drift.
                        q_errors.append(f"{r} - naming.abbreviation '{ab.group(1).strip()}' differs from the convention's '{conv.group(1)}'")

            # Per-entry structural rules. Split on the "- id:" boundaries, which
            # catch both group entries and question entries - a group carries
            # title: and questions: and has none of the per-question fields, so
            # it is skipped rather than reported as an incomplete question.
            blocks = re.split(r'^\s*-\s+id:\s*', raw, flags=re.M)[1:]
            q_blocks = [b for b in blocks
                        if not (re.search(r'^\s+title:', b, re.M) and re.search(r'^\s+questions:', b, re.M))]

            # Question ids must be unique within the set.
            ids = [re.match(r'(\S+)', b).group(1) if re.match(r'(\S+)', b) else '' for b in q_blocks]
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            if dupes:
                q_errors.append(f"{r} - duplicate question id(s): {', '.join(dupes)}. Ids are referenced by pattern pre-answers and written to the spec.")

            q_count += len(q_blocks)
            for b, qid in zip(q_blocks, ids):
                if not re.search(r'^\s+ask:', b, re.M):
                    q_warnings.append(f"{r} - '{qid}' has no ask, so there is no question to put to the user")
                has_default = re.search(r'^\s+default:', b, re.M) is not None
                has_required = re.search(r'^\s+required:\s*true', b, re.M) is not None
                # Inherited from the deployment set (copied, or derived through a map),
                # so it needs no default of its own.
                has_inherit = re.search(r'^\s+(from_deployment|derived_from):', b, re.M) is not None
                # Supplied at deploy time as an input variable, so it is never asked either.
                if re.search(r'^\s+parameterized:\s*true', b, re.M):
                    has_inherit = True
                if has_default and has_required:
                    q_errors.append(f"{r} - '{qid}' sets both required: true and a default. A required question is one with no safe default.")
                if has_inherit and (has_default or has_required):
                    q_errors.append(f"{r} - '{qid}' sets from_deployment or derived_from together with a default or required. The deployment answer is the default; a second one here is the ambiguity this field exists to remove.")
                if not has_default and not has_required and not has_inherit:
                    q_warnings.append(f"{r} - '{qid}' has neither a default, required: true, from_deployment nor derived_from, so it is unclear whether it gets asked")
                if not re.search(r'^\s+why:', b, re.M):
                    q_warnings.append(f"{r} - '{qid}' has no why. It is the only artefact that survives into a review.")
                if not re.search(r'^\s+renders:', b, re.M):
                    q_warnings.append(f"{r} - '{qid}' has no renders, so a review cannot map code back to this decision")

        if not q_errors:
            say(f"[ ok ] question sets - {len(question_sets)} file(s), {q_count} question(s)", 'green')
        else:
            say(f"[fail] question sets - {len(q_errors)} problem(s)", 'red')
            for e in q_errors:
                say(f"         {e}", 'gray')
            errors.append(f"{len(q_errors)} question-set error(s). The naming identifiers differ between targets and a wrong one renders a wrong name.")
        if q_warnings:
            say(f"[warn] question sets - {len(q_warnings)} incomplete question(s)", 'yellow')
            for w in q_warnings[:15]:
                say(f"         {w}", 'gray')
            if len(q_warnings) > 15:
                say(f"         ... and {len(q_warnings) - 15} more", 'gray')
            warnings.append('Questions missing why/renders, or with neither a default nor required. Judge whether the omission is intended.')

    # --- 6. routing coverage -----------------------------------------------
    if question_sets:
        route_issues = []
        families = sorted({os.path.dirname(os.path.dirname(q)) for q in question_sets})

        # A resource family routes through routing.md and is not a skill - the
        # azure-resources skill is the single trigger for all of them. A question
        # set inside a skill (the deployment set in iac-authoring) routes through
        # that skill's SKILL.md.
        azure_resources = os.path.join(plugin_root, 'core', 'azure-resources', 'SKILL.md')
        router_body = read(azure_resources) if os.path.isfile(azure_resources) else ''

        for fam_dir in families:
            fam_rel = rel(repo, fam_dir)
            router = os.path.join(fam_dir, 'routing.md')
            if not os.path.isfile(router):
                router = os.path.join(fam_dir, 'SKILL.md')
            router_leaf = os.path.basename(router)
            if not os.path.isfile(router):
                route_issues.append(f"{fam_rel} has question sets but neither routing.md nor SKILL.md to route to them")
                continue

            # A family nobody routes into is unreachable however good its table is.
            if router_leaf == 'routing.md':
                fam_name = os.path.basename(fam_dir)
                if f"resources/{fam_name}/routing.md" not in router_body:
                    route_issues.append(f"core/azure-resources/SKILL.md never links resources/{fam_name}/routing.md - the whole family is unreachable")

            body = read(router)
            for qs in question_sets:
                if os.path.dirname(os.path.dirname(qs)) != fam_dir:
                    continue
                # Every resource set is named questions.yaml, so the file name
                # alone matches any row; the resource directory is what identifies it.
                name = os.path.basename(qs)
                if re.match(r'^questions\.ya?ml$', name):
                    token = f"{os.path.basename(os.path.dirname(qs))}/{name}"
                else:
                    token = f"questions/{name}"
                if token not in body:
                    route_issues.append(f"{fam_rel}/{router_leaf} never mentions {token} - the resource is unreachable")
            # Rows pointing at a question set that does not exist, in either
            # shape. The lookbehind keeps a path-qualified reference out - a link
            # to core/iac-authoring/questions/deployment.yaml names another
            # skill's set and is not a route into this family.
            for m in re.finditer(r'(?<![\w./-])questions/([A-Za-z0-9._-]+\.ya?ml)', body):
                if not os.path.isfile(os.path.join(fam_dir, 'questions', m.group(1))):
                    route_issues.append(f"{fam_rel}/{router_leaf} routes to questions/{m.group(1)}, which does not exist")
            for m in re.finditer(r'(?<![\w./-])([a-z0-9][a-z0-9-]*)/questions\.ya?ml', body):
                if not os.path.isfile(os.path.join(fam_dir, m.group(1), 'questions.yaml')):
                    route_issues.append(f"{fam_rel}/{router_leaf} routes to {m.group(1)}/questions.yaml, which does not exist")

        if not route_issues:
            say('[ ok ] routing - every question set reachable from its routing table', 'green')
        else:
            say(f"[warn] routing - {len(route_issues)} issue(s)", 'yellow')
            for i in route_issues:
                say(f"         {i}", 'gray')
            warnings.append('A routing row pointing at a missing file is the one failure this repo cannot detect at runtime - the skill reads a missing file mid-run.')

    # --- 7. no CLAUDE.md inside the plugin ---------------------------------
    if os.path.isdir(plugin_root):
        strays = find_files(plugin_root, 'CLAUDE.md')
        if not strays:
            say('[ ok ] no CLAUDE.md inside the plugin directory', 'green')
        else:
            say(f"[fail] {len(strays)} CLAUDE.md inside the plugin directory", 'red')
            for s in strays:
                say(f"         {rel(repo, s)}", 'gray')
            errors.append('A CLAUDE.md in the plugin is not loaded as context and claude plugin validate warns about it. Instructions that must reach Claude belong in a skill; repo guidance belongs in the root CLAUDE.md.')

    # --- 7b. the plugin never refers to examples/ --------------------------
    if os.path.isdir(plugin_root):
        hits = []
        for t in tracked:
            if not t.startswith('plugins/') or '/evals/results/' in t:
                continue
            try:
                with open(os.path.join(repo, t), encoding='utf-8', errors='ignore') as fh:
                    for i, line in enumerate(fh, 1):
                        if 'examples/' in line:
                            hits.append(f"{t}:{i}")
            except OSError:
                continue
        if not hits:
            say('[ ok ] the plugin does not refer to examples/', 'green')
        else:
            say(f"[fail] {len(hits)} reference(s) to examples/ inside the plugin", 'red')
            for h in hits:
                say(f"         {h}", 'gray')
            errors.append('The plugin ships without examples/: a live deployment has neither the directory nor its specs. Skills, references, tests and fixtures carry what they need themselves and name no example.')

    # --- 7c. the CLAUDE.md block's text does not change without a new rev ---
    sync = os.path.join(plugin_root, 'core', 'iac-rendering', 'scripts', 'sync_claude_md.py')
    if os.path.isfile(sync):
        p = subprocess.run([sys.executable, sync, '--verify-lock'], capture_output=True, text=True)
        if p.returncode == 0:
            say('[ ok ] the CLAUDE.md block matches its lock (text and rev)', 'green')
        else:
            say('[fail] the CLAUDE.md block changed without a new rev', 'red')
            say(f"         {(p.stdout or p.stderr).strip()}", 'gray')
            errors.append('A customer repository only updates its CLAUDE.md section when rev rises. Bump rev in references/claude-md-block.md and write the line --verify-lock names into claude-md-block.lock.')

    # --- 7c2. every resource set has a resource group role in each scheme ---
    roles_file = os.path.join(plugin_root, 'core', 'iac-rendering', 'references', 'resource-group-roles.yaml')
    if os.path.isfile(roles_file):
        text = read(roles_file)
        lc = text.index('\nlifecycle:') if '\nlifecycle:' in text else len(text)
        listed = lambda part: {k.strip() for m in re.finditer(r'^\s+[a-z]+: \[([^\]]*)\]', part, re.M) for k in m.group(1).split(',')}
        attached = {k.strip() for m in re.finditer(r'^attached: \[([^\]]*)\]', text, re.M) for k in m.group(1).split(',')}
        concern, lifecycle = listed(text[:lc]) - {'main'}, listed(text[lc:]) - {'main'}
        sets = {os.path.basename(os.path.dirname(q)) for q in find_files(os.path.join(plugin_root, 'resources'), 'questions.yaml')}
        unplaced = sorted(f"{s} ({', '.join(n for n, t in (('concern', concern), ('lifecycle', lifecycle)) if s not in t)})"
                          for s in sets - attached if s not in concern or s not in lifecycle)
        if not unplaced:
            say(f"[ ok ] {len(sets)} resource set(s) each have a resource group role in every scheme", 'green')
        else:
            say(f"[fail] {len(unplaced)} resource set(s) without a resource group role", 'red')
            for h in unplaced:
                say(f"         {h}", 'gray')
            errors.append('A split has no main group, so a set without a role has no group to go into. Add it to resource-group-roles.yaml (concern and lifecycle), or to attached when it is deployed with another resource.')

    # --- 7d. every tracked spec is in canonical form ------------------------
    write_spec = os.path.join(plugin_root, 'core', 'iac-authoring', 'scripts', 'write_spec.py')
    specs = [t for t in tracked if os.path.basename(t) == 'infra-spec.yaml']
    if os.path.isfile(write_spec) and specs:
        loose = []
        for t in specs:
            p = subprocess.run([sys.executable, write_spec, os.path.join(repo, t), '--check'],
                               capture_output=True, text=True)
            if p.returncode == 1:
                loose.append(t)
            elif p.returncode != 0:
                loose.append(f"{t} - {(p.stdout or p.stderr).strip().splitlines()[-1].split(': ', 1)[-1]}")
        if not loose:
            say(f"[ ok ] {len(specs)} tracked spec(s) in canonical form", 'green')
        else:
            say(f"[fail] {len(loose)} tracked spec(s) not in canonical form", 'red')
            for h in loose:
                say(f"         {h}", 'gray')
            errors.append('A spec typed by hand diffs how it was typed, not what moved. Run core/iac-authoring/scripts/write_spec.py <spec> --no-stamp on it (without --no-stamp when its decisions were just made).')

    # --- 8. relative links + spaces in paths -------------------------------
    if args.skip_links:
        print('[skip] relative links')
    else:
        md_files = [t for t in tracked if t.endswith('.md')]
        broken = []
        for md in md_files:
            if not os.path.isfile(md):
                continue
            d = os.path.dirname(md) or '.'
            # Strip fenced blocks and inline code: a skill legitimately shows
            # "](target)" as an example, which is not a link.
            text = read(md)
            text = re.sub(r'```.*?```', '', text, flags=re.S)
            text = re.sub(r'`[^`\r\n]*`', '', text)
            for m in re.finditer(r'\]\(([^)]+)\)', text):
                target = m.group(1).strip()
                if re.match(r'^(https?:|mailto:|#)', target):
                    continue
                target = re.split(r'\s+', target)[0].split('#')[0]
                if not target.strip():
                    continue
                target = unquote(target)
                if not os.path.exists(os.path.join(d, target)):
                    broken.append(f"{md}  ->  {target}")
        if not broken:
            say(f"[ ok ] relative links - {len(md_files)} Markdown file(s), none broken", 'green')
        else:
            say(f"[fail] relative links - {len(broken)} broken", 'red')
            for b in broken:
                say(f"         {b}", 'gray')
            errors.append(f"{len(broken)} broken relative link(s) in tracked Markdown.")

    spaced = [t for t in tracked if ' ' in t]
    if not spaced:
        say('[ ok ] no spaces in tracked paths', 'green')
    else:
        say(f"[fail] {len(spaced)} tracked path(s) contain a space", 'red')
        for s in spaced:
            say(f"         {s}", 'gray')
        errors.append(f"{len(spaced)} tracked path(s) contain a space (breaks the shell and the script helpers).")

    # --- 9. the authoritative manifest check -------------------------------
    # `claude plugin validate` is the only check that reads the manifest the way
    # the loader does. The CLI is often not on PATH - the VS Code extension ships
    # its own binary - so look there before reporting it as unchecked.
    cli = shutil.which('claude')
    if not cli:
        home = os.environ.get('USERPROFILE') or os.path.expanduser('~')
        appdata = os.environ.get('APPDATA', '')
        for g in [
            os.path.join(home, '.vscode', 'extensions', 'anthropic.claude-code-*', 'resources', 'native-binary', 'claude.exe'),
            os.path.join(home, '.vscode-insiders', 'extensions', 'anthropic.claude-code-*', 'resources', 'native-binary', 'claude.exe'),
            os.path.join(home, '.cursor', 'extensions', 'anthropic.claude-code-*', 'resources', 'native-binary', 'claude.exe'),
            os.path.join(home, '.claude', 'local', 'claude*'),
            os.path.join(appdata, 'npm', 'claude.cmd') if appdata else '',
        ]:
            hits = sorted(glob.glob(g), reverse=True) if g else []
            if hits:
                cli = hits[0]
                break

    if not cli:
        say("[warn] manifests - 'claude' not found, so the authoritative check did not run", 'yellow')
        warnings.append('claude plugin validate could not run - the CLI is not on PATH and no bundled binary was found. It is the only check that reads plugin.json the way the loader does.')
    else:
        def validate(target):
            # The CLI prints UTF-8 (check marks); on Windows the default is cp1252 and
            # the reader thread dies, leaving stdout as None.
            p = subprocess.run([cli, 'plugin', 'validate', target], capture_output=True,
                               text=True, encoding='utf-8', errors='replace')
            return p.returncode, (p.stdout + p.stderr).splitlines()

        code, out = validate(plugin_root)
        m_code, m_out = validate(repo)
        if code == 0 and m_code == 0:
            say('[ ok ] manifests - plugin and marketplace validate', 'green')
            # Advice lines do not change the verdict, but they are worth seeing.
            for line in out + m_out:
                if re.match(r'^\s*❯', line):
                    say(f"       {line}", 'gray')
        else:
            say('[fail] manifests - claude plugin validate reported a problem', 'red')
            for line in out + m_out:
                say(f"         {line}", 'gray')
            errors.append('claude plugin validate failed. A manifest the loader rejects means the plugin does not load at all.')

    print('-' * 70)
    for w in warnings:
        say(f"  ! {w}", 'yellow')
    for e in errors:
        say(f"  X {e}", 'red')

    if errors:
        say(f"\n{len(errors)} error(s) - fix before committing.\n", 'red')
        return 1
    if warnings:
        say(f"\nNo errors, {len(warnings)} warning(s) to judge.\n", 'yellow')
        return 0
    say('\nAll checks passed.\n', 'green')
    return 0


if __name__ == '__main__':
    sys.exit(main())
