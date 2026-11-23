# Run inside the existing Starter FLOAT wrapper; keep the original 952 evidence intact.
$ErrorActionPreference='Stop'
$env:NES_CHR952='checked'
$env:NES_CHR951_GUARDS_ONLY='1'
& (Join-Path $PSScriptRoot 'check_nes_chr951.ps1')
$base=Join-Path $env:LOCALAPPDATA 'Temp'
$bin='C:/altera_standard/25.1std/questa_fse/win64/vsim.exe'
Push-Location (Join-Path $base 'nes-952checked/nes-trial816-board952')
try {
 foreach($phase in 1,2){
  $previous=@()
  foreach($g in 905,906){
   $from=Join-Path $base "nes-tile821-obj-jointmirror-p$phase-952checkedrows-cold-pair/gen$g"
   $out=Join-Path $base "nes-review174/p$phase/gen$g"
   New-Item -ItemType Directory -Force -Path $out | Out-Null
   Get-ChildItem -LiteralPath $from -File | Where-Object { $_.Name -match '914\.(hex|txt)$' } | Copy-Item -Destination $out
   $log=Join-Path $out 'all-e8.log'
   & $bin -c -gREPLAY=1 -gRETAIN951=1 "-gG=$g" work951.tb_nes_port914 "+trace=$out" @previous '+all_e8_differences' -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> $log
   if($LASTEXITCODE -or !(Select-String -LiteralPath $log -Pattern 'PASS914 trace' -Quiet)){throw "Failed generation $g phase $phase"}
   $previous=@("+previous_rows=$out/rows-out951.hex")
  }
 }
} finally {Pop-Location}
