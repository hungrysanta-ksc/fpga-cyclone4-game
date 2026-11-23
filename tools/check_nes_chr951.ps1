$ErrorActionPreference='Stop'
$rev = if ($env:NES_CHR951_REV) { $env:NES_CHR951_REV } else { 'retain' }
$variant952=$env:NES_CHR952
if($variant952 -and $variant952 -notin 'pair','halves','checked'){throw 'Unknown 952 board'}
if ($rev -notin 'retain','empty','neighbor','coldneighbor','control','banked','bankedcontrol') { throw 'Unknown board variant' }
$base = Join-Path $env:LOCALAPPDATA 'Temp'
$project = if ($rev -eq 'retain') { 'nes-trial816-board951' } elseif ($rev -eq 'control') { 'nes-board950/board950' } elseif ($rev -eq 'bankedcontrol') { 'nes-951banked/nes-trial816-board951' } else { "nes-951$rev/nes-trial816-board951" }
$prefix=951
$defines=@()
if($variant952){
 $prefix=952
 $rev=$variant952
 $project="nes-952$rev/nes-trial816-board952"
 $defines=@('+define+NES_COMPANION952')
}
$board = Join-Path $base $project
if ($env:NES_TAIL961 -eq 'pair') {
 if ($variant952 -ne 'checked') { throw '961 requires the checked row-cache build' }
 $board=Join-Path $base 'nes-trial816-board961'
}
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$bench=Join-Path (Split-Path $PSScriptRoot -Parent) 'tests/nes-functional/tb_nes_port914.sv'
Push-Location $board
try {
 if (!(Test-Path work951)) { & "$bin/vlib.exe" work951; if ($LASTEXITCODE) {throw 'vlib failed'} }
 $modules=@('nes_domain_reset124','nes_native_mailbox206','nes_plan_batch206','nes_e9_scan914',
   'nes_obj_capture611','nes_chr_cache611','nes_tile205','nes_native_arbiter165','nes_e9_rows914',
   'nes_source_tile192','nes_rom_physical','nes_bulk_aperture188','nes_tile_bulk206') | ForEach-Object { "$_.sv" }
 & "$bin/vlog.exe" -work work951 -sv @defines @modules $bench *> compile951.log
 if($LASTEXITCODE){throw 'see compile951.log'}
 & "$bin/vsim.exe" -c work951.tb_nes_port914 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> guards951.log
 if(!(Select-String -Path guards951.log -Pattern 'PASS914 checked' -Quiet)){throw 'see guards951.log'}
 if($variant952 -or $rev -in 'retain','empty','banked'){
  $extra=Join-Path (Split-Path $bench -Parent) 'tb_nes_chr951.sv'
  & "$bin/vlog.exe" -work work951 -sv $extra *> compileRow951.log
  if($LASTEXITCODE){throw 'see compileRow951.log'}
  & "$bin/vsim.exe" -c work951.tb_nes_chr951 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> row951.log
  if(!(Select-String -Path row951.log -Pattern 'PASS951 lease' -Quiet)){throw 'see row951.log'}
 }
 if($variant952){
  $extra=Join-Path (Split-Path $bench -Parent) 'tb_nes_companion952.sv'
  & "$bin/vlog.exe" -work work951 -sv $extra *> compileRow952.log
  if($LASTEXITCODE){throw 'see compileRow952.log'}
  & "$bin/vsim.exe" -c work951.tb_nes_companion952 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> row952.log
  if(!(Select-String -Path row952.log -Pattern 'PASS952 16 actual' -Quiet)){throw 'see row952.log'}
 }
 if($env:NES_CHR951_GUARDS_ONLY -eq '1'){return}
 $failed=@()
 $feedback=$env:NES_FEEDBACK953
 if($feedback -and ($feedback -notmatch '^953[a-z0-9]+$' -or $variant952 -ne 'checked')){throw 'Invalid feedback replay'}
 foreach($cache in 'cold','warm'){foreach($phase in 1,2){
  if($feedback -and $env:NES_FEEDBACK953_COLD2 -eq '1' -and ($cache -ne 'cold' -or $phase -ne 2)){continue}
  if($rev -eq 'bankedcontrol' -and $cache -eq 'warm'){continue}
  $tag=if($rev -in 'control','bankedcontrol'){'neighbor'}else{$rev}
  if($variant952 -and $env:NES_CHR952_RTL_ROWS -eq '1'){$tag+='rows'}
  $folder=Join-Path $base "nes-tile821-obj-jointmirror-p$phase-$prefix$tag-$cache-pair"
  if($feedback){$folder=Join-Path $base "nes-tile821-obj-jointmirror-p$phase-$feedback-$cache-pair"}
  $previous=''
  $single=($rev -in 'neighbor','coldneighbor','control','bankedcontrol') -or (($variant952 -or $rev -eq 'banked') -and $cache -eq 'warm')
  $frames=if($single){@(909,912)}else{@(905..912)}
  if($rev -eq 'bankedcontrol'){$frames=@(909)}
  if($feedback -and !$single){
   $frames=@(908..912)
   $previous=Join-Path $base "nes-tile821-obj-jointmirror-p$phase-952checkedrows-cold-pair/gen907/rows-out951.hex"
  }
  $checkpointMode=if($single){2}else{1}
  foreach($g in $frames){
   $d=if($g -eq 912){$folder}else{Join-Path $folder "gen$g"}
   $opt=@()
   if($previous){$opt+= "+previous_rows=$previous"}
   $log=Join-Path $d ('port'+$prefix+'-'+$rev+'.log')
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
