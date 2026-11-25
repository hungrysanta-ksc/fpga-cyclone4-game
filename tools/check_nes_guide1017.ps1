param([int[]]$Phases=@(1,2,3),[string]$TempDir=[IO.Path]::GetTempPath(),[string]$QuestaBin='C:/altera_standard/25.1std/questa_fse/win64')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$work=Join-Path $TempDir 'nes-prefetch1017'
Set-Location -LiteralPath (Join-Path $work 'test')
if (!(Test-Path 'work')) { & "$QuestaBin/vlib.exe" work; if ($LASTEXITCODE) {exit $LASTEXITCODE} }
$board=Join-Path $TempDir 'nes-display1010-boardD'
$modules=@('nes_tile205','nes_native_arbiter165','nes_obj_capture611','nes_chr_cache611') | ForEach-Object {Join-Path $board "$_.sv"}
& "$QuestaBin/vlog.exe" @modules -sv ../board/nes_e9_rows914.sv ../board/nes_source_tile192.sv ../board/nes_direct206.sv ../board/nes_live_joint.sv "$root/tests/nes-functional/tb_nes_guide1017.sv" "$root/tests/nes-functional/tb_nes_guide_source1017.sv" *> compile.log
if ($LASTEXITCODE) {Get-Content compile.log -Tail 20;exit $LASTEXITCODE}
foreach ($phase in $Phases) {
 foreach ($mode in 0,1,2) {
  $log="phase-$phase-mode-$mode.log"
  & "$QuestaBin/vsim.exe" -c work.tb_nes_guide1017 "+PHASE=$phase" "+MODE=$mode" -do 'onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0' *> $log
  if ($LASTEXITCODE -or !(Select-String -LiteralPath $log -Pattern 'PASS checked')) {Get-Content $log -Tail 15;exit 1}
  $sourceLog="source-$phase-$mode.log"
  & "$QuestaBin/vsim.exe" -c work.tb_nes_guide_source1017 "+PHASE=$phase" "+MODE=$mode" -do 'onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0' *> $sourceLog
  if ($LASTEXITCODE -or !(Select-String -LiteralPath $sourceLog -Pattern 'SOURCE .*PASS')) {Get-Content $sourceLog -Tail 15;exit 1}
  Select-String -LiteralPath $log -Pattern 'RESULT|PASS checked'
 }
}

if (!(Test-Path 'ref1012')) { & "$QuestaBin/vlib.exe" ref1012; if ($LASTEXITCODE) {exit $LASTEXITCODE} }
& "$QuestaBin/vlog.exe" -work ref1012 -sv +define+MMC1012_REF @modules "$board/nes_source_tile192.sv" "$board/nes_e9_rows914.sv" "$root/tests/nes-functional/tb_nes_guide_source1017.sv" *> ref-compile.log
if ($LASTEXITCODE) {Get-Content ref-compile.log -Tail 12;exit 1}
foreach ($phase in $Phases) {
 $log="original-$phase.log"
 & "$QuestaBin/vsim.exe" -c ref1012.tb_nes_guide_source1017 "+PHASE=$phase" '+MODE=0' -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> $log
 if ($LASTEXITCODE -or !(Select-String -LiteralPath $log -Pattern 'SOURCE .*PASS')) { Get-Content $log -Tail 12;exit 1 }
}
