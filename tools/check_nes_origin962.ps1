# Run via the existing Starter FLOAT wrapper after the 961 build and ARM replays.
param([ValidateSet('group','page','all','wire')][string]$Subset=$(if($env:NES_ROWS962){$env:NES_ROWS962}else{'all'}))
$ErrorActionPreference='Stop'
$temp=Join-Path $env:LOCALAPPDATA 'Temp'
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$board=Join-Path $temp 'nes-trial816-board961'
Push-Location $board
try {
 $cases=switch($Subset){'group'{ 'one','four' } 'page'{ 'page' } 'all'{ 'one','four','page' } 'wire'{ 'onewire' }}
 foreach($phase in 1,2){
  foreach($case in $cases){
   if($case -eq 'onewire' -and $phase -ne 1){continue}
   $dir=Join-Path $temp "nes-tile821-obj-jointmirror-p$phase-962$case-cold-pair/gen909"
   $prior=Join-Path $dir 'budget962.hex'
   if(!(Test-Path $prior)){throw "Missing cache input for $dir"}
   $log=Join-Path $dir 'tail961.log'
   & "$bin/vsim.exe" -c -gREPLAY=1 -gRETAIN951=1 -gG=909 work951.tb_nes_port914 "+trace=$dir" "+previous_rows=$prior" +timing958 +tail961 +all_e8_differences -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> $log
   if($LASTEXITCODE -or !(Select-String -LiteralPath $log -Pattern 'PASS914 trace chunks=11 bytes=1072' -Quiet)){throw "see $log"}
  }
 }
} finally {Pop-Location}
