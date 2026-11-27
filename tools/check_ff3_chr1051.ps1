param([Parameter(Mandatory)][string]$Board,[Parameter(Mandatory)][string]$Report)
$ErrorActionPreference='Stop'
$src=(Resolve-Path $Board).Path
$tb=(Resolve-Path "$PSScriptRoot/../tests/nes-functional/ff3_chr_group1051_tb.sv").Path
$out=[IO.Directory]::CreateDirectory($Report).FullName
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$scratch=[IO.Directory]::CreateDirectory((Join-Path $env:TEMP ('ff3-chr1051-'+[guid]::NewGuid().ToString('N'))))
Push-Location $scratch.FullName
try {
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib'}
 & "$bin/vlog.exe" -sv "$src/nes_chr_snapshot.sv" "$src/nes_native_export203.sv" $tb "$src/nes_rom_loader.sv" "$PSScriptRoot/../tests/nes-functional/ff3_load_count_tb.sv" *> "$out/chr-vlog.log"
 if($LASTEXITCODE){throw 'CHR and loader test compile'}
 & "$bin/vsim.exe" -c ff3_chr_group1051_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/chr.log"
 if($LASTEXITCODE -or !(Select-String -LiteralPath "$out/chr.log" -SimpleMatch 'PASS1051')){throw 'STOP test failed'}
 & "$bin/vsim.exe" -c ff3_load_count_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/loader.log"
 if($LASTEXITCODE -or !(Select-String -LiteralPath "$out/loader.log" -SimpleMatch 'PASS FF3 loader 524288')){throw 'loader test failed'}
}finally{Pop-Location}
