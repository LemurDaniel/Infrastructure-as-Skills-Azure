---
name: release
description: Cut a release of the plugin - bump the version in plugin.json, tag it and let the GitHub workflow build the ZIP and publish it. Use when asked to release, publish, tag, cut a version, "Release", "veröffentlichen", "neue Version" or bump the version. While the version is 0.0.x every release is a prerelease.
---

# Releasing the plugin

A release is a tag `v<version>` on `master`. `.github/workflows/release.yml` runs on the
tag, fails if the tag differs from `version` in
`plugins/infrastructure-as-skills-azure/.claude-plugin/plugin.json`, runs the repository
checks, zips the plugin directory (tracked files only, via `git archive`) and creates the
GitHub release with a SHA-256 file. A `0.0.x` version, or a `-suffix`, makes it a
prerelease; `0.1.0` and later are stable releases. `0.0.x` was the early line, `0.1.0` is
the first stable release; a minor or major bump is the owner's call, never a default bump.

## Steps

1. **Clean tree, on `master`.** `git status -sb` shows no changes and the branch is not
   behind `origin/master`. Unpushed commits are fine, they go out with the push below.
2. **Pick the version.** Read the last tag (`git tag --sort=-v:refname | head -1`) and the
   manifest version. Next patch is the default (`0.0.3` -> `0.0.4`); say which one you
   chose. If the manifest and the last tag disagree, ask.
3. **Run the checks** the workflow runs, so it does not fail after the tag exists:
   `check_repo_consistency.py`, `check_question_set.py`, `run_diagram_tests.py`
   (commands in CLAUDE.md).
4. **Bump `version`** in `plugin.json` and nothing else. `marketplace.json` carries none.
5. **Rewrite `PROGRESS.md`** if the session changed it (see the commit conventions), then
   commit the bump as `Release <version>`, following
   [git-commit-conventions](../git-commit-conventions/SKILL.md): no attribution lines.
6. **Tag:** `git tag -a v<version> -m "<version>"`.
7. **Push only when asked.** Committing and tagging are local and reversible; the push of
   the tag starts the workflow and publishes. Confirm with the user, then
   `git push origin master` and `git push origin v<version>`. Never `--force`, never move
   a tag that is pushed; a bad release is fixed by the next version.
8. **Report** the version, whether it is pushed, and that the workflow decides the rest:
   `gh run list --workflow release.yml --limit 1` shows it, `gh release view v<version>`
   the result.

## Never

- Tag from a branch other than `master`, or with a dirty tree.
- Edit or delete a published release or tag without being asked.
- Put the remote URL anywhere: the `origin` URL embeds a token.
