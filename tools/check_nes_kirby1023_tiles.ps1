$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$work=Join-Path (Split-Path $repo -Parent) 'probes/nes-kirby1023'
$scratch=Join-Path $env:TEMP ('nes-kirby1023-tiles-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $scratch | Out-Null
foreach($m in 'nes_domain_reset124','nes_native_mailbox206','nes_e9_scan914','nes_plan_batch206','nes_tile205'){
 Copy-Item "$work/board/$m.sv" $scratch
}
Copy-Item -Path "$work/arm/chr.hex","$work/arm/plans.txt","$repo/tests/nes-functional/tb_nes_kirby1023.sv" -Destination $scratch
$bin='C:/altera_standard/25.1std/questa_fse/win64'
Push-Location $scratch
try {
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib'}
 & "$bin/vlog.exe" -sv @(Get-ChildItem *.sv -Name) *> "$work/tile-compile.log"
 if($LASTEXITCODE){throw 'See tile-compile.log'}
 & "$bin/vsim.exe" -c work.tb_nes_kirby1023 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> "$work/tile-run.log"
 if($LASTEXITCODE -or !(Select-String -Path "$work/tile-run.log" -Pattern 'PASS1023 tiles=647 ' -Quiet)){throw 'See tile-run.log'}
 Copy-Item tiles.txt "$work/arm/tiles.txt" -Force
} finally {Pop-Location}
