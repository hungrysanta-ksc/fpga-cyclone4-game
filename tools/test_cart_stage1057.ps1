$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/..").Path
$out=(Resolve-Path "$root/../probes/nes-carts1057").Path
$q='C:/altera_standard/25.1std/questa_fse/win64'
$job=New-Item -Type Directory -Path (Join-Path $env:TEMP ('cart-stage-'+[guid]::NewGuid().ToString('N')))
Copy-Item -LiteralPath "$out/board-21/nes_rom_service.sv","$out/board-7/nes_chr_snapshot.sv","$root/tests/nes-functional/cart_stage1057_tb.sv" -Destination $job.FullName
Copy-Item -LiteralPath "$out/rows.txt" -Destination $job.FullName
Copy-Item -LiteralPath "$out/pattern-7.txt" -Destination $job.FullName
Push-Location $job.FullName
try {
 & "$q/vlib.exe" work
 if($LASTEXITCODE){throw 'work library'}
 & "$q/vlog.exe" -sv nes_rom_service.sv nes_chr_snapshot.sv cart_stage1057_tb.sv *> "$out/stage-vlog.log"
 if($LASTEXITCODE){throw 'stage compile'}
 & "$q/vsim.exe" -c cart_stage1057_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/stage-vsim.log"
 if($LASTEXITCODE -or !(Select-String -Quiet -LiteralPath "$out/stage-vsim.log" -Pattern '^# PASS1057 ')){throw 'stage regression'}
} finally {Pop-Location}
