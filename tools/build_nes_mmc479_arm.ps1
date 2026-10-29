param([Parameter(Mandatory=$true)][string]$Base,[Parameter(Mandatory=$true)][string]$Patch,[Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $Out){throw 'fresh output required'}
if((Test-Path 'W:/') -or (Test-Path 'V:/')){throw 'build drives already occupied'}
$taskRoot=Split-Path -Parent $PSScriptRoot
$workspace=Split-Path -Parent $taskRoot
$python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $python -c 'import pathlib,shutil,sys; b,p,o=map(pathlib.Path,sys.argv[1:]);o.mkdir();shutil.copytree(b/"src",o/"src",ignore=shutil.ignore_patterns("obj-*",".dep-*"));shutil.copytree(b/"utils",o/"utils");shutil.copytree(b/"verilog",o/"verilog");[(shutil.copyfile(n,o/"src"/n.name)) for n in p.iterdir() if n.is_file()]' $Base $Patch $Out
if($LASTEXITCODE){throw 'materialization failed'}
$arm=Join-Path $workspace '.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi'
$savedPath=$env:PATH
$savedCwd=Get-Location
$mountedWork=$false
$mountedArm=$false
try {
 & subst W: $Out
 if($LASTEXITCODE){throw 'workspace subst failed'}
 $mountedWork=$true
 & subst V: $arm
 if($LASTEXITCODE){throw 'toolchain subst failed'}
 $mountedArm=$true
 $env:PATH='V:/bin;C:/Program Files/Git/usr/bin;C:/altera_lite/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin;'+$savedPath
 Set-Location 'W:/src'
 # Bootstrap generated order-only prerequisites before the old Windows make
 # searches its implicit C rules. A completely fresh OBJDIR otherwise fails
 # the first search for cdcuser.o even though its source exists.
 & 'C:/altera_lite/25.1std/nios2eds/bin/gnu/H-x86_64-mingw32/bin/make.exe' -r CONFIG=config-mk3-stm32 AWK=awk BIN2C=../utils/bin2c.exe OBJDIR=obj-nes-100 DEPDIR=.dep-nes-100 'GBC_DIAG_CFLAGS=-DGBC_DIAGNOSTIC -DGBC_PROBE_G12 -DGBC_SAVE_G12 -DGBC_DUMP_G12' obj-nes-100/autoconf.h obj-nes-100/cfgware.h obj-nes-100/version.h *> (Join-Path $Out 'bootstrap.log')
 if($LASTEXITCODE){throw 'generated header bootstrap failed'}
 & 'C:/altera_lite/25.1std/nios2eds/bin/gnu/H-x86_64-mingw32/bin/make.exe' -r CONFIG=config-mk3-stm32 AWK=awk BIN2C=../utils/bin2c.exe OBJDIR=obj-nes-100 DEPDIR=.dep-nes-100 'GBC_DIAG_CFLAGS=-DGBC_DIAGNOSTIC -DGBC_PROBE_G12 -DGBC_SAVE_G12 -DGBC_DUMP_G12' build *> (Join-Path $Out 'build.log')
 if($LASTEXITCODE){throw 'ARM build failed; inspect raw build.log'}
 & 'V:/bin/arm-none-eabi-size.exe' 'obj-nes-100/sd2snes.elf' *> (Join-Path $Out 'size.log')
 if($LASTEXITCODE){throw 'size failed'}
} finally {
 Set-Location -LiteralPath $savedCwd
 $env:PATH=$savedPath
 if($mountedWork){& subst W: /D | Out-Null}
 if($mountedArm){& subst V: /D | Out-Null}
}
