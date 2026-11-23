# Run through the repository's Starter FLOAT wrapper.
$ErrorActionPreference='Stop'
$workspace=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$temp=[IO.Path]::GetTempPath()
$client=Join-Path $workspace 'probes/nes-blank960/retry'
$expected=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $client 'sink165.sfc')).Hash.ToLowerInvariant()
$env:PYTHONPATH=Join-Path $workspace '.tools/arm259-python'
$python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $python "$PSScriptRoot/check_nes_rom613.py" --board (Join-Path $temp 'nes-trial816-board964') --client $client --client-sha $expected --out (Join-Path $temp 'nes-image966-release/bus') --bin C:/altera_standard/25.1std/questa_fse/win64
if ($LASTEXITCODE) {throw 'MMC966 ROM aperture, reset or STOP verification failed'}
