# Build and upload to PyPI. Run scripts/check.ps1 first.
# The version must not already be on PyPI; the token is read from a secret store, never git.
$ErrorActionPreference = "Stop"

# Refuse to upload a version that is already on PyPI (works on Windows PowerShell 5.1 and pwsh 7).
$version = (Select-String -Path pyproject.toml -Pattern '^version = "(.+)"').Matches[0].Groups[1].Value
$published = $true
try {
    Invoke-WebRequest -UseBasicParsing "https://pypi.org/pypi/lvtypedesc/$version/json" | Out-Null
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 404) { $published = $false } else { throw }
}
if ($published) { throw "lvtypedesc $version is already on PyPI. Bump the version first." }

$token = $env:PYPI_TOKEN
if (-not $token -and (Test-Path "C:\secrets\pypi-token.txt")) {
    $token = (Get-Content "C:\secrets\pypi-token.txt" -Raw).Trim()
}
if (-not $token) {
    throw "No PyPI token. Set `$env:PYPI_TOKEN or save it to C:\secrets\pypi-token.txt (never commit it)."
}

# Build from a clean clone of the committed HEAD, never from the working tree, so local
# line endings or stray files cannot reach the archives. Native tools do not obey
# $ErrorActionPreference, so every exit code is checked.
$work = Join-Path ([System.IO.Path]::GetTempPath()) ("lvtypedesc-release-" + [guid]::NewGuid())
try {
    git clone --quiet . $work
    if ($LASTEXITCODE) { throw "git clone failed" }
    Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
    python -m build --outdir dist $work
    if ($LASTEXITCODE) { throw "build failed" }
    python -m twine check --strict dist/*
    if ($LASTEXITCODE) { throw "twine check failed" }
} finally {
    Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}

$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = $token
try {
    python -m twine upload dist/*
    if ($LASTEXITCODE) { throw "upload failed" }
} finally { Remove-Item Env:\TWINE_PASSWORD -ErrorAction SilentlyContinue }
