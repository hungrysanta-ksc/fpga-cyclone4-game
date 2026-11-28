$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
 foreach($n in 1,2){
  & "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe" -B -c "from test_cart_resume1059 import run;run(1,zelda=$n)"
  if($LASTEXITCODE){throw "Zelda $n CPU/restore failed"}
 }
}finally{Pop-Location}
