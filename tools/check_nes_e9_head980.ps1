param()
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$tmp=Join-Path $env:LOCALAPPDATA 'Temp'
$board=Join-Path $tmp 'nes-trial816-board964'
Push-Location $board
try {
    if (!(Test-Path work980)) {
        & "$bin/vlib.exe" work980
        if ($LASTEXITCODE) { throw 'vlib failed' }
    }
    $modules=@('nes_domain_reset124','nes_native_mailbox206','nes_plan_spi200','nes_plan_batch206','nes_e9_scan914',
        'nes_obj_capture611','nes_chr_cache611','nes_tile205','nes_native_arbiter165','nes_e9_rows914',
        'nes_source_tile192','nes_rom_physical','nes_bulk_aperture188','nes_tile_bulk206') | ForEach-Object { "$_.sv" }
    & "$bin/vlog.exe" -work work980 -sv +define+NES_COMPANION952 +define+NES_MAIL964 @modules "$repo/tests/nes-functional/tb_nes_port914.sv" *> compile980.log
    if ($LASTEXITCODE) { throw 'see compile980.log' }
    foreach ($tag in '978returned','980checked2','980head5','980run8') {
        foreach ($phase in 1,2) {
            $d=Join-Path $tmp "nes-tile821-obj-jointmirror-p$phase-$tag-cold-pair/gen911"
            $log=Join-Path $d 'admit980.log'
            & "$bin/vsim.exe" -c -gREPLAY=1 -gG=911 work980.tb_nes_port914 "+trace=$d" +admission954 +prefix954 -do 'onerror {quit -code 1}; run -all; quit -code 0' *> $log
            if ($LASTEXITCODE -or !(Select-String -Quiet -LiteralPath $log -Pattern 'PASS954 prefix')) { throw "see $log" }
        }
    }
} finally { Pop-Location }
