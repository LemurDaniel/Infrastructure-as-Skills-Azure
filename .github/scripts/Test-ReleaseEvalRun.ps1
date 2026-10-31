# NOTE:
#   Requires: git with the eval-history branch reachable on origin, run from the repository root.
#   Called by release.plugin.yaml before a release is published.
#
#   ./.github/scripts/Test-ReleaseEvalRun.ps1 -Version 0.7.0
#
#   Warns, never fails: every release pull request records its Sonnet eval run on the
#   eval-history branch (git-commit-conventions, section 5), and the README badge shows the
#   newest one with its version and commit. A release without a run for its version is
#   published anyway; the warning says the badge still names an older version.

#
#   Chapters:
#     CHECK THE EVAL RUN AND THE BADGE   The run of this version and the pinned badge.
#

param (
    <#
    [Required]
    The version about to be released, without the leading v (e.g. 0.7.0).
    #>
    [Parameter(Mandatory = $true)]
    [System.String]
    $Version
)

Set-StrictMode -Version 1.0
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$EVAL_MODEL = 'sonnet'

# ===========================================================================
# ==================   CHECK THE EVAL RUN AND THE BADGE   ===================
# ===========================================================================
#
#   1. Eval run   Finds the Sonnet run recorded for this version.
#   2. Badge      Checks that the README badge is pinned to a run of this version.
#

# ---------------------------------------------------------------------------
# Eval run
#   Finds the Sonnet run recorded for this version.
# ---------------------------------------------------------------------------

# A missing branch is a warning, not an error: nothing was ever recorded.
$PSNativeCommandUseErrorActionPreference = $false
git fetch --quiet origin eval-history 2>$null
$IsHistoryFetched = $LASTEXITCODE -EQ 0
$PSNativeCommandUseErrorActionPreference = $true

if (-NOT $IsHistoryFetched) {
    Write-Output "::warning::no eval-history branch: v$Version is released without a recorded eval run"
    exit 0
}

$Runs = @((git show FETCH_HEAD:index.json | Out-String | ConvertFrom-Json).runs)
| Where-Object { $_.model -EQ $EVAL_MODEL }
$Runs = @($Runs)
$OwnRuns = @($Runs | Where-Object { $_.version -EQ $Version })

if ($OwnRuns.Count -GT 0) {
    $Run = $OwnRuns[-1]
    $FullCount = @($Run.cases | Where-Object { $_.passRate -EQ 1 }).Count
    Write-Output "eval run for v${Version}: $EVAL_MODEL at $($Run.commit), $FullCount/$(@($Run.cases).Count) cases at 100%"
}
else {
    $LastRun = $Runs.Count -GT 0 ? $Runs[-1] : $null
    $Shown = 'nothing'
    if ($null -NE $LastRun) {
        $ShortCommit = "$($LastRun.commit)".Substring(0, [System.Math]::Min(7, "$($LastRun.commit)".Length))
        $Shown = "v$($LastRun.version) @ $ShortCommit"
    }
    Write-Output ("::warning::v$Version is released without a Sonnet eval run on eval-history; " +
        "the README badge still shows $Shown. Run the suite (git-commit-conventions, section 5).")
}

# ---------------------------------------------------------------------------
# Badge
#   Checks that the README badge is pinned to a run of this version.
# ---------------------------------------------------------------------------

# README: .../Infrastructure-as-Skills-Azure/<40-hex eval-history commit>/badge-sonnet.json
$PinMatch = Select-String -Path README.md -Pattern 'Infrastructure-as-Skills-Azure/([0-9a-f]{40})/badge-sonnet\.json'
| Select-Object -First 1

if ($null -EQ $PinMatch) {
    Write-Output '::warning::the README badge is not pinned to an eval-history commit'
    exit 0
}
$Pin = $PinMatch.Matches[0].Groups[1].Value

# A pin that is not on eval-history is a warning as well.
$PSNativeCommandUseErrorActionPreference = $false
$Badge = git show "${Pin}:badge-sonnet.json" 2>$null | Out-String
$IsBadgeFound = $LASTEXITCODE -EQ 0
$PSNativeCommandUseErrorActionPreference = $true

if (-NOT $IsBadgeFound) {
    Write-Output "::warning::the README badge is pinned to $Pin, which is not on eval-history"
}
elseif (-NOT $Badge.Contains("v$Version ")) {
    $BadgeVersion = [System.Text.RegularExpressions.Regex]::Match($Badge, 'v[0-9][^ ]*').Value
    Write-Output "::warning::the README badge is pinned to a run of another version ($BadgeVersion), not v$Version"
}
else {
    Write-Output "README badge pinned to ${Pin}: v$Version"
}
