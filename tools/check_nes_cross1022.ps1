$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$job=Join-Path (Split-Path $repo -Parent) 'probes/nes-cross1022/rtl'
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$scratch=Join-Path $env:TEMP ('nes-cross1022-questa-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $scratch | Out-Null
Copy-Item -LiteralPath "$job/vectors.txt","$repo/rtl/nes_obj_cross1022.sv","$repo/rtl/nes_probe_order1022.sv","$repo/tests/nes-functional/tb_nes_cross1022.sv" -Destination $scratch
Push-Location $scratch
try {
 if(!(Test-Path work)){& "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib'}}
 & "$bin/vlog.exe" -sv nes_obj_cross1022.sv nes_probe_order1022.sv tb_nes_cross1022.sv *> "$job/compile.log"
 if($LASTEXITCODE){throw 'See compile.log'}
 & "$bin/vsim.exe" -c work.tb_nes_cross1022 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> "$job/run.log"
 if($LASTEXITCODE -or !(Select-String -Path "$job/run.log" -Pattern 'PASS1022 120' -Quiet)){throw 'See run.log'}
} finally {Pop-Location}
