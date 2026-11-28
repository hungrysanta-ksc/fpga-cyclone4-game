$ErrorActionPreference='Stop'
$py="$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
& $py "$PSScriptRoot/check_cart_boot1056.py" "$env:USERPROFILE/Downloads/test"
exit $LASTEXITCODE
