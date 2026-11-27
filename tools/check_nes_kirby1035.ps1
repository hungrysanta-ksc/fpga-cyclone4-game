$ErrorActionPreference='Stop'
$python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $python "$PSScriptRoot/check_nes_kirby1035.py"
if ($LASTEXITCODE) { throw 'MMC1035 RTL comparison failed' }
