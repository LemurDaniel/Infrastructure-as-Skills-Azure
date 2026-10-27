#!/bin/sh
# Stage the case's fixed starting state: everything under workspace/ into the run's working
# directory. A file named *.in loses the suffix on the way (CLAUDE.md.in becomes CLAUDE.md): a
# CLAUDE.md may not sit inside the plugin directory, where it would never be loaded anyway.
set -e
cp -R "$(dirname "$0")/workspace/." .
find . -name '*.in' -type f | while read -r f; do mv "$f" "${f%.in}"; done
