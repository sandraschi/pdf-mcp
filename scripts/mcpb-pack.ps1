# MCPB pack with a mandatory fresh stage (MCPB_PACKAGING_STANDARDS.md 2.5).
#
# Wipes mcpb/src, recopies the live package into mcpb/src/<package> (never
# flattened), stages manifest + assets + docs, ensures the pack-root
# .mcpbignore exists, then runs `mcpb pack`. Bare `mcpb pack .` is forbidden -
# it ships a stale twin.
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$McpbDir = Join-Path $RepoRoot "mcpb"
$PkgName = "pdf_mcp"
$PkgSrc = Join-Path $RepoRoot $PkgName
$Version = (Select-String -Path (Join-Path $RepoRoot "pyproject.toml") -Pattern '^version\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
if (-not $Version) { throw "Could not read version from pyproject.toml" }

if (-not (Test-Path -LiteralPath $PkgSrc)) { throw "Package source missing: $PkgSrc" }

Write-Host "=== MCPB pack pdf-mcp $Version (fresh stage) ===" -ForegroundColor Cyan

# 1. Wipe + recreate mcpb/
if (Test-Path -LiteralPath $McpbDir) { Remove-Item -Recurse -Force -LiteralPath $McpbDir }
New-Item -ItemType Directory -Force -Path $McpbDir | Out-Null
$stageSrc = Join-Path $McpbDir "src"
New-Item -ItemType Directory -Force -Path $stageSrc | Out-Null

# 2. Copy src -> mcpb/src/<package> (preserve the package dir).
Copy-Item -Recurse -Force -LiteralPath $PkgSrc (Join-Path $stageSrc $PkgName)
Copy-Item -Force (Join-Path $RepoRoot "manifest.json") (Join-Path $McpbDir "manifest.json")
foreach ($doc in @("README.md", "CHANGELOG.md", "LICENSE")) {
    $p = Join-Path $RepoRoot $doc
    if (Test-Path -LiteralPath $p) { Copy-Item -Force -LiteralPath $p (Join-Path $McpbDir $doc) }
}

# 3. Assets (icon + 3-4-100 prompts).
$assetsSrc = Join-Path $RepoRoot "assets"
if (Test-Path -LiteralPath $assetsSrc) {
    Copy-Item -Recurse -Force -LiteralPath $assetsSrc (Join-Path $McpbDir "assets")
}

# 4. .mcpbignore MUST be at the pack root, not only the repo root.
$ignore = Join-Path $RepoRoot ".mcpbignore"
if (-not (Test-Path -LiteralPath $ignore)) { throw ".mcpbignore missing at repo root" }
Copy-Item -Force -LiteralPath $ignore (Join-Path $McpbDir ".mcpbignore")

# 5. Strip bytecode / backups that the copy may have dragged in.
Get-ChildItem -Path $McpbDir -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '__pycache__|\.pyc$|\.bak(\.|$)' } |
    ForEach-Object { Remove-Item -Recurse -Force -LiteralPath $_.FullName -ErrorAction SilentlyContinue }

# 6. 3-4-100 gate.
function Get-WordCount([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return 0 }
    return (@(Get-Content -Raw -LiteralPath $Path) -split '\s+' | Where-Object { $_ }).Count
}
$sys = Get-WordCount (Join-Path $McpbDir "assets\prompts\system.md")
$user = Get-WordCount (Join-Path $McpbDir "assets\prompts\user.md")
$exPath = Join-Path $McpbDir "assets\prompts\examples.json"
$ex = if (Test-Path -LiteralPath $exPath) { @((Get-Content -Raw -LiteralPath $exPath | ConvertFrom-Json)).Count } else { 0 }
Write-Host "  prompts: system=$sys (min 3000) user=$user (min 4000) examples=$ex (min 100)"
if ($sys -lt 3000 -or $user -lt 4000 -or $ex -lt 100) {
    throw "3-4-100 FAIL: system=$sys user=$user examples=$ex (need 3000 / 4000 / 100)"
}

# 7. Layout assertion: the package dir must survive under mcpb/src.
$serverPy = Join-Path $stageSrc "$PkgName\server.py"
if (-not (Test-Path -LiteralPath $serverPy)) {
    throw "mcpb/src layout flattened - $PkgName directory missing under mcpb/src"
}

# 8. Pack (from the staged mcpb dir, so pack-root .mcpbignore applies).
$dist = Join-Path $RepoRoot "dist"
New-Item -ItemType Directory -Force -Path $dist | Out-Null
$out = Join-Path $dist "pdf-mcp-$Version.mcpb"
Push-Location $McpbDir
try {
    bunx @anthropic-ai/mcpb pack . $out
    if ($LASTEXITCODE -ne 0) { throw "mcpb pack failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

$size = (Get-Item -LiteralPath $out).Length
Write-Host "=== MCPB bundle: $out ($size bytes) ===" -ForegroundColor Green
