# Run under the project FLOAT wrapper with WATCH762_TEST set to the generated bench.
$ErrorActionPreference = 'Stop'
$bin762 = 'C:/altera_standard/25.1std/questa_fse/win64'
Push-Location -LiteralPath $env:WATCH762_TEST
try {
    & "$bin762/vlib.exe" work *> compile762.log
    if ($LASTEXITCODE) { throw 'vlib failed' }
    & "$bin762/vlog.exe" -sv nes_domain_reset124.sv nes_map_watch762.sv nes_sink_spi165.sv nes_sink_bus165.sv nes_sink_bridge165.sv watch762_tb.sv *>> compile762.log
    if ($LASTEXITCODE) { throw 'See compile762.log' }
    foreach ($phase762 in 0,8) {
        $log762 = "phase-$phase762.log"
        & "$bin762/vsim.exe" -c watch762_tb "-gPHASE=$phase762" -do 'onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0' *> $log762
        if ($LASTEXITCODE -or !(Select-String -LiteralPath $log762 -SimpleMatch PASS762 -Quiet)) { throw "See $log762" }
    }
} finally { Pop-Location }
