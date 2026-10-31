#!/usr/bin/env python3
"""Checks the comments of rendered files against references/code-structure.md.

Read-only. Standard library only, Python 3.9+. Reads every Terraform (.tf, .tftest.hcl,
.tfvars), Bicep (.bicep, .bicepparam) and YAML file under the paths given and checks what a
reviewer would otherwise count by eye:

  1. The file opens with a comment: its header.
  2. Every banner line is 75 characters after the comment mark and one space; a chapter
     title is UPPERCASE and centered.
  3. A chapter has a description; its numbered steps name the sections that follow, in order.
  4. A section has a title and a description, closed by a second line; it stands inside a
     chapter, except the header of a YAML file.
  5. A file with chapters lists them in a table of contents ("Chapters:"), in file order.
     A Terraform root or module lists the chapters of all its .tf files in the header of
     providers.tf instead, or of variables.tf in a module without one.

A file the repository wrote in its own style is not this check's to judge: run it on the
files the render wrote.

Usage:
    python3 check_code_structure.py <file or directory>...

Exit 0 clean, 1 violations, 2 nothing to check.
"""

#
#   Chapters:
#     HELPERS                        Comment text, banner rules and the files to read.
#     READ ONE FILE                  Table of contents, chapters and sections of a file.
#     CHECK THE TABLES OF CONTENTS   Each list against the chapters it names.
#     CHECK THE RENDER               Reads every file, then reports.
#

import os
import re
import sys

WIDTH = 75
MIN_RULE_LENGTH = 20
COMMENT_MARKS = {
    '.tf': '#', '.hcl': '#', '.tfvars': '#',
    '.yaml': '#', '.yml': '#',
    '.bicep': '//', '.bicepparam': '//',
}
SKIPPED_DIRS = {'.git', '.terraform', 'node_modules'}
TERRAFORM_TOC_HOLDERS = ('providers.tf', 'variables.tf')

# Indentation counted after the comment mark and its one space: `#   1. Plan` reads `  1. Plan`.
RULE_RE = re.compile(r'^(=+|-+)$')
TITLE_RE = re.compile(r'^(=+)   (.+?)   (=+)$')
STEP_RE = re.compile(r'^ {2}\d+\. (.+?)(?: {2,}\S.*)?$')
TOC_ENTRY_RE = re.compile(r'^ {4}(\S.*?)(?: {2,}\S.*)?$')

errors = []     # filled by every chapter, reported in CHECK THE RENDER


# ===========================================================================
# ===============================   HELPERS   ===============================
# ===========================================================================
#
#   err            Records one violation with its place.
#   comment_text   The text of a comment line, None for code.
#   is_rule        Whether a comment text is a banner line of = or -.
#   mark_of        The comment mark of a file type, None when it is not checked.
#   files_under    Every file under the paths given.
#

def err(where, message):
    """Records one violation.

    where    (Required) `path` or `path:line`.
    message  (Required) What is wrong and what is expected instead.

    err('main.bicep:3', 'banner line is 72 characters, not 75')
    """
    errors.append(f"{where}: {message}")


def comment_text(line, mark):
    """Returns the text of a comment line without its mark and one space, or None for code.

    line  (Required) One line of the file.
    mark  (Required) The file's comment mark, '#' or '//'.

    comment_text('  #   1. Plan', '#')  => '  1. Plan'
    comment_text('plan:', '#')          => None
    """
    stripped = line.strip()
    if not stripped.startswith(mark):
        return None
    rest = stripped[len(mark):]
    return rest[1:] if rest.startswith(' ') else rest


def is_rule(text, char):
    """Whether a comment text is a banner line made of `char` alone.

    text  (Required) A comment text from comment_text, or None.
    char  (Required) '=' for a chapter, '-' for a section.
    """
    return (
        text is not None
        and len(text) >= MIN_RULE_LENGTH
        and RULE_RE.match(text) is not None
        and text[0] == char
    )


def mark_of(path):
    """Returns the comment mark of a checked file type, None for any other file.

    path  (Required) A file path.

    mark_of('tests/security.tftest.hcl')  => '#'
    mark_of('README.md')                  => None
    """
    if path.endswith('.tftest.hcl'):
        return '#'
    return COMMENT_MARKS.get(os.path.splitext(path)[1])


