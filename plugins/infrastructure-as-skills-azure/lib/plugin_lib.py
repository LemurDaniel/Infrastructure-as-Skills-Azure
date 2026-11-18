"""What every script of the plugin needs, written once: where the plugin's files are, how a
script speaks and exits, and how the question sets are found and read.

Each script used to carry its own copy - eight ways to find a question set, nine colour
printers, three exit codes for "PyYAML is missing" - and the copies had drifted: one check
warned where another failed, one script exited 1 where the skills expect 2. A script imports
this module from `<plugin>/lib`:

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'lib'))
    import plugin_lib

Not for a script the render copies into a customer's repository (`run_arm_tests.py`): that
one runs where this module does not exist and stays self-contained.

Exit codes, the same for every script: 0 clean, 1 the check found something, 2 the script
could not run (no parser, no file); 3 is the version gate's alone.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.abspath(os.path.join(HERE, '..'))
CORE = os.path.join(PLUGIN, 'core')
RESOURCES = os.path.join(PLUGIN, 'resources')
PATTERNS = os.path.join(PLUGIN, 'patterns')
DEPLOYMENT_SET = os.path.join(CORE, 'iac-authoring', 'questions', 'deployment.yaml')

COULD_NOT_RUN = 2


# ---------------------------------------------------------------------------
# Speaking
# ---------------------------------------------------------------------------

COLORS = {'cyan': '36', 'green': '32', 'red': '31', 'yellow': '33', 'gray': '90', 'darkyellow': '33'}
USE_COLOR = sys.stdout.isatty() and not os.environ.get('NO_COLOR')


def say(text, color=None):
    """One line, coloured on a terminal that takes colour and plain everywhere else."""
    if color and USE_COLOR and color in COLORS:
        print(f"\033[{COLORS[color]}m{text}\033[0m")
    else:
        print(text)


def ok(text):
    say(f"[ ok ] {text}", 'green')


def bad(text):
    say(f"[fail] {text}", 'red')


def warn(text):
    say(f"[warn] {text}", 'yellow')


def require_yaml():
    """The yaml module - or the one message every script gives without it, and exit 2: a
    script that cannot parse has not checked anything and must not look as if it passed."""
    try:
        import yaml
    except ImportError:
        bad('no YAML parser available')
        say('       Install one and re-run:', 'gray')
        say('         pip install pyyaml', 'gray')
        sys.exit(COULD_NOT_RUN)
    return yaml


# ---------------------------------------------------------------------------
# The question sets
# ---------------------------------------------------------------------------

def set_paths():
    """{set name: its questions.yaml} for every resource set, by family then name. The set's
    name is its directory's (`storage-account`), which is also a resource's key in a spec."""
    found = {}
    if os.path.isdir(RESOURCES):
        for family in sorted(os.listdir(RESOURCES)):
            family_dir = os.path.join(RESOURCES, family)
            if not os.path.isdir(family_dir):
                continue
            for name in sorted(os.listdir(family_dir)):
                path = os.path.join(family_dir, name, 'questions.yaml')
                if os.path.isfile(path):
                    found[name] = path
    return found


def set_path(name):
    """The questions.yaml of a set name, whichever family holds it; None when there is none."""
    if not os.path.isdir(RESOURCES):
        return None
    for family in sorted(os.listdir(RESOURCES)):
        path = os.path.join(RESOURCES, family, name, 'questions.yaml')
        if os.path.isfile(path):
            return path
    return None


def family_of(name):
    """The family directory a set lives in, or None."""
    path = set_path(name)
    return os.path.basename(os.path.dirname(os.path.dirname(path))) if path else None


def set_name(key):
    """The set of a resource key in a spec: `app-service` for `app-service__chat`."""
    return str(key).split('__')[0]


def load(path, yaml):
    """A YAML file parsed; an empty file is an empty mapping."""
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def questions_of(doc):
    """(group id, question) for every question of a parsed set, in the file's order."""
    for group in (doc.get('groups') or []) if isinstance(doc, dict) else []:
        if not isinstance(group, dict):
            continue
        for question in group.get('questions') or []:
            if isinstance(question, dict):
                yield group.get('id'), question


def question_index(yaml):
    """{(set name or 'deployment', question id): question} over the deployment set and every
    resource set, each question carrying its group as `_group`."""
    index = {}

    def add(owner, path):
        for group, question in questions_of(load(path, yaml)):
            if question.get('id'):
                index[(owner, question['id'])] = dict(question, _group=group)

    if os.path.isfile(DEPLOYMENT_SET):
        add('deployment', DEPLOYMENT_SET)
    for name, path in set_paths().items():
        add(name, path)
    return index
