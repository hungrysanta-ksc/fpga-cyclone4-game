$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$experiment=Join-Path (Split-Path $root -Parent) 'probes/nes-kirby1034'
$scratch=New-Item -ItemType Directory (Join-Path $env:TEMP ('kirby1034-'+[guid]::NewGuid()))
$bin='C:/altera_standard/25.1std/questa_fse/win64'
Push-Location $scratch.FullName
try {
 Copy-Item "$experiment/board-shared/nes_display1010.sv","$root/tests/nes-functional/tb_nes_kirby1034.sv" .
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'work library failed'}
 & "$bin/vlog.exe" -sv nes_display1010.sv tb_nes_kirby1034.sv *> "$experiment/obscompile.log"
 if($LASTEXITCODE){throw 'observer compile failed'}
 & "$bin/vsim.exe" -c work.tb_nes_kirby1034 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> "$experiment/observer.log"
 if($LASTEXITCODE -or !(Select-String -Quiet -Path "$experiment/observer.log" -Pattern 'PASS1034')){throw 'observer regression failed'}
} finally {Pop-Location}
