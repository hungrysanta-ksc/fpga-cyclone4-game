$ErrorActionPreference='Stop'
$repo=(Resolve-Path "$PSScriptRoot/..").Path
$python="$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$work=New-Item -Type Directory -Path (Join-Path $env:TEMP ('ff3-menu-'+[guid]::NewGuid().ToString('N')))
$board=Join-Path $work.FullName 'board'
& $python "$repo/tools/prepare_ff3_menu_board.py" $board
if($LASTEXITCODE){throw 'FF3 menu board generation failed'}
Push-Location $work.FullName
try {
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib failed'}
 & "$bin/vlog.exe" -sv "$board/nes_display1010.sv" "$board/nes_menu_reply.sv" "$board/nes_screen_status151.sv" "$repo/tests/nes-functional/ff3_menu_link_tb.sv"
 if($LASTEXITCODE){throw 'menu bus compile failed'}
 $report=Join-Path $repo '../probes/nes-ff3-1043/menu-link.log'
 & "$bin/vsim.exe" -c ff3_menu_link_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> $report
 if($LASTEXITCODE -or !(Select-String -LiteralPath $report -SimpleMatch 'PASS FF3 menu SNES write')){throw 'menu bus simulation failed'}
}finally{Pop-Location}
