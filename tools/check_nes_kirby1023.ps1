param()
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$work=Join-Path (Split-Path $repo -Parent) 'probes/nes-kirby1023'
$scratch=Join-Path $env:TEMP ('nes-kirby1023-sim-'+[guid]::NewGuid().ToString('N'))
$raw=Join-Path $env:LOCALAPPDATA 'Temp/nes-kirby1023-mesen01'
$python='C:/Users/mohallo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $python "$repo/tools/check_nes_kirby1023.py" geometry $raw --board "$work/board" --out $scratch *> "$work/geometry.log"
$result=$LASTEXITCODE
Copy-Item -LiteralPath $scratch -Destination "$work/replay-$(Split-Path $scratch -Leaf)" -Recurse
exit $result
