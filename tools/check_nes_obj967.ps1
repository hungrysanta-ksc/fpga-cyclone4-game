# Run with the single-seat Starter FLOAT wrapper.
$ErrorActionPreference='Stop'
$board=Join-Path $env:LOCALAPPDATA 'Temp/nes-trial816-board964'
$out=Join-Path $env:LOCALAPPDATA 'Temp/nes-obj967'
$bench=Join-Path (Split-Path $PSScriptRoot -Parent) 'tests/nes-functional'
$bin='C:/altera_standard/25.1std/questa_fse/win64'
New-Item -ItemType Directory -Force -Path $out | Out-Null
Push-Location $out
try {
 if(!(Test-Path work)){ & "$bin/vlib.exe" work; if($LASTEXITCODE){throw 'vlib'} }
 $modules='nes_domain_reset124','nes_native_mailbox206','nes_plan_spi200','nes_plan_batch206','nes_e9_scan914',
   'nes_obj_capture611','nes_chr_cache611','nes_tile205','nes_native_arbiter165','nes_e9_rows914',
   'nes_source_tile192','nes_rom_physical','nes_bulk_aperture188','nes_tile_bulk206','nes_supply905' |
     ForEach-Object { Join-Path $board "$_.sv" }
 & "$bin/vlog.exe" -sv +define+NES_COMPANION952 +define+NES_MAIL964 @modules "$bench/tb_nes_port914.sv" "$bench/tb_nes_obj967.sv" "$bench/tb_nes_page963.sv" *> compile.log
 if($LASTEXITCODE){throw 'see nes-obj967/compile.log'}
 $run='onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'
 & "$bin/vsim.exe" -c -gCONSUMER_CAPTURE=0 work.tb_nes_page963 -do $run *> guards.log
 if($LASTEXITCODE -or !(Select-String -LiteralPath guards.log -Pattern 'PASS963 SPI' -Quiet)){throw 'see nes-obj967/guards.log'}
 foreach($phase in 1,2){foreach($mode in 'control','early','eight','late','other'){
  $log="p$phase-$mode.log"
  & "$bin/vsim.exe" -c work.tb_nes_obj967 "+mode=$mode" "+phase=$phase" -do $run *> $log
  if($LASTEXITCODE -or !(Select-String -LiteralPath $log -Pattern 'PASS967' -Quiet)){throw "see $out/$log"}
 }}
} finally {Pop-Location}
