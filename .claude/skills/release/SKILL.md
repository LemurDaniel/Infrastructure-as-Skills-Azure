---
name: release
description: Releasing the plugin - every merge of a pull request into master publishes the version in plugin.json, so every branch raises it before the PR. Use when bumping the version, opening a PR, or asked to release, publish, tag, cut a version, "Release", "veröffentlichen", "neue Version". A 0.0.x or suffixed version is a prerelease.
---

# Releasing the plugin

**A merge into `master` is a release.** `.github/workflows/release.yml` runs on every push
to `master`, reads `version` from
`plugins/infrastructure-as-skills-azure/.claude-plugin/plugin.json`, fails if `v<version>`
already exists, runs the repository checks, zips the plugin directory (tracked files only,
via `git archive`), and creates the tag `v<version>` on the merged commit with the GitHub
release and a SHA-256 file. A `0.0.x` version, or a `-suffix`, makes it a prerelease;
`0.1.0` and later are stable releases.

`.github/workflows/pull-request.yml` blocks the merge unless the version is raised:
`scripts/check_version_bump.py` fails when `plugin.json` is not newer than the last `v*`
tag and the version on the base branch. So **every branch bumps the version**, there is
no separate release step.

## Steps, in the branch before the PR

1. **Pick the version.** Read the last tag (`git fetch --tags`, then
   `git tag --sort=-v:refname | head -1`) and the manifest version on `origin/master`.
   Next patch is the default (`0.4.0` -> `0.4.1`); say which one you chose. A minor or
   major bump is the owner's call, never a default. If the manifest and the last tag
   disagree, ask.
2. **Bump `version`** in `plugin.json` and nothing else. `marketplace.json` carries none.
   Commit it on its own as `Bump the version to <version>`, following
   [git-commit-conventions](../git-commit-conventions/SKILL.md).
3. **Check:** `python3 .claude/skills/release/scripts/check_version_bump.py` and the
   repository checks the workflow runs (`check_repo_consistency.py`,
   `check_question_set.py`, `run_diagram_tests.py`; commands in CLAUDE.md).
4. **A branch that was overtaken** - another PR merged with the same version - bumps
   again after rebasing on `origin/master`; the PR check fails until it does.
5. **After the merge, report** what the workflow did:
   `gh run list --workflow release.yml --limit 1`, then `gh release view v<version>`.

## Never

- Create or push a `v*` tag by hand: the release workflow creates it.
- Merge a PR without being asked; the merge publishes.
- Edit or delete a published release or tag without being asked. A bad release is fixed
  by the next version.
- Put the remote URL anywhere: the `origin` URL embeds a token.
