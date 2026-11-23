$ErrorActionPreference = 'Stop'
$board = Join-Path $env:LOCALAPPDATA 'Temp/nes-board950/board950'
$bin = 'C:/altera_standard/25.1std/questa_fse/win64'
$bench = Join-Path (Split-Path $PSScriptRoot -Parent) 'tests/nes-functional/tb_nes_port914.sv'
Push-Location $board
try {
    $lib = 'port950'
    if (!(Test-Path $lib)) {
        & "$bin/vlib.exe" $lib
        if ($LASTEXITCODE) { throw 'Questa library setup failed' }
    }
    $modules = @('nes_domain_reset124','nes_native_mailbox206','nes_plan_batch206','nes_e9_scan914',
        'nes_obj_capture611','nes_chr_cache611','nes_tile205','nes_native_arbiter165',
        'nes_e9_rows914','nes_source_tile192','nes_rom_physical',
        'nes_bulk_aperture188','nes_tile_bulk206') | ForEach-Object { "$_.sv" }
    & "$bin/vlog.exe" -work $lib -sv @modules $bench *> compile-port950.log
    if ($LASTEXITCODE) { throw 'See compile-port950.log' }
    foreach ($phase in 1,2) {
        $trace = Join-Path $env:LOCALAPPDATA "Temp/nes-tile821-obj-jointmirror-p$phase-950rtl-cold-pair"
        $log = "port950-cold$phase.log"
        & "$bin/vsim.exe" -c -gREPLAY=1 -gG=912 "$lib.tb_nes_port914" "+trace=$trace" -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> $log
        if ($LASTEXITCODE -or !(Select-String $log -Pattern 'PASS914 trace' -Quiet)) { throw "See $log" }
    }
} finally { Pop-Location }
