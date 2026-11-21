$ErrorActionPreference='Stop'
$rev=if($env:NES_PORT914_VARIANT -in 'F','G','H','I'){$env:NES_PORT914_VARIANT}else{'I'}
$board=Join-Path $env:LOCALAPPDATA "Temp/nes-port914$rev/nes-trial816-board914"
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$tb=Join-Path (Split-Path $PSScriptRoot -Parent) 'tests/nes-functional/tb_nes_port914.sv'
Push-Location $board
try {
 if(!(Test-Path work)){ & "$bin/vlib.exe" work }
 $modules=@('nes_domain_reset124','nes_native_mailbox206','nes_plan_batch206','nes_e9_scan914',
  'nes_obj_capture611','nes_chr_cache611','nes_tile205','nes_native_arbiter165',
  'nes_e9_rows914','nes_source_tile192','nes_rom_physical','nes_bulk_aperture188','nes_tile_bulk206') | ForEach-Object { "$_.sv" }
 & "$bin/vlog.exe" -sv @modules $tb *> compile914.log
 if($LASTEXITCODE){ throw 'see compile914.log' }
 & "$bin/vsim.exe" -c tb_nes_port914 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> sim914.log
 if($LASTEXITCODE -or !(Select-String sim914.log -Pattern 'PASS914' -Quiet)){ throw 'see sim914.log' }
 $ref=Join-Path $env:LOCALAPPDATA 'Temp/nes-trial816-board906/nes_plan_spi200.sv'
 [IO.File]::WriteAllText((Join-Path $board 'spi_reference.sv'),[IO.File]::ReadAllText($ref).Replace('module nes_plan_spi200(','module nes_plan_spi200_reference('))
 $spiTb=Join-Path (Split-Path $PSScriptRoot -Parent) 'tests/nes-functional/tb_nes_spi914.sv'
 & "$bin/vlog.exe" -sv spi_reference.sv nes_plan_spi200.sv $spiTb *> compile_spi914.log
 if($LASTEXITCODE){throw 'see compile_spi914.log'}
 & "$bin/vsim.exe" -c tb_nes_spi914 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> spi914.log
 if($LASTEXITCODE -or !(Select-String spi914.log -Pattern 'PASS914 SPI' -Quiet)){throw 'see spi914.log'}
 foreach($phase in 1,2){foreach($cache in 'cold','warm'){
  $generations=if($env:NES_PORT914_LEAD -eq '1' -and $cache -eq 'warm'){@(910,911)}elseif($env:NES_PORT914_LEAD -eq '1'){@()}else{@(912)}
  foreach($generation in $generations){
   $trace=if($generation -eq 912){Join-Path $env:LOCALAPPDATA "Temp/nes-tile821-obj-jointmirror-p$phase-914wire-$cache-pair"}else{Join-Path $env:LOCALAPPDATA "Temp/nes-tile821-obj-jointmirror-p$phase-914lead-$cache-pair/gen$generation"}
   $log=if($generation -eq 912){"trace-$phase-$cache.log"}else{"lead-$generation-$phase-$cache.log"}
   & "$bin/vsim.exe" -c -gREPLAY=1 "-gG=$generation" tb_nes_port914 "+trace=$trace" -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> $log
  if($LASTEXITCODE -or !(Select-String $log -Pattern 'PASS914 trace' -Quiet)){throw "see $log"}
 }}}
} finally { Pop-Location }
