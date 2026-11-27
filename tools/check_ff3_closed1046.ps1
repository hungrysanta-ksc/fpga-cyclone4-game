param([Parameter(Mandatory)][string]$Board,[Parameter(Mandatory)][string]$Report)
$ErrorActionPreference='Stop'
$src=(Resolve-Path $Board).Path
$tb=(Resolve-Path "$PSScriptRoot/../tests/nes-functional/ff3_closed1046_tb.sv").Path
$out=[IO.Directory]::CreateDirectory($Report).FullName
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$scratch=[IO.Directory]::CreateDirectory((Join-Path $env:TEMP ('ff3-closed1046-'+[guid]::NewGuid().ToString('N'))))
Push-Location $scratch.FullName
try {
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib'}
 & "$bin/vlog.exe" -sv "$src/nes_native_compact181.sv" "$src/nes_native_planes165.sv" "$src/nes_native_raster181.sv" "$src/nes_patch_capture181.sv" "$src/nes_patch_rows181.sv" "$src/nes_native_frame201.sv" $tb *> "$out/closed-vlog.log"
 if($LASTEXITCODE){throw 'forced blank test compile'}
 & "$bin/vsim.exe" -c ff3_closed1046_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/closed-test.log"
 if($LASTEXITCODE -or !(Select-String -LiteralPath "$out/closed-test.log" -SimpleMatch 'PASS forced blank')){throw 'forced blank test failed'}
}finally{Pop-Location}
