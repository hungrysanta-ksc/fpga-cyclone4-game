# Run with the project's single-seat Starter FLOAT wrapper.
$ErrorActionPreference='Stop'
$env:NES_CHR952='checked'
$env:NES_CHR951_GUARDS_ONLY='1'
& (Join-Path $PSScriptRoot 'check_nes_chr951.ps1')
$base=Join-Path $env:LOCALAPPDATA 'Temp'
$bin='C:/altera_standard/25.1std/questa_fse/win64/vsim.exe'
$prefix=$env:NES_954_MODE -eq 'prefix'
if (!$prefix -and $env:NES_954_MODE -ne 'full') {throw 'Choose prefix or full'}
Push-Location (Join-Path $base 'nes-952checked/nes-trial816-board952')
try {
 foreach($p in 1,2) {
  $opt=@('+admission954')
  $dir=Join-Path $base "nes-admission954/p$p"
  $frames=@(905)
  if ($prefix) {$opt+='+prefix954'} else {$frames+=906}
  foreach($g in $frames) {
   if (!$prefix) {$dir=Join-Path $base "nes-tile821-obj-jointmirror-p$p-954first-cold-pair/gen$g"}
   $log=Join-Path $dir "$(if ($prefix) {'prefix'} else {'full'}).log"
   & $bin -c -gREPLAY=1 -gRETAIN951=1 "-gG=$g" work951.tb_nes_port914 "+trace=$dir" @opt -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> $log
   $pass=if ($prefix) {'PASS954 prefix'} else {'PASS914 trace'}
   if ($LASTEXITCODE -or !(Select-String -LiteralPath $log -Pattern $pass -Quiet)) {throw "See $log"}
   $opt=@("+previous_rows=$dir/rows-out951.hex")
  }
 }
} finally {Pop-Location}
