$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

$webRoot = Join-Path $repoRoot "webapp"
if (-not (Test-Path (Join-Path $webRoot "package.json"))) {
    exit 0
}

$bunExe = (Get-Command bun -ErrorAction SilentlyContinue)
if ($bunExe) {
    $bun = $bunExe.Source
}
elseif (Test-Path "C:\Users\sandr\.bun\bin\bun.exe") {
    $bun = "C:\Users\sandr\.bun\bin\bun.exe"
}
else {
    # bun not available; the Biome gate is enforced in CI (.github/workflows/ci.yml)
    exit 0
}

Push-Location $webRoot
try {
    if (-not (Test-Path "node_modules")) {
        & $bun install --silent
    }
    & $bun run biome:ci
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
