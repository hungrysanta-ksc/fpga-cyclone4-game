# Invoke as the job of the existing Starter FLOAT wrapper.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$workspace=Split-Path $root -Parent
$temp=[IO.Path]::GetTempPath()
$client=Join-Path $workspace 'probes/nes-receipt941/prefix'
$board=Join-Path $temp 'nes-952checked/nes-trial816-board952'
$pinned=(Get-Content -Raw (Join-Path $root 'analysis/admission954-results.json') | ConvertFrom-Json).consumer
$python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$env:PYTHONPATH=Join-Path $workspace '.tools/arm259-python'
& $python "$PSScriptRoot/check_nes_rom613.py" --board $board --client $client --client-sha $pinned --out (Join-Path $temp 'nes-image955/bus') --bin C:/altera_standard/25.1std/questa_fse/win64
if ($LASTEXITCODE) {throw 'MMC955 ROM aperture test failed'}
