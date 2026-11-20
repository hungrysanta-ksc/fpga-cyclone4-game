$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$board=Join-Path $env:LOCALAPPDATA 'Temp/nes-trial816-board872'
$out=Join-Path $env:LOCALAPPDATA 'Temp/nes-retire878-endpoint'
$null=New-Item -ItemType Directory -Path $out -Force
Copy-Item "$repo/tests/nes-functional/retire878_tb.sv","$repo/tests/nes-functional/spi200_bus.svh" -Destination $out
Push-Location $out
try {
    $bin='C:/altera_standard/25.1std/questa_fse/win64'
    & "$bin/vlib" work
    if($LASTEXITCODE){exit $LASTEXITCODE}
    & "$bin/vlog" -sv '+incdir+.' "$board/nes_domain_reset124.sv" "$board/nes_plan_spi200.sv" retire878_tb.sv *> compile.log
    if($LASTEXITCODE){exit $LASTEXITCODE}
    & "$bin/vsim" -c work.retire878_tb -do 'onfinish exit; run -all; quit -f' *> run.log
    if($LASTEXITCODE){exit $LASTEXITCODE}
    if(!(Select-String -Quiet -SimpleMatch 'PASS retire878 9 conditions' run.log)){exit 1}
} finally { Pop-Location }
