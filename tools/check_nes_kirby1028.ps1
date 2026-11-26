param([switch]$MailboxOnly)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$probes=Join-Path (Split-Path $repo -Parent) 'probes'
$out=Join-Path $probes 'nes-kirby1028'
$board=Join-Path $probes 'nes-kirby1027/board-tag'
$bin='C:/altera_standard/25.1std/questa_fse/win64'
foreach($version in 0,1){
 $scratch=Join-Path $env:TEMP ('nes-kirby1028-'+[guid]::NewGuid().ToString('N'))
 New-Item -ItemType Directory $scratch | Out-Null
 foreach($m in 'nes_plan_batch206','nes_e9_scan914','nes_native_mailbox206','nes_domain_reset124','nes_chr_cache611','nes_obj_capture611','nes_e9_rows914','nes_tile205','nes_native_arbiter165','nes_source_tile192'){
  $src=if($version -and $m -eq 'nes_e9_rows914'){$out}else{$board}
  Copy-Item -LiteralPath "$src/$m.sv" -Destination $scratch
 }
 Copy-Item "$out/batch*.hex","$out/case*.txt","$out/grants*.txt","$probes/nes-kirby1023/arm/chr.hex","$repo/tests/nes-functional/tb_nes_kirby1028.sv" $scratch
 Push-Location $scratch
 try{
  & "$bin/vlib.exe" work
  if($LASTEXITCODE){throw 'vlib'}
  & "$bin/vlog.exe" -sv @(Get-ChildItem *.sv -Name) *> "$out/compile-$version.log"
  if($LASTEXITCODE){throw "compile-$version.log"}
  foreach($phase in 1,2,3){
   $modes=@(0,1,2,4)
   if($version){
    if($phase -eq 1){$modes+=3}
    $modes+=5..7
   }
   if($phase -le 2){$modes+=8,9}
   if($MailboxOnly){$modes=@($modes | Where-Object {$_ -ge 8})}
   foreach($mode in $modes){
    $log="$out/run-$version-$phase-$mode.log"
    & "$bin/vsim.exe" -c work.tb_nes_kirby1028 "+PHASE=$phase" "+MODE=$mode" "+VERSION=$version" -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> $log
    if($LASTEXITCODE -or !(Select-String -Path $log -Pattern '^# PASS1028' -Quiet)){throw "Failed run-$version-$phase-$mode.log"}
   }
  }
 }finally{Pop-Location}
}
