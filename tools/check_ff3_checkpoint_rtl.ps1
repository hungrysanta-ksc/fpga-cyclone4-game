$ErrorActionPreference='Stop'
$python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $python "$PSScriptRoot/check_ff3_checkpoint_rtl.py"
if($LASTEXITCODE){throw 'FF3 checkpoint RTL test failed'}

