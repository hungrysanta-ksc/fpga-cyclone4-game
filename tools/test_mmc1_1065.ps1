$ErrorActionPreference='Stop'
& "$PSScriptRoot/test_sxrom_pins1065.ps1"
Push-Location $PSScriptRoot
try {
 $python="$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
 & $python -B -c "from test_cart_resume1059 import run;run(1,zelda=2,opening=True)"
 if($LASTEXITCODE){throw '1064 title baseline failed'}
 & $python -B -c "from test_cart_resume1059 import run;run(1,sxrom=True)"
 $ff=$LASTEXITCODE
 & $python -B -c "from test_cart_resume1059 import run;run(1,zelda=2,opening=True,title_fix=True)"
 if($ff -or $LASTEXITCODE){throw '1065 functional verification failed'}
}finally{Pop-Location}
