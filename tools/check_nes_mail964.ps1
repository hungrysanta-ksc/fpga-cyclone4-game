$ErrorActionPreference = 'Stop'
$board = Join-Path $env:LOCALAPPDATA 'Temp/nes-trial816-board964'
$tempDir = Split-Path $board -Parent
$bench = Join-Path (Split-Path $PSScriptRoot -Parent) 'tests/nes-functional'
$bin = 'C:/altera_standard/25.1std/questa_fse/win64'
Push-Location $board
try {
 if (!(Test-Path work964)) { & "$bin/vlib.exe" work964; if ($LASTEXITCODE) {throw 'vlib failed'} }
 $modules=@('nes_domain_reset124','nes_native_mailbox206','nes_plan_spi200','nes_plan_batch206','nes_e9_scan914',
   'nes_obj_capture611','nes_chr_cache611','nes_tile205','nes_native_arbiter165','nes_e9_rows914',
   'nes_source_tile192','nes_rom_physical','nes_bulk_aperture188','nes_tile_bulk206') | ForEach-Object { "$_.sv" }
 & "$bin/vlog.exe" -work work964 -sv +define+NES_COMPANION952 +define+NES_MAIL964 @modules "$bench/tb_nes_port914.sv" "$bench/tb_nes_page963.sv" *> compile964.log
 if ($LASTEXITCODE) {throw 'see compile964.log'}
 $script = 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0'
 & "$bin/vsim.exe" -c -gCONSUMER_CAPTURE=0 work964.tb_nes_page963 -do $script *> guards964.log
 if ($LASTEXITCODE -or !(Select-String -Quiet -Path guards964.log -Pattern 'PASS963 SPI')) {throw 'see guards964.log'}
 $tag=if($env:NES_MAIL964_TAG){$env:NES_MAIL964_TAG}else{'963bnes-mail964both'}
 $intervals=$tag -match '^965wire[1-9][0-9]?$'
 if(!$intervals -and $tag -notin '963bnes-mail964both','964feedback','964recheck','965first','965both','965tail'){throw 'unexpected replay'}
 foreach($phase in 1,2){
  if(($intervals -or $tag -eq '965tail') -and $env:NES_965_PHASE -in '1','2' -and $phase -ne [int]$env:NES_965_PHASE){continue}
  $base=Join-Path $tempDir "nes-tile821-obj-jointmirror-p$phase-$tag-cold-pair"
  $previous=$null
  $end=if($tag -in '965first','965both' -or $env:NES_965_LEAD_ONLY -eq '1'){906}else{912}
  $first=905
  if($tag -eq '965tail'){
   $digest,$previous=Get-Content -LiteralPath "$base/checkpoint965.txt"
   if((Get-FileHash -LiteralPath $previous -Algorithm SHA256).Hash -ne $digest){throw 'row checkpoint changed'}
   $first=910
  }
  foreach($g in $first..$end){
   $d=if($g -eq 912){$base}else{Join-Path $base "gen$g"}
   $options=@("+trace=$d",'+all_e8_differences')
   if($tag -like '965*' -and $g -le 906){$options+='+timing958'}
   $admission=($tag -eq '965both' -and $g -in 905,906) -or ($tag -eq '965first' -and $g -eq 905)
   if($intervals -and $g -le 906){$admission=$true;$options+='+multiple965'}
   if($admission){$options+='+admission954'}
   if($previous){$options+="+previous_rows=$previous"}
   $page=Get-Content -LiteralPath "$d/mail964.txt"
   if($page -ne 'none'){ $at,$packet=$page -split ' '; $options+="+page_at=$at"; $options+="+page_bytes=$packet" }
   & "$bin/vsim.exe" -c -gREPLAY=1 -gRETAIN951=1 "-gG=$g" work964.tb_nes_port914 @options -do $script *> "$d/mail964.log"
   if($LASTEXITCODE -or !(Select-String -Quiet -LiteralPath "$d/mail964.log" -Pattern 'PASS914 trace')){throw "see $d/mail964.log"}
   if($admission -and !(Select-String -Quiet -LiteralPath "$d/mail964.log" -Pattern 'ACCEPT954 batch=')){throw "missing E9 admission for $g"}
   if($intervals -and $end -eq 912 -and $g -le 906 -and
      !(Select-String -Quiet -LiteralPath "$d/mail964.log" -Pattern 'E8914 compared=\d+ different=0$')){
    throw "ARM and RTL credit differ in $g"
   }
   if($page -ne 'none' -and !(Select-String -Quiet -LiteralPath "$d/mail964.log" -Pattern 'PAGE964 accepted')){throw 'missing mailbox admission'}
   $previous="$d/rows-out951.hex"
  }
 }
} finally {Pop-Location}
