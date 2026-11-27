param([Parameter(Mandatory)][string]$Board,[Parameter(Mandatory)][string]$Report)
$ErrorActionPreference='Stop'
$src=(Resolve-Path $Board).Path
$tb=(Resolve-Path "$PSScriptRoot/../tests/nes-functional/ff3_slot_stop1046_tb.sv").Path
$out=[IO.Directory]::CreateDirectory($Report).FullName
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$scratch=[IO.Directory]::CreateDirectory((Join-Path $env:TEMP ('ff3-stop1046-'+[guid]::NewGuid().ToString('N'))))
Push-Location $scratch.FullName
try {
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib'}
 & "$bin/vlog.exe" -sv "$src/nes_rom_spi.sv" $tb *> "$out/stop-vlog.log"
 if($LASTEXITCODE){throw 'STOP test compile'}
 & "$bin/vsim.exe" -c ff3_slot_stop1046_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/stop.log"
 if($LASTEXITCODE -or !(Select-String -LiteralPath "$out/stop.log" -SimpleMatch 'PASS cold validation, slot restart')){throw 'STOP test failed'}
}finally{Pop-Location}
