$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$work=Join-Path (Split-Path $repo -Parent) 'probes/nes-kirby1023'
$replay=(Get-ChildItem $work -Directory -Filter 'replay-*'|Sort-Object LastWriteTime|Select-Object -Last 1).FullName
$scratch=Join-Path $env:TEMP ('nes-kirby1023-ingress-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $scratch | Out-Null
Copy-Item -Path "$work/board/nes_native_spi165.sv","$work/board/nes_geometry_sender653.sv","$repo/tests/nes-functional/kirby1023_ingress_tb.sv","$repo/tests/nes-functional/spi200_bus.svh","$replay/frame*.wire" -Destination $scratch
$bin='C:/altera_standard/25.1std/questa_fse/win64'
Push-Location $scratch
try {
 & "$bin/vlib.exe" work
 & "$bin/vlog.exe" -sv @(Get-ChildItem *.sv -Name) *> "$work/ingress-compile.log"
 if($LASTEXITCODE){throw 'See ingress-compile.log'}
 foreach($f in 750,1830,3030,3570){
  & "$bin/vsim.exe" -c work.kirby1023_ingress_tb "+FRAME=$f" -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> "$work/ingress-$f.log"
  if($LASTEXITCODE -or !(Select-String -Path "$work/ingress-$f.log" -Pattern 'PASS1023 ingress' -Quiet)){throw "See ingress-$f.log"}
  Copy-Item "frame$f.d1" $replay -Force
 }
} finally {Pop-Location}
