---
name: release
description: Releasing the plugin - every merge of dev into master publishes the version in plugin.json, so the release pull request raises it. Use when bumping the version, opening a PR, or asked to release, publish, tag, cut a version, "Release", "veröffentlichen", "neue Version". A 0.0.x or suffixed version is a prerelease.
---

# Releasing the plugin

**A merge into `master` is a release.** Feature branches go into `dev` (which deploys the
eval agent and releases nothing); `dev` goes into `master` by a release pull request, merged
as a merge commit. `.github/workflows/release.plugin.yaml` runs on every push
to `master`, reads `version` from
`plugins/infrastructure-as-skills-azure/.claude-plugin/plugin.json`, fails if `v<version>`
already exists, runs the repository checks, zips the plugin directory (tracked files only,
via `git archive`), and creates the tag `v<version>` on the merged commit with the GitHub
release and a SHA-256 file. A `0.0.x` version, or a `-suffix`, makes it a prerelease;
`0.1.0` and later are stable releases.

`.github/workflows/check.pull-request.yaml` blocks a pull request into `master` unless it comes
from `dev` and the version is raised: `scripts/check_version_bump.py` fails when
`plugin.json` is not newer than the last `v*` tag and the version on `master`. So **the
release bumps the version**, once for everything `dev` collected; a feature branch does not.

## Steps, on a branch into `dev`, before the release PR

1. **Pick the version.** Read the last tag (`git fetch --tags`, then
   `git tag --sort=-v:refname | head -1`) and the manifest version on `origin/master`.
   Next patch is the default (`0.4.0` -> `0.4.1`); say which one you chose. A minor or
   major bump is the owner's call, never a default. If the manifest and the last tag
   disagree, ask.
2. **Bump `version`** in `plugin.json` and nothing else. `marketplace.json` carries none.
   Commit it on its own as `Bump the version to <version>` on a branch cut from
   `origin/dev`, and merge that into `dev` first, following
   [git-commit-conventions](../git-commit-conventions/SKILL.md).
3. **Check:** `python3 .claude/skills/release/scripts/check_version_bump.py` and the
   repository checks the workflow runs (`check_repo_consistency.py`,
   `check_question_set.py`, `run_diagram_tests.py`; commands in CLAUDE.md).
4. **Open the release PR** when asked: `gh pr create --base master --head dev`, title
   `Release <version>`, the body listing what `dev` collected since the last tag.
5. **Before the merge**, a release that changes the plugin's skills, resources or evals gets
   the full eval suite on Sonnet and on Haiku, run locally by test agents
   ([git-commit-conventions](../git-commit-conventions/SKILL.md), section 5); the pull
   request runs no eval.
6. **Merge as a merge commit** (`gh pr merge <n> --merge`), never squash: `dev` and
   `master` keep one history. **After the merge, report** what the workflow did:
   `gh run list --workflow release.plugin.yaml --limit 1`, then `gh release view v<version>`.

## Never

- Create or push a `v*` tag by hand: the release workflow creates it.
- Merge a PR without being asked; the merge into `master` publishes.
- Open a PR into `master` from anything but `dev`.
- Edit or delete a published release or tag without being asked. A bad release is fixed
  by the next version.
- Put the remote URL anywhere: the `origin` URL embeds a token.
