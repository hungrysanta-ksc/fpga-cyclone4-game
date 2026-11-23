# Use the existing single-seat FLOAT wrapper and completed MMC960 replay.
$ErrorActionPreference='Stop'
$env:NES_CHR952='checked'
$env:NES_CHR951_GUARDS_ONLY='1'
& (Join-Path $PSScriptRoot 'check_nes_chr951.ps1')
$temp=Join-Path $env:LOCALAPPDATA 'Temp'
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$pair=$env:NES_TAIL961 -eq 'pair'
$board=if($pair){'nes-trial816-board961'}else{'nes-952checked/nes-trial816-board952'}
$prior=if($pair){'961pair'}else{'960closed'}
$wire=$env:NES_WIRE961 -in '1','2'
$tag=if($wire){if($pair){'961wirepair'}else{'961wirebase'}}else{$prior}
if($env:NES_WIRE961 -eq '2'){$tag+='2'}
Push-Location (Join-Path $temp $board)
try {
 if($pair){
  & "$bin/vsim.exe" -c -gCROSS=1 work951.tb_nes_companion952 -do 'onerror {quit -code 1}; run -all; quit -code 0' *> row961.log
  if($LASTEXITCODE -or !(Select-String -LiteralPath row961.log -Pattern 'PASS952 16 actual' -Quiet)){throw 'see row961.log'}
 }
 foreach($phase in 1,2){
  $base=Join-Path $temp "nes-tile821-obj-jointmirror-p$phase-$tag-cold-pair"
  $previous=Join-Path $temp "nes-tile821-obj-jointmirror-p$phase-960closed-cold-pair/gen906/rows-out951.hex"
  $frames=907,908,909
  if($wire){
   $previous=Join-Path $temp "nes-tile821-obj-jointmirror-p$phase-$prior-cold-pair/gen907/rows-out951.hex"
   $frames=908,909
  } elseif($env:NES_TAIL961_FROM909 -eq '1'){
   $previous=Join-Path $base 'gen908/rows-out951.hex'
   $frames=@(909)
  }
  if (!(Test-Path $previous)) {throw 'Missing previous RTL checkpoint'}
  foreach($g in $frames){
   $d=Join-Path $base "gen$g"
   $log=Join-Path $d 'tail961.log'
   & "$bin/vsim.exe" -c -gREPLAY=1 -gRETAIN951=1 "-gG=$g" work951.tb_nes_port914 "+trace=$d" "+previous_rows=$previous" +timing958 +tail961 +all_e8_differences -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> $log
   if($LASTEXITCODE -or !(Select-String -LiteralPath $log -Pattern 'PASS914 trace' -Quiet)){throw "see $log"}
   $previous=Join-Path $d 'rows-out951.hex'
  }
 }
} finally {Pop-Location}
