# NOTE:
#   Requires: the Claude Code CLI (claude) and python3 on PATH, ANTHROPIC_API_KEY set,
#   run from the repository root. Called by eval.plugin.yaml.
#
#   ./.github/scripts/Invoke-PluginEvalSuite.ps1 -OutputDir $env:RUNNER_TEMP/eval -Model sonnet -MaxCostUsd 30
#   ./.github/scripts/Invoke-PluginEvalSuite.ps1 -OutputDir ./eval -Model haiku -MaxCostUsd 5 -Runs 2 -Tag terraform
#
#   One case per call, so the log says which case runs, how far along the suite is and how
#   long the rest will take (the average of the cases so far); the CLI itself prints only the
#   final table. Each call gets what is left of the cost ceiling. Report only: a failing case
#   does not fail the run, a case without a result does.

#
#   Chapters:
#     HELPERS          Duration format and the cost of a case result.
#     SELECT CASES     Validations and the cases that match name and tag.
#     RUN THE CASES    One eval call per case, then the merged result.
#

param (
    <#
    [Required]
    The directory the case results and the merged aggregate-result.json are written to.
    #>
    [Parameter(Mandatory = $true)]
    [System.String]
    $OutputDir,

    <#
    [Required]
    The model the agent runs on: sonnet, haiku or opus.
    #>
    [Parameter(Mandatory = $true)]
    [ValidateSet('sonnet', 'haiku', 'opus')]
    [System.String]
    $Model,

    <#
    [Required]
    The hard cost ceiling of the whole suite in USD.
    #>
    [Parameter(Mandatory = $true)]
    [System.Double]
    $MaxCostUsd,

    <#
    [Optional]
    Runs for every case, run in parallel up to 8. Empty runs each case's own `runs:` from prompt.md.
    #>
    [Parameter()]
    [System.String]
    $Runs = '',

    <#
    [Optional]
    Case name glob (e.g. 'spec-*'). Empty runs all cases.
    #>
    [Parameter()]
    [System.String]
    $Case = '',

    <#
    [Optional]
    Only cases whose prompt.md frontmatter carries this tag. Empty runs all cases.
    #>
    [Parameter()]
    [System.String]
    $Tag = ''
)

Set-StrictMode -Version 1.0
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$PLUGIN_DIR   = 'plugins/infrastructure-as-skills-azure'
$MAX_PARALLEL = 8

# ===========================================================================
# ===============================   HELPERS   ===============================
# ===========================================================================
#
#   Format-Duration   Seconds as 3m07s.
#   Get-CaseCost      The costUsd of a case result, 0 when it has none.
#

function Format-Duration {
    param ([System.Int32] $Seconds)
    return '{0}m{1:d2}s' -f [System.Math]::Floor($Seconds / 60), ($Seconds % 60)
}

function Get-CaseCost {
    param ([System.String] $ResultPath)
    $Result = Get-Content -Path $ResultPath -Raw | ConvertFrom-Json
    return [System.Double] ($Result.costUsd ?? 0)
}

# ===========================================================================
# ============================   SELECT CASES   =============================
# ===========================================================================
#
#   1. Validations   Fails early without an API key.
#   2. Cases         Every case directory that matches the name glob and the tag.
#

# ---------------------------------------------------------------------------
# Validations
#   Fails early without an API key.
# ---------------------------------------------------------------------------

if ([System.String]::IsNullOrEmpty($env:ANTHROPIC_API_KEY)) {
    Write-Output '::error::the repository secret ANTHROPIC_API_KEY is not set'
    exit 1
}

# ---------------------------------------------------------------------------
# Cases
#   Every case directory that matches the name glob and the tag.
# ---------------------------------------------------------------------------

# The tags are in the prompt.md frontmatter: tags: [pr, terraform, ...]
$TagPattern = '^tags:.*[\[ ,]' + [System.Text.RegularExpressions.Regex]::Escape($Tag) + '[\],]'

$Cases = Get-ChildItem -Path "$PLUGIN_DIR/evals" -Filter case.yaml -File -Recurse
| Where-Object { $_.FullName -NOTMATCH '[\\/]results[\\/]' }
| ForEach-Object { $_.Directory }
| Where-Object { [System.String]::IsNullOrEmpty($Case) -OR $_.Name -LIKE $Case }
| Where-Object { [System.String]::IsNullOrEmpty($Tag) -OR (Select-String -Path "$($_.FullName)/prompt.md" -Pattern $TagPattern -Quiet) }
| Sort-Object -Property FullName -Culture 'en-US'
| ForEach-Object { $_.Name }

$Cases = @($Cases)
if ($Cases.Count -EQ 0) {
    Write-Output "::error::no case matches case '$Case' and tag '$Tag'"
    exit 1
}

