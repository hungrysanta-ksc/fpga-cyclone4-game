param([Parameter(Mandatory=$true)][string]$SourceRoot)
$ErrorActionPreference='Stop'
$workspace=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$build=(Resolve-Path -LiteralPath $SourceRoot).Path
$arm=Join-Path $workspace '.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi'
if((Test-Path 'W:/') -or (Test-Path 'V:/')){throw 'Build drive already in use'}
$savedPath=$env:PATH
$mountedWork=$false;$mountedArm=$false
try {
 & subst W: $build
 if($LASTEXITCODE){throw 'Build drive mapping failed'};$mountedWork=$true
 & subst V: $arm
 if($LASTEXITCODE){throw 'Toolchain mapping failed'};$mountedArm=$true
 $env:PATH='V:/bin;C:/Program Files/Git/usr/bin;C:/altera_lite/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin;'+$savedPath
 Push-Location 'W:/src'
 try {
  $make='C:/altera_lite/25.1std/nios2eds/bin/gnu/H-x86_64-mingw32/bin/make.exe'
  & $make -r 'CONFIG=config-mk3-stm32' 'AWK=awk' 'BIN2C=../utils/bin2c.exe' 'OBJDIR=obj-nes-100' 'DEPDIR=.dep-nes-100' 'obj-nes-100/autoconf.h' 'obj-nes-100/cfgware.h' 'obj-nes-100/version.h' *> (Join-Path $build 'bootstrap.log')
  if($LASTEXITCODE){throw 'ARM header bootstrap failed; inspect bootstrap.log'}
  & $make -r 'CONFIG=config-mk3-stm32' 'AWK=awk' 'BIN2C=../utils/bin2c.exe' 'OBJDIR=obj-nes-100' 'DEPDIR=.dep-nes-100' 'GBC_DIAG_CFLAGS=-DGBC_DIAGNOSTIC -DGBC_PROBE_G12 -DGBC_SAVE_G12 -DGBC_DUMP_G12' build *> (Join-Path $build 'build.log')
  if($LASTEXITCODE){throw 'ARM build failed; inspect build.log'}
  & 'V:/bin/arm-none-eabi-size.exe' 'obj-nes-100/sd2snes.elf' *> (Join-Path $build 'size.log')
  if($LASTEXITCODE){throw 'size failed'}
 } finally {Pop-Location}
} finally {
 $env:PATH=$savedPath
 if($mountedWork){& subst W: /D |Out-Null}
 if($mountedArm){& subst V: /D |Out-Null}
}
