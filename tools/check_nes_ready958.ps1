# Invoke through the licensed single-seat wrapper, after both ARM replays.
$ErrorActionPreference='Stop'
$mode=if($env:NES_958_RTL){$env:NES_958_RTL}else{'mark'}
if($mode -notin 'mark','credit','closed','short'){throw 'unknown replay'}
$env:NES_CHR952='checked'
$env:NES_CHR951_GUARDS_ONLY='1'
& (Join-Path $PSScriptRoot 'check_nes_chr951.ps1')
$temp=Join-Path $env:LOCALAPPDATA 'Temp'
$vsim='C:/altera_standard/25.1std/questa_fse/win64/vsim.exe'
$python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$env:PYTHONPATH=Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) '.tools/arm259-python'
Push-Location (Join-Path $temp 'nes-952checked/nes-trial816-board952')
try {
 foreach($p in 1,2){
  & $python (Join-Path $PSScriptRoot 'nes_ready958.py') $temp $p --fixtures $mode
  if($LASTEXITCODE){throw 'fixture export failed'}
  $base=Join-Path $temp "nes-tile821-obj-jointmirror-p$p-958$mode-cold-pair"
  $opts=@()
  foreach($gen in 905,906){
   $d=Join-Path $base "gen$gen"
   $log=Join-Path $d 'timing958.log'
   if($gen -eq 906){$opts+='+admission954';$opts+='+timing958'}
   & $vsim -c -gREPLAY=1 -gRETAIN951=1 "-gG=$gen" work951.tb_nes_port914 "+trace=$d" @opts -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> $log
   if($LASTEXITCODE -or !(Select-String -LiteralPath $log -Pattern 'PASS914 trace' -Quiet)){throw "see $log"}
   $opts=@("+previous_rows=$d/rows-out951.hex")
  }
 }
} finally {Pop-Location}
