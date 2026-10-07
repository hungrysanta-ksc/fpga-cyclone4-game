# SPDX-License-Identifier: MIT
param(
 [Parameter(Mandatory=$true)][string]$SourceRoot,
 [Parameter(Mandatory=$true)][string]$ArmBin,
 [Parameter(Mandatory=$true)][string]$HostGcc,
 [Parameter(Mandatory=$true)][string]$Make,
 [Parameter(Mandatory=$true)][string]$UnixBin,
 [string]$QuartusBin,
 [string]$MiniImage,
 [ValidatePattern('^[D-Z]:$')][string]$Drive='W:',
 [ValidatePattern('^[D-Z]:$')][string]$ArmDrive='V:'
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath $SourceRoot).Path
$arm=(Resolve-Path -LiteralPath $ArmBin).Path
$savedPath=$env:PATH
if($Drive -eq $ArmDrive -or (Test-Path "$Drive\") -or (Test-Path "$ArmDrive\")){throw "Build drives must be distinct and unused"}
& subst $Drive $root
if($LASTEXITCODE -ne 0){throw 'ASCII build drive mapping failed'}
try {
 & subst $ArmDrive (Split-Path $arm)
 if($LASTEXITCODE -ne 0){throw "ARM drive mapping failed"}
 $env:PATH="$ArmDrive/bin;$UnixBin;$(Split-Path $HostGcc);"+$savedPath
 $work="$Drive/"
 foreach($tool in @('bin2c','rle')){
  & $HostGcc -Wall -Wstrict-prototypes -Werror "$work/utils/$tool.c" -o "$work/utils/$tool.exe"
  if($LASTEXITCODE -ne 0){throw "$tool build failed"}
 }
 & $HostGcc -Wall -Wstrict-prototypes -Werror "$work/src/utils/genhdr.c" -o "$work/src/utils/genhdr.exe"
 if($LASTEXITCODE -ne 0){throw 'genhdr build failed'}
 $mini="$work/verilog/sd2snes_mini"
 if($MiniImage){
  $expected='9ae79c3028391063338d42ae16b19acf48d0d80858939b015ef6481f55cbefe9'
  if((Get-FileHash -LiteralPath $MiniImage -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected){throw 'Unexpected mini image'}
  Copy-Item -LiteralPath $MiniImage -Destination "$mini/fpga_mini.bi3"
 } else {
  if(-not $QuartusBin){throw 'Supply QuartusBin to build mini, or a hash-verified MiniImage'}
  Push-Location $mini
  try {
   foreach($phase in @('map','fit','sta','asm')){
    & "$QuartusBin/quartus_$phase.exe" sd2snes_mini -c main
    if($LASTEXITCODE -ne 0){throw "Mini $phase failed"}
   }
   & "$work/utils/rle.exe" "$mini/output_files/main.rbf" "$mini/fpga_mini.bi3"
   if($LASTEXITCODE -ne 0){throw 'Mini compression failed'}
  } finally {Pop-Location}
 }
 Push-Location "$work/src"
 try {
  $buildArgs=@('-r','CONFIG=config-mk3-stm32','AWK=awk','BIN2C=../utils/bin2c.exe','OBJDIR=obj-nes-062','DEPDIR=.dep-nes-062','GBC_DIAG_CFLAGS=-DGBC_DIAGNOSTIC -DGBC_PROBE_G12 -DGBC_SAVE_G12 -DGBC_DUMP_G12','build')
  & $Make @buildArgs
  # Make 3.81 may stop after generating its first dependency on a clean tree.
  if($LASTEXITCODE -ne 0){& $Make @buildArgs}
  if($LASTEXITCODE -ne 0){throw 'Firmware build failed; inspect the complete log'}
 } finally {Pop-Location}
} finally {$env:PATH=$savedPath;& subst $Drive /D;& subst $ArmDrive /D}
$fw=Join-Path $root 'src/obj-nes-062/firmware.stm'
if(-not (Test-Path -LiteralPath $fw)){throw 'H1 firmware output missing'}
$elf=Join-Path $root 'src/obj-nes-062/sd2snes.elf'
$symbols=& (Join-Path $arm 'arm-none-eabi-nm.exe') -S $elf
if($LASTEXITCODE -ne 0 -or -not ($symbols -match '\bT nes_mcu_load_probe$')){throw 'Load-only062 entry was discarded or missing from final ELF'}
foreach($name in @('nes_rom_verify','nes_rom_verified_start','nes_menu_sd_probe','nes_menu_diagnostic_run','nes_menu_diagnostic_prepared','nes_menu_diagnostic_released')){if(-not ($symbols -match ('\bT '+$name+'$'))){throw '062 verification function discarded'}}
$mainDump=& (Join-Path $arm 'arm-none-eabi-objdump.exe') -d --disassemble=main $elf
if($LASTEXITCODE -ne 0){throw 'main disassembly failed'}
$runDump=& (Join-Path $arm 'arm-none-eabi-objdump.exe') -d --disassemble=nes_menu_diagnostic_run $elf
if($LASTEXITCODE -ne 0){throw 'menu run disassembly failed'}
$mainText=$mainDump -join "`n"
$runText=$runDump -join "`n"
if(([regex]::Matches($mainText,'\bbl\s+[^\r\n]*<nes_menu_diagnostic_run>')).Count -ne 3){throw 'Three manual menu call sites missing from final ELF'}
foreach($name in @('nes_menu_diagnostic_prepared','nes_menu_diagnostic_released')){
 if($mainText -notmatch ('\bbl\s+[^\r\n]*<'+$name+'>')){throw 'Menu restoration call site missing'}
}
if($runText -notmatch '\bbl\s+[^\r\n]*<nes_menu_sd_probe>'){throw 'Menu does not call actual candidate-aware SD probe'}
$mainDump | Set-Content -LiteralPath (Join-Path $root 'main-disassembly.txt') -Encoding utf8
$runDump | Set-Content -LiteralPath (Join-Path $root 'menu-run-disassembly.txt') -Encoding utf8
$symbols | Set-Content -LiteralPath (Join-Path $root 'symbols.txt') -Encoding utf8
$output=Join-Path $root 'firmware-nes-062-compile-only.stm'
Copy-Item -LiteralPath $fw -Destination $output
$hash=(Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Output "PASS: compile-only NES062 verification link (three called manual hooks; no installable hardware pair) $hash"
