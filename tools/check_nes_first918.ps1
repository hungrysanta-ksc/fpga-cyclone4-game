$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$rtl=Join-Path (Split-Path $root -Parent) 'probes/nes-first918-single/rtl'
$tb=Join-Path $root 'tests/nes-functional'
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$run='onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'
function Sim([string]$log,[string]$pass,[string[]]$arguments) {
 & "$bin/vsim.exe" -c @arguments -do $run *> $log
 if($LASTEXITCODE -or !(Select-String -LiteralPath $log -Pattern $pass -SimpleMatch -Quiet)){throw "see $log"}
}
$sim=Join-Path $env:LOCALAPPDATA 'Temp/nes-first918-questa'
[IO.Directory]::CreateDirectory($sim) | Out-Null
Copy-Item "$rtl/nes_*.sv","$tb/tb_nes_first918.sv","$tb/tb_nes_port914.sv" $sim
Push-Location $sim
try {
 if(!(Test-Path work)){& "$bin/vlib.exe" work}
 $files=(Get-ChildItem nes_*.sv).Name
 & "$bin/vlog.exe" -sv @files tb_nes_first918.sv tb_nes_port914.sv *> compile.log
 if($LASTEXITCODE){throw 'see compile.log'}
 Sim 'stop918.log' 'PASS918' @('tb_nes_first918')
 Sim 'port918.log' 'PASS914' @('tb_nes_port914')
 foreach($g in 908,912){foreach($p in 1,2){foreach($cache in 'warm','cold'){
  $dir=Join-Path $env:LOCALAPPDATA "Temp/nes-tile821-obj-jointmirror-p$p-918single-$cache-pair"
  if($g -ne 912){$dir=Join-Path $dir "gen$g"}
  Sim "trace-$g-$p-$cache.log" 'PASS914 trace' @('-gREPLAY=1',"-gG=$g",'tb_nes_port914',"+trace=$dir")
 }}}
} finally {Pop-Location}
