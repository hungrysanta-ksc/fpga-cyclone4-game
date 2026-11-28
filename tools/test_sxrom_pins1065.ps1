$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/..").Path
$out=(Resolve-Path "$root/../probes/nes-mmc1-1065").Path
$q='C:/altera_standard/25.1std/questa_fse/win64'
$work=New-Item -ItemType Directory -Path (Join-Path $env:TEMP ('sxrom-pins-'+[guid]::NewGuid().ToString('N')))
Push-Location $work.FullName
try {
 & "$q/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib failed'}
 & "$q/vlog.exe" -sv "$root/rtl/nes_mmc1_1063.sv" "$root/rtl/nes_sxrom_address1065.sv" "$root/tests/nes-functional/sxrom_pins1065_tb.sv" *> "$out/pins-compile.log"
 if($LASTEXITCODE){throw 'pin test compile failed'}
 foreach($n in 1,2){
  Copy-Item "$out/ff$n.trace" trace.txt -Force
  & "$q/vsim.exe" -c sxrom_pins1065_tb '+trace=trace.txt' -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/pins-$n.log"
  if($LASTEXITCODE -or !(Select-String -Quiet -Path "$out/pins-$n.log" -Pattern '^# PASS SXROM')){throw "FF$n pin comparison failed"}
 }
 & "$q/vlog.exe" -sv "$out/board-sxrom/nes_rom_loader.sv" "$root/tests/nes-functional/ff3_load_count_tb.sv" *> "$out/sx-loader-compile.log"
 if($LASTEXITCODE){throw 'SXROM loader compile failed'}
 & "$q/vsim.exe" -c ff3_load_count_tb -gBYTES=524288 -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/sx-loader.log"
 if($LASTEXITCODE -or !(Select-String -Quiet -Path "$out/sx-loader.log" -Pattern '^# PASS FF3 loader 524288')){throw 'SXROM loader START/STOP failed'}
}finally{Pop-Location}