# Without -Runs each case runs its own `runs:` from prompt.md; --runs would override them all.
$RunsArgs = @()
$Parallel = $MAX_PARALLEL
if (-NOT [System.String]::IsNullOrEmpty($Runs)) {
    $RunsArgs = @('--runs', $Runs)
    $Parallel = [System.Math]::Min([System.Int32] $Runs, $MAX_PARALLEL)
}

$RunsLabel = [System.String]::IsNullOrEmpty($Runs) ? "the case's own" : $Runs
$TagLabel  = [System.String]::IsNullOrEmpty($Tag) ? '' : " tagged $Tag"
Write-Output "$($Cases.Count) case(s)$TagLabel on $Model, $RunsLabel run(s) each, ceiling `$$($MaxCostUsd): $($Cases -join ' ')"

# ===========================================================================
# ============================   RUN THE CASES   ============================
# ===========================================================================
#
#   1. Cases    One eval call per case with what is left of the cost ceiling.
#   2. Merge    Merges the case results into one aggregate-result.json.
#

# ---------------------------------------------------------------------------
# Cases
#   One eval call per case with what is left of the cost ceiling.
# ---------------------------------------------------------------------------

$null = New-Item -Path "$OutputDir/cases" -ItemType Directory -Force
$StartedAt = Get-Date
$Spent     = 0.0     # reported per case and at the end
$IsPartial = $false  # set when the ceiling stops the suite early

for ($i = 0; $i -LT $Cases.Count; $i++) {
    $Name    = $Cases[$i]
    $Elapsed = [System.Int32] ((Get-Date) - $StartedAt).TotalSeconds
    $Eta     = $i -EQ 0 ? 'first case' : "about $(Format-Duration ([System.Int32] ($Elapsed / $i * ($Cases.Count - $i)))) left"
    $Budget  = [System.Math]::Round([System.Math]::Max(0.0, $MaxCostUsd - $Spent), 2)

    if ($Budget -LE 0) {
        Write-Output "::warning::cost ceiling `$$MaxCostUsd reached after $i of $($Cases.Count) case(s); the rest is skipped"
        $IsPartial = $true
        break
    }

    Write-Output "::group::[$($i + 1)/$($Cases.Count)] $Name - $(Format-Duration $Elapsed) elapsed, $Eta, `$$Spent spent"
    $CaseStartedAt = Get-Date
    $CaseDir       = "$OutputDir/cases/$Name"

    # --threshold 0: report only. Exit 2 is the cost ceiling - partial results, still recorded.
    # --scaffold: the sync cases stage a repository first, and this is our own suite.
    $EvalArgs = @(
        'plugin', 'eval', $PLUGIN_DIR, '--case', $Name
        '--model', $Model, '--judge-model', 'sonnet'
    ) + $RunsArgs + @(
        '-j', $Parallel, '--ablation', 'none', '--max-cost-usd', $Budget
        '--allow-tools', 'Write', 'Edit', '--trust-plugin', '--scaffold', '--no-publish', '--threshold', '0'
        '--output-dir', $CaseDir, '--report', "$CaseDir/report.html"
    )
    # Its exit code is reported, never thrown: a failing case is a result, not a broken run.
    $PSNativeCommandUseErrorActionPreference = $false
    claude @EvalArgs
    $ExitCode = $LASTEXITCODE
    $PSNativeCommandUseErrorActionPreference = $true
    Write-Output '::endgroup::'

    $ResultPath = "$CaseDir/aggregate-result.json"
    if (-NOT (Test-Path -Path $ResultPath)) {
        Write-Output "::error::[$($i + 1)/$($Cases.Count)] $Name produced no result (exit $ExitCode)"
        continue
    }
    $Spent = [System.Math]::Round($Spent + (Get-CaseCost -ResultPath $ResultPath), 2)
    $CaseSeconds = [System.Int32] ((Get-Date) - $CaseStartedAt).TotalSeconds
    Write-Output "[$($i + 1)/$($Cases.Count)] $Name done in $(Format-Duration $CaseSeconds), exit $ExitCode, `$$Spent spent so far"
}

# ---------------------------------------------------------------------------
# Merge
#   Merges the case results into one aggregate-result.json.
# ---------------------------------------------------------------------------

$Results = @(Get-ChildItem -Path "$OutputDir/cases/*/aggregate-result.json" -File | ForEach-Object { $_.FullName })
if ($Results.Count -EQ 0) {
    Write-Output '::error::no case produced a result'
    exit 1
}

$MergeArgs = $Results + @('--out', "$OutputDir/aggregate-result.json")
if ($IsPartial) {
    $MergeArgs += '--partial'
}
python3 .claude/skills/plugin-evals/scripts/merge_eval_results.py @MergeArgs

$TotalSeconds = [System.Int32] ((Get-Date) - $StartedAt).TotalSeconds
Write-Output "suite done in $(Format-Duration $TotalSeconds), `$$Spent"
