# SPDX-License-Identifier: MIT
param([Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference='Stop'
if (Test-Path -LiteralPath $Out) { throw 'Output directory already exists' }
New-Item -ItemType Directory -Path $Out | Out-Null
$repo=Split-Path -Parent $PSScriptRoot
Copy-Item (Join-Path $repo 'tests/nes-nrom448/*.sv') $Out
Push-Location $Out
try {
 $bin='C:/altera_standard/25.1std/questa_fse/win64'
 & "$bin/vlib.exe" work *> vlib.log; if ($LASTEXITCODE) { throw 'vlib failed' }
 & "$bin/vlog.exe" -sv rom_boot_full_model.sv model_tb.sv *> compile.log; if ($LASTEXITCODE) { throw 'compile failed' }
 & "$bin/vsim.exe" -c work.nrom448_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> simulation.log
 if ($LASTEXITCODE -or -not (Select-String -Quiet -Path simulation.log -Pattern 'PASS NROM448 full PRG/CHR pin model boundaries and lanes') -or -not (Select-String -Quiet -Path simulation.log -Pattern 'Errors: 0, Warnings: 0')) { throw 'simulation failed' }
} finally { Pop-Location }
