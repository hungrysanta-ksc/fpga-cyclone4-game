param([Parameter(Mandatory)][string]$Board,[Parameter(Mandatory)][string]$Report,[string]$FlashReference)
$ErrorActionPreference='Stop'
$src=(Resolve-Path $Board).Path
$tb=(Resolve-Path "$PSScriptRoot/../tests/nes-functional/ff3_battle1047_tb.sv").Path
$out=[IO.Directory]::CreateDirectory($Report).FullName
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$scratch=[IO.Directory]::CreateDirectory((Join-Path $env:TEMP ('ff3-battle1047-'+[guid]::NewGuid().ToString('N'))))
$arguments=@()
if($FlashReference) {
 Copy-Item -LiteralPath $FlashReference -Destination (Join-Path $scratch.FullName 'flash.hex')
 $arguments=@('+reference')
}
$defines=@()
if(Select-String -LiteralPath "$src/nes_chr_snapshot.sv" -SimpleMatch 'output reg [7:0] clean_pages') {
 $defines=@('+define+FF3_PAGE_HISTORY')
}
Push-Location $scratch.FullName
try {
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib'}
 & "$bin/vlog.exe" -sv @defines "$src/nes_chr_snapshot.sv" "$src/nes_native_raster181.sv" $tb *> "$out/battle-vlog.log"
 if($LASTEXITCODE){throw 'battle test compile'}
 & "$bin/vsim.exe" -c ff3_battle1047_tb @arguments -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/battle-test.log"
 if($LASTEXITCODE -or !(Select-String -LiteralPath "$out/battle-test.log" -SimpleMatch 'PASS FF3 battle palettes')){throw 'battle test failed'}
 if($FlashReference){Copy-Item -LiteralPath 'effective.hex' -Destination (Join-Path $out 'effective.hex')}
}finally{Pop-Location}
