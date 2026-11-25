$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$job=Join-Path (Split-Path $repo -Parent) 'probes/nes-cross1022/load'
$scratch=Join-Path $env:TEMP ('nes-kirby1022-load-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $scratch | Out-Null
Copy-Item -Path "$job/*.sv","$job/payload.bin","$repo/tests/nes-functional/tb_nes_kirby1022_load.sv" -Destination $scratch
$bin='C:/altera_standard/25.1std/questa_fse/win64'
Push-Location $scratch
try {
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib'}
 & "$bin/vlog.exe" -sv @(Get-ChildItem *.sv -Name) *> "$job/compile.log"
 if($LASTEXITCODE){throw 'See compile.log'}
 & "$bin/vsim.exe" -c work.tb_nes_kirby1022_load -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> "$job/run.log"
 if($LASTEXITCODE -or !(Select-String -Path "$job/run.log" -Pattern 'PASS1022 786432' -Quiet)){throw 'See run.log'}
} finally {Pop-Location}
