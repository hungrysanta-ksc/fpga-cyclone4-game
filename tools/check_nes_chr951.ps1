$ErrorActionPreference='Stop'
$rev = if ($env:NES_CHR951_REV) { $env:NES_CHR951_REV } else { 'retain' }
if ($rev -notin 'retain','empty','neighbor','coldneighbor','control','banked','bankedcontrol') { throw 'Unknown board variant' }
$base = Join-Path $env:LOCALAPPDATA 'Temp'
$project = if ($rev -eq 'retain') { 'nes-trial816-board951' } elseif ($rev -eq 'control') { 'nes-board950/board950' } elseif ($rev -eq 'bankedcontrol') { 'nes-951banked/nes-trial816-board951' } else { "nes-951$rev/nes-trial816-board951" }
$board = Join-Path $base $project
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$bench=Join-Path (Split-Path $PSScriptRoot -Parent) 'tests/nes-functional/tb_nes_port914.sv'
Push-Location $board
try {
 if (!(Test-Path work951)) { & "$bin/vlib.exe" work951; if ($LASTEXITCODE) {throw 'vlib failed'} }
 $modules=@('nes_domain_reset124','nes_native_mailbox206','nes_plan_batch206','nes_e9_scan914',
   'nes_obj_capture611','nes_chr_cache611','nes_tile205','nes_native_arbiter165','nes_e9_rows914',
   'nes_source_tile192','nes_rom_physical','nes_bulk_aperture188','nes_tile_bulk206') | ForEach-Object { "$_.sv" }
 & "$bin/vlog.exe" -work work951 -sv @modules $bench *> compile951.log
 if($LASTEXITCODE){throw 'see compile951.log'}
 & "$bin/vsim.exe" -c work951.tb_nes_port914 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> guards951.log
 if(!(Select-String -Path guards951.log -Pattern 'PASS914 checked' -Quiet)){throw 'see guards951.log'}
 if($rev -in 'retain','empty','banked'){
  $extra=Join-Path (Split-Path $bench -Parent) 'tb_nes_chr951.sv'
  & "$bin/vlog.exe" -work work951 -sv $extra *> compileRow951.log
  if($LASTEXITCODE){throw 'see compileRow951.log'}
  & "$bin/vsim.exe" -c work951.tb_nes_chr951 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> row951.log
  if(!(Select-String -Path row951.log -Pattern 'PASS951 lease' -Quiet)){throw 'see row951.log'}
 }
 if($env:NES_CHR951_GUARDS_ONLY -eq '1'){return}
 $failed=@()
 foreach($cache in 'cold','warm'){foreach($phase in 1,2){
  if($rev -eq 'bankedcontrol' -and $cache -eq 'warm'){continue}
  $tag=if($rev -in 'control','bankedcontrol'){'neighbor'}else{$rev}
  $folder=Join-Path $base "nes-tile821-obj-jointmirror-p$phase-951$tag-$cache-pair"
  $previous=''
  $single=($rev -in 'neighbor','coldneighbor','control','bankedcontrol') -or ($rev -eq 'banked' -and $cache -eq 'warm')
  $frames=if($single){@(909,912)}else{@(905..912)}
  if($rev -eq 'bankedcontrol'){$frames=@(909)}
  $checkpointMode=if($single){2}else{1}
  foreach($g in $frames){
   $d=if($g -eq 912){$folder}else{Join-Path $folder "gen$g"}
   $opt=@()
   if($previous){$opt+= "+previous_rows=$previous"}
   $log=Join-Path $d ('port951-'+$rev+'.log')
   & "$bin/vsim.exe" -c -gREPLAY=1 "-gRETAIN951=$checkpointMode" "-gG=$g" work951.tb_nes_port914 "+trace=$d" @opt -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> $log
   if(!(Select-String -Path $log -Pattern 'PASS914 trace' -Quiet)){
    $failed+=$log
    if(!$single){break}
   }
   if(!(Select-String -Path $log -Pattern 'E8914 compared=[1-9][0-9]* different=0$' -Quiet)){
    $failed+="E8 timeline: $log"
   }
   $previous=Join-Path $d 'rows-out951.hex'
  }
 }}
 if($failed.Count){throw ("RTL mismatches: " + ($failed -join ", "))}
} finally {Pop-Location}
