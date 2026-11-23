$ErrorActionPreference = 'Stop'
$base = Join-Path $env:LOCALAPPDATA 'Temp'
$board = Join-Path $base 'nes-952checked/nes-trial816-board952'
$out = Join-Path $base 'nes-window957'
$tests = Join-Path (Split-Path $PSScriptRoot -Parent) 'tests/nes-functional'
$bin = 'C:/altera_standard/25.1std/questa_fse/win64'
New-Item -ItemType Directory -Force -Path $out | Out-Null
Copy-Item -LiteralPath (Join-Path $tests 'window957-grants.txt') -Destination (Join-Path $out 'calendar.txt')
Push-Location $out
try {
 if (!(Test-Path work)) { & "$bin/vlib.exe" work; if ($LASTEXITCODE) { throw 'vlib' } }
 $modules = 'nes_domain_reset124','nes_native_mailbox206','nes_plan_batch206','nes_e9_scan914',
  'nes_obj_capture611','nes_chr_cache611','nes_tile205','nes_native_arbiter165','nes_e9_rows914',
  'nes_source_tile192','nes_rom_physical','nes_bulk_aperture188','nes_tile_bulk206' |
  ForEach-Object { Join-Path $board "$_.sv" }
 & "$bin/vlog.exe" -sv '+define+NES_COMPANION952' @modules "$tests/tb_nes_port914.sv" "$tests/tb_nes_window957.sv" *> compile.log
 if ($LASTEXITCODE) { throw 'see nes-window957/compile.log' }
 $do = 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'
 & "$bin/vsim.exe" -c work.tb_nes_port914 -do $do *> guards.log
 if ($LASTEXITCODE -or !(Select-String guards.log -Pattern 'PASS914 checked' -Quiet)) { throw 'see guards.log' }
 foreach($gap in 1,2) { foreach($form in 'short','full') { foreach($lead in -50,75,1100) {
  $log = "gap$gap-$form-lead$lead.log"
  $extra = if ($form -eq 'full') { '+full_obj' } else { '+short_obj' }
  & "$bin/vsim.exe" -c work.tb_nes_window957 '+calendar=calendar.txt' "+gap=$gap" "+lead=$lead" $extra -do $do *> $log
  if ($LASTEXITCODE -or !(Select-String $log -Pattern 'PASS957 bytes=' -Quiet)) { throw "see $log" }
 }}}
} finally { Pop-Location }
