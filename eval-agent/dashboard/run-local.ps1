#Requires -Version 7
<#
.SYNOPSIS
Baut das Dashboard-Image und startet es lokal im Mock-Modus (keine Azure-/GitHub-Zugriffe).
.PARAMETER Port
Lokaler Port.
.PARAMETER MockUser
Angemeldeter Fake-User.
#>
[CmdletBinding()]
param(
    [int] $Port = 8080,
    [string] $MockUser = 'mock.user@example.com'
)

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    docker build -t eval-dashboard:local .
    if ($LASTEXITCODE) { throw 'docker build failed' }

    Write-Host "🚀 http://localhost:$Port (MOCK, Strg+C beendet)"
    docker run --rm --name eval-dashboard-local -p "${Port}:8080" `
        -e MOCK=1 -e "MOCK_USER=$MockUser" eval-dashboard:local
}
finally { Pop-Location }
