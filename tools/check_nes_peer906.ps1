$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$temp=[IO.Path]::GetTempPath()
$board=Join-Path $temp 'nes-trial816-board905'
$work=Join-Path $temp 'nes-peer906'
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$py=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$rom=Join-Path $env:USERPROFILE 'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes'
$trace=Join-Path $env:USERPROFILE 'Downloads/nes-frame-mmc905.bin'
foreach($variant in 'byte','pair'){
 $job=Join-Path $work $variant
 & $py "$PSScriptRoot/prepare_nes_peer906.py" $temp $job $trace $rom
 if($LASTEXITCODE){throw 'stimulus preparation'}
 Push-Location $job
 try{
  if(!(Test-Path work)){& "$bin/vlib.exe" work}
  $src=if($variant -eq 'byte'){$board}else{$job}
  & "$bin/vlog.exe" -sv "$board/nes_native_arbiter165.sv" "$board/nes_chr_cache611.sv" "$board/nes_obj_capture611.sv" "$src/nes_tile205.sv" "$src/nes_source_tile192.sv" "$root/tests/nes-functional/tb_nes_peer906.sv" *> compile.log
  if($LASTEXITCODE){throw "compile $variant"}
  foreach($phase in 1,2){foreach($pattern in 0,1,2){
   $log="run-$phase-$pattern.log"
   & "$bin/vsim.exe" -c tb_nes_peer906 "+phase=$phase" "+pattern=$pattern" -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> $log
   if($LASTEXITCODE -or !(Select-String $log -Pattern 'PASS906' -Quiet)){throw "failed $variant $log"}
  }
   $log="edge-$phase.log"
   & "$bin/vsim.exe" -c tb_nes_peer906 "+phase=$phase" '+pattern=0' '+edge' -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> $log
   if($LASTEXITCODE -or !(Select-String $log -Pattern 'PASS906 directed' -Quiet)){throw "failed $variant $log"}
  }
 }finally{Pop-Location}
}
