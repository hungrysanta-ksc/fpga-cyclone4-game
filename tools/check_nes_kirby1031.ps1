param([switch]$Shared,[switch]$Bus)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$probes=Join-Path (Split-Path $repo -Parent) 'probes'
$out=Join-Path $probes 'nes-kirby1031'
$board=Join-Path $out 'board'
if($Shared){$out=Join-Path $probes 'nes-kirby1032';$board=Join-Path $out 'board-shared'}
if($Bus){
 $work=Join-Path $probes 'nes-kirby1032'
 $board=Join-Path $work 'board-bus'
 $out=(New-Item -ItemType Directory -Force (Join-Path $work 'bus-test')).FullName
}
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$scratch=New-Item -ItemType Directory (Join-Path $env:TEMP ('kirby1031-'+[guid]::NewGuid().ToString('N')))
$fixture=@(Get-ChildItem "$probes/nes-kirby1023/replay-*/frame1830.d1")
if($fixture.Count -ne 1){throw 'Expected one qualified Kirby ingress replay'}
Copy-Item "$board/nes_native_spi165.sv","$board/nes_geometry_sender653.sv","$repo/tests/nes-functional/kirby1031_offer_tb.sv","$repo/tests/nes-functional/spi200_bus.svh" $scratch
$defs=@()
if($Shared){Copy-Item "$board/nes_display1010.sv" $scratch;$defs=@('+define+SHARED1032')}
if($Bus){
 $old=Join-Path $probes 'nes-kirby1023/board'
 Copy-Item "$board/nes_display1010.sv","$board/nes_sink_bus165.sv","$board/nes_screen_status151.sv","$board/sink-program.hex" $scratch
 (Get-Content "$old/nes_screen_status151.sv" -Raw).Replace('module nes_screen_status151(','module nes_screen_status151_old(') | Set-Content "$scratch/nes_screen_status151_old.sv"
 (Get-Content "$old/nes_sink_bus165.sv" -Raw).Replace('module nes_sink_bus165(','module nes_sink_bus165_old(') | Set-Content "$scratch/nes_sink_bus165_old.sv"
 (Get-Content "$repo/tests/nes-functional/tb_nes_kirby1027_status.sv" -Raw).Replace(".edge1027(2'd0),",'') | Set-Content "$scratch/tb_nes_kirby1027_status.sv"
}
Push-Location $scratch
try {
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib failed'}
 & "$bin/vlog.exe" -sv @defs @(Get-ChildItem *.sv -Name) *> "$out/compile.log"
 if($LASTEXITCODE){throw "See $out/compile.log"}
 if($Bus){
  & "$bin/vsim.exe" -c work.tb_nes_kirby1027_status -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> "$out/status.log"
  if($LASTEXITCODE -or !(Select-String -Path "$out/status.log" -Pattern '^# PASS1027_STATUS 346 SPI73 bits' -Quiet) -or !(Select-String -Path "$out/status.log" -Pattern '^# PASS1027_BUS 10966 observed clocks' -Quiet)){throw "See $out/status.log"}
 }
 foreach($frame in 750,1830,3030,3570){
  $base=Join-Path $fixture[0].DirectoryName "frame$frame"
  $words=Get-Content "$base.wire" -TotalCount 81
  if($words.Count -ne 81 -or $words[0] -notmatch '^e' -or @($words[1..80] | Where-Object {$_ -notmatch '^0'}).Count){throw 'Expected BEGIN + 80 map cells'}
  Set-Content -Encoding ascii words.hex $words
  $block=Get-Content "$base.d1" -TotalCount 1
  $bytes=@([regex]::Matches($block,'[a-fA-F0-9]{2}') | ForEach-Object {$_.Value})
  if($bytes.Count*2 -ne $block.Length){throw 'Invalid reference payload'}
  Set-Content -Encoding ascii block.hex $bytes
  $modes=if($frame -eq 1830){0..4}else{@(0)}
  foreach($mode in $modes){
   $log="$out/replay-$frame-$mode.log"
   & "$bin/vsim.exe" -c work.kirby1031_offer_tb "+MODE=$mode" +COUNT=81 "+BYTES=$($bytes.Count-2)" +WORDS=words.hex +D1=block.hex -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> $log
   if($LASTEXITCODE -or !(Select-String $log -Pattern '^# PASS1031' -Quiet)){throw "See $log"}
  }
 }
} finally {Pop-Location}
