param([switch]$Observer)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$probes=Join-Path (Split-Path $repo -Parent) 'probes'
$board=Join-Path $probes 'nes-kirby1023/board'
$out=Join-Path $probes 'nes-kirby1026'
if ($Observer) {
 $out=Join-Path $probes 'nes-kirby1027'
 $board=Join-Path $out 'board-tag'
}
New-Item -ItemType Directory -Force $out | Out-Null
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$scratch=Join-Path $env:TEMP ('nes-kirby1026-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $scratch | Out-Null
Push-Location $scratch
try {
 if (!(Test-Path work)) { & "$bin/vlib.exe" work; if ($LASTEXITCODE) { throw 'vlib' } }
 $files=foreach ($name in 'nes_domain_reset124','nes_native_mailbox206','nes_bulk_aperture188','nes_tile_bulk206','nes_chr_cache611','nes_obj_capture611','nes_e9_rows914','nes_tile205','nes_native_arbiter165','nes_source_tile192') { Join-Path $board "$name.sv" }
 Copy-Item -LiteralPath $files -Destination $scratch
 Copy-Item "$repo/tests/nes-functional/tb_nes_kirby1026.sv" $scratch
 $defines=@()
 if ($Observer) {
  Copy-Item "$board/nes_display1010.sv","$repo/tests/nes-functional/kirby1027_scoreboard.svh" $scratch
  Copy-Item "$board/nes_screen_status151.sv","$repo/tests/nes-functional/tb_nes_kirby1027_status.sv" $scratch
  Copy-Item "$board/nes_sink_bus165.sv","$board/sink-program.hex" $scratch
  $baseline=Join-Path $probes 'nes-kirby1023/board'
  (Get-Content "$baseline/nes_display1010.sv" -Raw).Replace('module nes_display1010(', 'module nes_display1010_old(') | Set-Content nes_display1010_old.sv
  (Get-Content "$baseline/nes_sink_bus165.sv" -Raw).Replace('module nes_sink_bus165(', 'module nes_sink_bus165_old(') | Set-Content nes_sink_bus165_old.sv
  (Get-Content "$baseline/nes_screen_status151.sv" -Raw).Replace('module nes_screen_status151(', 'module nes_screen_status151_old(').Replace('nes_display1010 trace(', 'nes_display1010_old trace(') | Set-Content nes_screen_status151_old.sv
  $defines=@('+define+KIRBY1027_OBSERVER')
 }
 & "$bin/vlog.exe" -sv @defines @(Get-ChildItem *.sv -Name) *> "$out/compile.log"
 if ($LASTEXITCODE) {throw "See $out/compile.log"}
 if ($Observer) {
  & "$bin/vsim.exe" -c work.tb_nes_kirby1027_status -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> "$out/status.log"
  if ($LASTEXITCODE -or !(Select-String -Path "$out/status.log" -Pattern 'PASS1027_STATUS' -Quiet)) {throw "See $out/status.log"}
 }
 $cases=if ($Observer) {0..6} else {0..4}
 foreach ($case in $cases) {
  & "$bin/vsim.exe" -c work.tb_nes_kirby1026 "+CASE=$case" -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> "$out/case$case.log"
  if ($LASTEXITCODE -or !(Select-String -Path "$out/case$case.log" -Pattern "PASS1026 case=$case " -Quiet)) {throw "See $out/case$case.log"}
 }
} finally {Pop-Location}
