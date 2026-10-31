# NOTE:
#   Requires: Python 3.9+ with PyYAML (pip install pyyaml), run from the repository root.
#   The checks a pull request and a release both run (check.pull-request.yaml, release.plugin.yaml).
#
#   ./.github/scripts/Invoke-RepositoryChecks.ps1                  # Linux, macOS, CI
#   ./.github/scripts/Invoke-RepositoryChecks.ps1 -Python python   # Windows

param (
    <#
    [Optional]
    The Python interpreter. Defaults to 'python3'; on Windows 'python' or 'py'.
    #>
    [Parameter()]
    [System.String]
    $Python = 'python3'
)

Set-StrictMode -Version 1.0
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$PLUGIN_DIR = 'plugins/infrastructure-as-skills-azure'

# A failing check throws and stops the run; the order is cheapest first.
& $Python .claude/skills/git-commit-conventions/scripts/check_repo_consistency.py
& $Python "$PLUGIN_DIR/core/iac-authoring/scripts/check_question_set.py"
& $Python "$PLUGIN_DIR/core/iac-authoring/tests/run_interview_digest_tests.py"
& $Python "$PLUGIN_DIR/core/iac-diagram/tests/run_diagram_tests.py"