def files_under(paths):
    """Yields every file under the paths given, in a stable order, skipping tool directories.

    paths  (Required) Files or directories.
    """
    for path in paths:
        if os.path.isfile(path):
            yield path
            continue
        for root, dirs, names in os.walk(path):
            dirs[:] = sorted(d for d in dirs if d not in SKIPPED_DIRS)
            for name in sorted(names):
                yield os.path.join(root, name)


# ===========================================================================
# ============================   READ ONE FILE   ============================
# ===========================================================================
#
#   read_toc       The entries of a `Chapters:` block.
#   read_chapter   One chapter banner and its description.
#   read_section   One section banner, its title and description.
#   read_file      Walks one file and returns its chapters and table of contents.
#
#   Every reader takes the index of the line it starts on and returns the index after
#   the last line it read, so read_file walks on from there.
#

def read_toc(path, texts, start):
    """Reads the entries below a `Chapters:` line.

    path   (Required) The file, for messages.
    texts  (Required) The comment text of every line, None for code.
    start  (Required) Index of the `Chapters:` line.

    Returns (entries, next index).
    """
    entries, i = [], start + 1
    while i < len(texts) and texts[i] not in (None, ''):
        match = TOC_ENTRY_RE.match(texts[i])
        if match:
            entries.append(match.group(1))
        i += 1
    return entries, i


def read_chapter(path, texts, start):
    """Reads a chapter: rule, title, rule, then the description between empty comment lines.

    path   (Required) The file, for messages.
    texts  (Required) The comment text of every line, None for code.
    start  (Required) Index of the first `=` line.

    Returns (chapter or None, next index). A chapter is a dict with title, line, the
    numbered steps of its description and the sections read_file adds to it.
    """
    title_text = texts[start + 1] if start + 1 < len(texts) else None
    closing = texts[start + 2] if start + 2 < len(texts) else None
    match = TITLE_RE.match(title_text or '')
    if not match or not is_rule(closing, '='):
        err(f"{path}:{start + 1}", "a `=` line that opens no chapter - a chapter is three lines: rule, title, rule")
        return None, start + 1

    # Banner
    for k in range(start, start + 3):
        if len(texts[k]) != WIDTH:
            err(f"{path}:{k + 1}", f"banner line is {len(texts[k])} characters, not {WIDTH}")
    left, title, right = match.groups()
    if title != title.upper():
        err(f"{path}:{start + 2}", f"chapter title `{title}` is not UPPERCASE")
    if abs(len(left) - len(right)) > 1:
        err(f"{path}:{start + 2}", f"chapter title `{title}` is not centered ({len(left)} and {len(right)} `=`)")
    chapter = {'title': title, 'line': start + 2, 'steps': [], 'sections': []}

    # Description: an empty comment line, the entries, an empty comment line.
    i = start + 3
    if i >= len(texts) or texts[i] != '':
        err(f"{path}:{i + 1}", f"chapter {title} has no description below its banner")
        return chapter, i
    i += 1
    entry_count = 0
    while i < len(texts) and texts[i] not in (None, ''):
        entry_count += 1
        step = STEP_RE.match(texts[i])
        if step:
            chapter['steps'].append(step.group(1))
        i += 1
    if entry_count == 0:
        err(f"{path}:{i}", f"chapter {title} has no description below its banner")
    return chapter, i


def read_section(path, texts, start):
    """Reads a section: rule, title, description indented by three spaces, rule.

    path   (Required) The file, for messages.
    texts  (Required) The comment text of every line, None for code.
    start  (Required) Index of the first `-` line.

    Returns (title or None, next index).
    """
    end = start + 1
    while end < len(texts) and texts[end] is not None and not is_rule(texts[end], '-'):
        end += 1
    if end >= len(texts) or not is_rule(texts[end], '-'):
        err(f"{path}:{start + 1}", "a section that is never closed - a section ends with a second `-` line")
        return None, start + 1

    for k in (start, end):
        if len(texts[k]) != WIDTH:
            err(f"{path}:{k + 1}", f"banner line is {len(texts[k])} characters, not {WIDTH}")
    body = texts[start + 1:end]
    title = body[0] if body else ''
    if not title or title.startswith(' '):
        err(f"{path}:{start + 1}", "a section without a title on its first line")
    elif not any(line.startswith('  ') and line.strip() for line in body[1:]):
        err(f"{path}:{start + 1}", f"section `{title}` has no description indented by three spaces")
    return title or None, end + 1


