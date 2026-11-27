$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/..").Path
$out=[IO.Directory]::CreateDirectory("$root/../probes/nes-ff3-1041").FullName
$work=New-Item -Type Directory -Path (Join-Path $env:TEMP ('ff3-cpu-'+[guid]::NewGuid().ToString('N')))
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
Push-Location $work.FullName
try{
 & $python "$root/tools/prepare_ff3_display1037.py" board
 if($LASTEXITCODE){throw 'board preparation failed'}
 & $python -c "import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from prepare_nes_ff3_checkpoint import prepare; from prepare_ff3_core1040 import live_cpu; prepare(Path('reference'),live_cpu)" "$root/tools"
 if($LASTEXITCODE){throw '1040 board preparation failed'}
 (Get-FileHash board/rtl/t65/T65.vhd).Hash | Set-Content "$out/paired-candidate-sha.txt"
 $base=Join-Path $work.FullName 'reference/rtl/t65'
 $baseline=Get-Item "$base/T65.vhd"
 if((Get-FileHash $baseline.FullName).Hash -ne 'DABEF98CBFFEBA5801223C035080D4D5AA1BCDB7C5588C1CC69A46C7ED125E4E'){throw '1040 reference mismatch'}
 $source=[IO.File]::ReadAllText($baseline.FullName)
 [IO.File]::WriteAllText("$work/T65_ref.vhd",(($source -replace '(?i)\bT65\b','T65_ref') -replace '(?i)work\.T65_ALU\b','work.T65_ALU_ref'))
 $alu=[IO.File]::ReadAllText("$base/T65_ALU.vhd")
 [IO.File]::WriteAllText("$work/T65_ALU_ref.vhd",($alu -replace '(?i)\bT65_ALU\b','T65_ALU_ref'))
 & "$bin/vlib.exe" work *> "$out/cpu-vlib.log"
 if($LASTEXITCODE){throw 'vlib failed'}
 & "$bin/vcom.exe" -2008 board/rtl/bus_savestates.vhd board/rtl/t65/T65_Pack.vhd board/rtl/t65/T65_ALU.vhd board/rtl/t65/T65_MCode.vhd board/rtl/t65/T65.vhd T65_ALU_ref.vhd T65_ref.vhd *> "$out/cpu-vcom.log"
 if($LASTEXITCODE){throw 'CPU compile failed'}
 & "$bin/vlog.exe" -sv "$root/tests/nes-functional/ff3_cpu1041_tb.sv" *> "$out/cpu-vlog.log"
 if($LASTEXITCODE){throw 'test compile failed'}
 & "$bin/vsim.exe" -c -suppress 3009 work.ff3_cpu1041_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/cpu-sim.log"
 if($LASTEXITCODE -or !(Select-String "$out/cpu-sim.log" -Pattern '# PASS paired T65')){throw 'T65 execution or restore diverged'}
}finally{Pop-Location}
