$ErrorActionPreference = 'Stop'
$board = Join-Path $env:LOCALAPPDATA 'Temp/nes-trial816-board963'
$bench = Join-Path (Split-Path $PSScriptRoot -Parent) 'tests/nes-functional/tb_nes_page963.sv'
$bin = 'C:/altera_standard/25.1std/questa_fse/win64'
Push-Location $board
try {
 if (!(Test-Path work963)) { & "$bin/vlib.exe" work963; if ($LASTEXITCODE) { throw 'vlib failed' } }
 & "$bin/vlog.exe" -work work963 -sv nes_domain_reset124.sv nes_native_mailbox206.sv nes_plan_spi200.sv nes_e9_rows914.sv $bench *> compile963.log
 if ($LASTEXITCODE) { throw 'see compile963.log' }
 & "$bin/vsim.exe" -c work963.tb_nes_page963 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> guards963.log
 if ($LASTEXITCODE -or !(Select-String -Quiet -Path guards963.log -Pattern 'PASS963 SPI')) { throw 'see guards963.log' }
} finally { Pop-Location }