def read_file(path, mark):
    """Walks one file and reports its malformed header, banners and steps.

    path  (Required) The file.
    mark  (Required) Its comment mark, from mark_of.

    Returns (chapters, table of contents or None).
    """
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    texts = [comment_text(line, mark) for line in lines]

    # Header
    first_line = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first_line is not None and texts[first_line] is None:
        err(path, "does not open with a comment - every rendered file starts with its header")
    is_yaml = path.endswith(('.yaml', '.yml'))

    # Banners, in file order
    chapters, toc, i = [], None, 0
    while i < len(texts):
        text = texts[i]
        if text is not None and text.strip() == 'Chapters:':
            toc, i = read_toc(path, texts, i)
        elif is_rule(text, '='):
            chapter, i = read_chapter(path, texts, i)
            if chapter:
                chapters.append(chapter)
        elif is_rule(text, '-'):
            is_yaml_header = is_yaml and i == first_line
            start = i
            title, i = read_section(path, texts, i)
            if title and chapters:
                chapters[-1]['sections'].append(title)
            elif title and not is_yaml_header:
                err(f"{path}:{start + 1}", f"section `{title}` stands outside a chapter - every section lives inside one")
        else:
            i += 1

    # Numbered steps name the sections
    for chapter in chapters:
        if chapter['steps'] and chapter['steps'] != chapter['sections']:
            err(f"{path}:{chapter['line']}",
                f"chapter {chapter['title']} numbers {chapter['steps']}, its sections are {chapter['sections']}")
    return chapters, toc


# ===========================================================================
# ====================   CHECK THE TABLES OF CONTENTS   =====================
# ===========================================================================
#
#   check_tocs   Each file's list against its chapters, a Terraform root's list
#                against the chapters of all its .tf files.
#

def check_tocs(parsed):
    """Reports a missing or stale table of contents.

    parsed  (Required) {path: (chapters, toc)} from read_file.
    """
    # Every file but a root .tf carries its own list, in file order.
    roots = {}
    for path, (chapters, toc) in parsed.items():
        if path.endswith('.tf'):
            roots.setdefault(os.path.dirname(path), []).append(path)
            continue
        titles = [c['title'] for c in chapters]
        if titles and toc is None:
            err(path, f"has chapters {titles} but no table of contents (`Chapters:` below the header)")
        elif toc is not None and toc != titles:
            err(path, f"table of contents lists {toc}, the chapters are {titles}")

    # A Terraform root is one book: its list sits in providers.tf, or variables.tf in a module without one.
    for root, paths in roots.items():
        titles = [c['title'] for path in paths for c in parsed[path][0]]
        if not titles:
            continue
        holder = next((os.path.join(root, n) for n in TERRAFORM_TOC_HOLDERS if os.path.join(root, n) in parsed), None)
        toc = parsed[holder][1] if holder else None
        if toc is None:
            err(root or '.', f"Terraform root has chapters {titles} but lists none (`Chapters:` in the header of providers.tf)")
        elif sorted(toc) != sorted(titles):
            err(holder, f"table of contents lists {sorted(toc)}, the root's chapters are {sorted(titles)}")


# ===========================================================================
# ==========================   CHECK THE RENDER   ===========================
# ===========================================================================
#
#   main   Reads every checked file under the paths, checks the lists, reports.
#

def main(paths):
    """Checks the files under the paths and prints one line per violation.

    paths  (Required) Files or directories, the render's root as a rule.

    Returns the exit code: 0 clean, 1 violations, 2 nothing to check.

    main(['eval-agent/infra'])
    """
    if not paths:
        print("usage: check_code_structure.py <file or directory>...")
        return 2

    parsed = {}
    for path in files_under(paths):
        mark = mark_of(path)
        if mark:
            parsed[path] = read_file(path, mark)
    if not parsed:
        print("nothing to check: no Terraform, Bicep or YAML file under the paths given")
        return 2
    check_tocs(parsed)

    print(f"Code structure - {len(parsed)} file(s)")
    for error in errors:
        print(f"[fail] {error}")
    if not errors:
        print("[ ok ] headers, banners, chapters, sections and tables of contents")
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
