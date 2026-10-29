# SPDX-License-Identifier: MIT
param([Parameter(Mandatory=$true)][string]$Board,[Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference='Stop'
if (Test-Path -LiteralPath $Out) {throw 'Output directory already exists'}
New-Item -ItemType Directory -Path $Out | Out-Null
$repo=Split-Path -Parent $PSScriptRoot
foreach($n in @('nes_diag_clock_guard127.sv','nes_diag_startup_guard.sv','nes_domain_reset124.sv')){Copy-Item (Join-Path $Board $n) $Out}
Copy-Item (Join-Path $repo 'tests/nes-functional/guard127_tb.sv') $Out
Push-Location $Out
try {
 $bin='C:/altera_standard/25.1std/questa_fse/win64'
 & "$bin/vlib.exe" work *> vlib.log; if($LASTEXITCODE){throw 'vlib failed'}
 & "$bin/vlog.exe" -sv nes_diag_clock_guard127.sv nes_diag_startup_guard.sv nes_domain_reset124.sv guard127_tb.sv *> compile.log; if($LASTEXITCODE){throw 'compile failed'}
 & "$bin/vsim.exe" -c work.guard127_tb -do 'onerror {quit -code 1};run -all;quit -f' *> simulation.log
 if($LASTEXITCODE -or -not (Select-String -Quiet -Path simulation.log -Pattern 'PASS127 GUARD cases=3') -or -not (Select-String -Quiet -Path simulation.log -Pattern 'Errors: 0')){throw 'guard simulation failed'}
} finally {Pop-Location}
