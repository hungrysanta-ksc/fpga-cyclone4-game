$ErrorActionPreference='Stop'
$python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $python "$PSScriptRoot/check_nes_query1036.py"
if($LASTEXITCODE){throw 'Query/STOP RTL comparison failed'}
