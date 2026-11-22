$ErrorActionPreference = 'Stop'
$board = Join-Path ([IO.Path]::GetTempPath()) 'nes-board925'
$workspace = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$client = Join-Path $workspace 'probes/nes-return920/mask'
$python = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$env:PYTHONPATH = Join-Path $workspace '.tools/arm259-python'
$pinned = (Get-Content -Raw (Join-Path $PSScriptRoot '../analysis/window924-results.json') | ConvertFrom-Json).proof.objheader.recovery.consumer
& $python "$PSScriptRoot/check_nes_rom613.py" --board "$board/board925" --out "$board/bus" --client $client --client-sha $pinned --bin C:/altera_standard/25.1std/questa_fse/win64
if ($LASTEXITCODE) { throw 'MMC925 ROM aperture test failed' }
