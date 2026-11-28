$ErrorActionPreference='Stop'
& "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe" "$PSScriptRoot/test_cart_resume1059.py" 7 5 21
if($LASTEXITCODE){throw 'cartridge resume comparison failed'}
