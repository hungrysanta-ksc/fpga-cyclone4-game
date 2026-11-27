param([Parameter(Mandatory)][string]$Board,[Parameter(Mandatory)][string]$Report)
$ErrorActionPreference='Stop'
$src=(Resolve-Path $Board).Path
$fixture=(Resolve-Path "$PSScriptRoot/../tests/nes-functional").Path
$out=[IO.Directory]::CreateDirectory($Report).FullName
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$py="$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
$scratch=New-Item -ItemType Directory -Path (Join-Path $env:TEMP ('ff3-pages-'+[guid]::NewGuid().ToString('N')))
& $py "$PSScriptRoot/ff3_chr_fixture1037.py" $scratch.FullName
if($LASTEXITCODE){throw 'FF3 tile reference'}
Push-Location $scratch
try {
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib failed'}
 & "$bin/vlog.exe" -sv '+define+FF3_PAGES' "$src/nes_chr_snapshot.sv" "$src/nes_tile205.sv" "$src/nes_source_tile192.sv" "$fixture/ff3_display_tb.sv" *> "$out/page-vlog.log"
 if($LASTEXITCODE){throw 'page test compile'}
 & "$bin/vsim.exe" -c ff3_display_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/pages.log"
 if($LASTEXITCODE -or !(Select-String -LiteralPath "$out/pages.log" -SimpleMatch 'PASS FF3 8192B snapshot')){throw 'page data / STOP test failed'}
 $maskDefines=@()
 if(Select-String -LiteralPath "$src/nes_native_raster181.sv" -SimpleMatch 'non_backdrop'){$maskDefines+=('+define+FF3_BACKDROP')}
 if(Select-String -LiteralPath "$src/nes_native_raster181.sv" -SimpleMatch 'reg copy_gray;'){$maskDefines+=('+define+FF3_GRAYSCALE')}
 & "$bin/vlog.exe" -sv @maskDefines "$src/nes_native_raster181.sv" "$fixture/ff3_mask1045_tb.sv" *> "$out/mask-vlog.log"
 if($LASTEXITCODE){throw 'mask compile'}
 & "$bin/vsim.exe" -c ff3_mask1045_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/mask.log"
 if($LASTEXITCODE -or !(Select-String -LiteralPath "$out/mask.log" -SimpleMatch 'PASS FF3 mask 256 cases')){throw 'mask rows'}
}finally{Pop-Location}
