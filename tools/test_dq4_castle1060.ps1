$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
 & "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe" -c "from pathlib import Path; from test_cart_resume1059 import run; run(5,Path.home()/'Downloads/9ac62bb9-100000-1a.nsv')"
 if($LASTEXITCODE){throw 'Castle slot replay failed'}
}finally{Pop-Location}
