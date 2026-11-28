$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/..").Path
$out=(Resolve-Path "$root/../probes/nes-carts1059").Path
$b="$out/board-21"
$q='C:/altera_standard/25.1std/questa_fse/win64'
$job=New-Item -Type Directory -Path (Join-Path $env:TEMP ('vrc-render-'+[guid]::NewGuid().ToString('N')))
Push-Location $job.FullName
try {
 foreach($name in 'nes_source_tile192.sv','nes_tile205.sv','nes_native_arbiter165.sv','nes_rom_service.sv','cart_nrom.sv'){Copy-Item "$b/$name" .}
 foreach($name in 'regs_savestates.sv','bus_savestates.vhd','ppu.sv'){Copy-Item "$b/rtl/$name" .}
 Copy-Item "$root/tests/nes-functional/prerender1058_tb.sv","$root/tests/nes-functional/demand1059_tb.sv" .
 & "$q/vlib.exe" work
 & "$q/vcom.exe" -2008 bus_savestates.vhd *> "$out/render-vcom.log"
 if($LASTEXITCODE){throw 'vcom'}
 & "$q/vlog.exe" -sv regs_savestates.sv ppu.sv cart_nrom.sv nes_rom_service.sv nes_tile205.sv nes_native_arbiter165.sv nes_source_tile192.sv demand1059_tb.sv prerender1058_tb.sv *> "$out/render-vlog.log"
 if($LASTEXITCODE){throw 'vlog'}
 foreach($tb in 'prerender1058_tb','demand1059_tb'){
  & "$q/vsim.exe" -c -L altera_mf_ver -suppress 3009 $tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/$tb.log"
  if($LASTEXITCODE -or !(Select-String -Quiet -Path "$out/$tb.log" -Pattern '^# PASS')){throw $tb}
 }
} finally {Pop-Location}
