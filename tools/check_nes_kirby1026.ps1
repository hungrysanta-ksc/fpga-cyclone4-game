$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$probes=Join-Path (Split-Path $repo -Parent) 'probes'
$board=Join-Path $probes 'nes-kirby1023/board'
$out=Join-Path $probes 'nes-kirby1026'
New-Item -ItemType Directory -Force $out | Out-Null
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$scratch=Join-Path $env:TEMP ('nes-kirby1026-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $scratch | Out-Null
Push-Location $scratch
try {
 if (!(Test-Path work)) { & "$bin/vlib.exe" work; if ($LASTEXITCODE) { throw 'vlib' } }
 $files=foreach ($name in 'nes_domain_reset124','nes_native_mailbox206','nes_bulk_aperture188','nes_tile_bulk206','nes_chr_cache611','nes_obj_capture611','nes_e9_rows914','nes_tile205','nes_native_arbiter165','nes_source_tile192') { Join-Path $board "$name.sv" }
 Copy-Item -LiteralPath $files -Destination $scratch
 Copy-Item "$repo/tests/nes-functional/tb_nes_kirby1026.sv" $scratch
 & "$bin/vlog.exe" -sv @(Get-ChildItem *.sv -Name) *> "$out/compile.log"
 if ($LASTEXITCODE) {throw "See $out/compile.log"}
 foreach ($case in 0..4) {
  & "$bin/vsim.exe" -c work.tb_nes_kirby1026 "+CASE=$case" -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> "$out/case$case.log"
  if ($LASTEXITCODE -or !(Select-String -Path "$out/case$case.log" -Pattern "PASS1026 case=$case " -Quiet)) {throw "See $out/case$case.log"}
 }
} finally {Pop-Location}
