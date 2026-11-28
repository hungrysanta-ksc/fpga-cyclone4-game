$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$out=(Resolve-Path (Join-Path $root '../probes/nes-mmc1-1063')).Path
$q='C:/altera_standard/25.1std/questa_fse/win64'
$work=New-Item -ItemType Directory -Path (Join-Path $env:TEMP ('mmc1-'+[guid]::NewGuid().ToString('N')))
Push-Location $work.FullName
try {
 & "$q/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib'}
 & "$q/vlog.exe" -sv "$root/rtl/nes_mmc1_1063.sv" "$root/tests/nes-functional/mmc1_1063_tb.sv" *> "$out/compile.log"
 if($LASTEXITCODE){throw 'vlog'}
 foreach($n in 1,2){
  Copy-Item -LiteralPath "$out/zelda$n.trace" -Destination trace.txt
  & "$q/vsim.exe" -c mmc1_1063_tb '+trace=trace.txt' -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/rtl-$n.log"
  if($LASTEXITCODE -or !(Select-String -Quiet -Path "$out/rtl-$n.log" -Pattern '^# PASS MMC1')){throw "MMC1 $n"}
 }
}finally{Pop-Location}
