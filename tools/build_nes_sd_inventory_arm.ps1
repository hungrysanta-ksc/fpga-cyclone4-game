param([Parameter(Mandatory=$true)][string]$SourceRoot,[Parameter(Mandatory=$true)][string]$ArmBin,[Parameter(Mandatory=$true)][string]$HostGcc,[Parameter(Mandatory=$true)][string]$Make,[Parameter(Mandatory=$true)][string]$UnixBin,[Parameter(Mandatory=$true)][string]$MiniImage)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath $SourceRoot).Path
$arm=(Resolve-Path -LiteralPath $ArmBin).Path
if((Test-Path W:/) -or (Test-Path V:/)){throw 'W: and V: must be unused'}
if((Get-FileHash -LiteralPath $MiniImage).Hash.ToLowerInvariant() -ne '9ae79c3028391063338d42ae16b19acf48d0d80858939b015ef6481f55cbefe9'){throw 'Unexpected mini image hash'}
$envSavedPath=$env:PATH
& subst W: $root
if($LASTEXITCODE -ne 0){throw 'Source mapping failed'}
$armMapped=$false
try{
 & subst V: (Split-Path $arm)
 if($LASTEXITCODE -ne 0){throw 'ARM mapping failed'}
 $armMapped=$true
 $env:PATH='V:/bin;'+$UnixBin+';'+(Split-Path $HostGcc)+';'+$envSavedPath
 & $HostGcc -Wall -Wstrict-prototypes -Werror W:/utils/bin2c.c -o W:/utils/bin2c.exe
 if($LASTEXITCODE -ne 0){throw 'bin2c failed'}
 & $HostGcc -Wall -Wstrict-prototypes -Werror W:/src/utils/genhdr.c -o W:/src/utils/genhdr.exe
 if($LASTEXITCODE -ne 0){throw 'genhdr failed'}
 Copy-Item -LiteralPath $MiniImage -Destination W:/verilog/sd2snes_mini/fpga_mini.bi3
 Push-Location W:/src
 try{
  $argsBuild=@('-r','CONFIG=config-mk3-stm32','AWK=awk','BIN2C=../utils/bin2c.exe','OBJDIR=obj-sdinfo072','DEPDIR=.dep-sdinfo072','GBC_DIAG_CFLAGS=-DGBC_DIAGNOSTIC -DGBC_PROBE_G12 -DGBC_SAVE_G12 -DGBC_DUMP_G12','build')
  & $Make @argsBuild > (Join-Path $root '../build01.log') 2>&1
  $first=$LASTEXITCODE
  if($first -ne 0){& $Make @argsBuild > (Join-Path $root '../build02.log') 2>&1}
  if($LASTEXITCODE -ne 0){throw 'Firmware build failed; raw build logs retained'}
 }finally{Pop-Location}
}finally{
 $env:PATH=$envSavedPath
 & subst W: /D
 if($armMapped){& subst V: /D}
}
Write-Output 'ARM firmware linked. No installation performed; no C44 timestamp normalization.'
