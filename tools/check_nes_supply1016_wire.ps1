$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$board=$env:NES1016_BOARD
if (!(Test-Path -LiteralPath "$board/nes_supply1016.sv")) { throw 'Set NES1016_BOARD to the generated board project' }
$out=Join-Path $board 'wire'
New-Item -ItemType Directory -Force $out | Out-Null
$bin='C:/altera_standard/25.1std/questa_fse/win64'
Push-Location $out
try {
 if (!(Test-Path work)) { & "$bin/vlib.exe" work; if ($LASTEXITCODE) { throw 'vlib' } }
 Copy-Item -LiteralPath "$root/tests/nes-functional/tb_nes_supply1016.sv" -Destination .
 & "$bin/vlog.exe" -sv "$board/nes_screen_status151.sv" "$board/nes_supply1016_host.sv" "$board/nes_supply1016.sv" tb_nes_supply1016.sv *> compile.log
 if ($LASTEXITCODE) {throw 'vlog failed, see compile.log'}
 & "$bin/vsim.exe" -c -suppress 3009 tb_nes_supply1016 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> sim.log
 if ($LASTEXITCODE -or !(Select-String -Path sim.log -Pattern 'PASS1016' -Quiet)) {throw 'capture test failed, see sim.log'}
 Copy-Item -LiteralPath "$root/tests/nes-functional/tb_nes_supply1016_source.sv" -Destination .
 $files=foreach ($name in 'nes_source_tile192','nes_chr_cache611','nes_obj_capture611','nes_tile205','nes_e9_rows914','nes_native_arbiter165') {Join-Path $board "$name.sv"}
 & "$bin/vlog.exe" -sv @files tb_nes_supply1016_source.sv *> source-compile.log
 if ($LASTEXITCODE) {throw 'source compilation failed'}
 & "$bin/vsim.exe" -c tb_nes_supply1016_source -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> source-sim.log
 if ($LASTEXITCODE -or !(Select-String -Path source-sim.log -Pattern 'PASS1016' -Quiet)) {throw 'source test failed'}
} finally {Pop-Location}
