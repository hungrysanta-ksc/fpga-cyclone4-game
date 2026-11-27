$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/..").Path
$board=(Resolve-Path $env:FF3_CHECKPOINT_BOARD).Path
$report=(Resolve-Path $env:FF3_PLAY_REPORT).Path
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$tmp=New-Item -Type Directory -Path (Join-Path $env:TEMP ('ff3-play-'+[guid]::NewGuid().ToString('N')))
Push-Location $tmp.FullName
try {
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'work library'}
 & "$bin/vlog.exe" -sv "$board/nes_display1010.sv" "$board/nes_screen_status151.sv" "$board/nes_menu_reply.sv" "$board/nes_rom_loader.sv" "$board/nes_run_observer134.sv" "$board/nes_checkpoint_spi.sv" "$root/tests/nes-functional/ff3_load_count_tb.sv" "$root/tests/nes-functional/ff3_spi_tb.sv" "$root/tests/nes-functional/ff3_menu_link_tb.sv"
 if($LASTEXITCODE){throw 'compile'}
 foreach($case in 'ff3_menu_link_tb','ff3_spi_tb','ff3_load_count_tb'){
  [string[]]$simArgs=@('-c')
  if($case -eq 'ff3_spi_tb'){$simArgs+='-gBOOT=1'}
  & "$bin/vsim.exe" @simArgs $case -do 'onerror {quit -code 1};run -all;quit -f' *> "$report/$case.log"
  if($LASTEXITCODE -or !(Select-String -LiteralPath "$report/$case.log" -SimpleMatch 'PASS FF3')){throw $case}
 }
}finally{Pop-Location}
& "$PSScriptRoot/check_ff3_checkpoint_rtl.ps1"
if($LASTEXITCODE){throw 'full FF3 core'}
