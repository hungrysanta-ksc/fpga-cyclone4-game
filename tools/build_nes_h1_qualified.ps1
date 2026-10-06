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
  $buildArgs=@('-r','CONFIG=config-mk3-stm32','AWK=awk','BIN2C=../utils/bin2c.exe','OBJDIR=obj-h1-043','DEPDIR=.dep-h1-043','GBC_DIAG_CFLAGS=-DGBC_DIAGNOSTIC -DGBC_PROBE_G12 -DGBC_SAVE_G12 -DGBC_DUMP_G12','build')
  & $Make @buildArgs
  # Make 3.81 may stop after generating its first dependency on a clean tree.
  if($LASTEXITCODE -ne 0){& $Make @buildArgs}
  if($LASTEXITCODE -ne 0){throw 'Firmware build failed; inspect the complete log'}
 } finally {Pop-Location}
} finally {$env:PATH=$savedPath;& subst $Drive /D;& subst $ArmDrive /D}
$fw=Join-Path $root 'src/obj-h1-043/firmware.stm'
if(-not (Test-Path -LiteralPath $fw)){throw 'H1 firmware output missing'}
$output=Join-Path $root 'firmware-h1-043.stm'
Copy-Item -LiteralPath $fw -Destination $output
$hash=(Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Output "PASS: experimental H1 firmware $hash"
