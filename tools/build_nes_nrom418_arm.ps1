param([ValidatePattern('^[a-z0-9-]+$')][string]$Run='arm01',[ValidatePattern('^nrom[0-9]+$')][string]$TrialLabel='nrom471',[string]$Patch471='',[string]$Patch474='')
$ErrorActionPreference='Stop'
$root='C:/Users/mohallo/Documents/ChatGPT/sd2snes 에서 게임보이컬러 전용 게임 구동하기'
$source=Join-Path $root 'probes/nes-repeat227/arm01'
$candidate=Join-Path $root 'probes/nes-nrom407/build04'
$out=Join-Path $env:TEMP ('nes-nrom418-'+$Run)
$archive=Join-Path $root ('probes/nes-nrom418/'+$Run)
if(Test-Path -LiteralPath $archive){throw 'expected fresh archive'}
if(Test-Path -LiteralPath $out){throw 'expected fresh ARM output'}
if((Test-Path 'W:/') -or (Test-Path 'V:/')){throw 'build drive already in use'}
New-Item -ItemType Directory -Path $out | Out-Null
Copy-Item -LiteralPath (Join-Path $source 'src'),(Join-Path $source 'utils') -Destination $out -Recurse
New-Item -ItemType Directory -Path (Join-Path $out 'verilog/sd2snes_mini') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $source 'verilog/sd2snes_mini/fpga_mini.bi3') -Destination (Join-Path $out 'verilog/sd2snes_mini/fpga_mini.bi3')
foreach($file in @('Makefile','nes_h1_stm32.c','nes_rom_verify.c','nes_run136.inc','nes_nrom406.c','nes_nrom406.h')){
 Copy-Item -LiteralPath (Join-Path $candidate $file) -Destination (Join-Path $out "src/$file") -Force
}
Copy-Item -LiteralPath (Join-Path $root 'probes/nes-nrom418/menu01/nes_menu_diagnostic.c') -Destination (Join-Path $out 'src/nes_menu_diagnostic.c') -Force
& (Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe') (Join-Path $PSScriptRoot 'label_nes_nrom_trial.py') --directory (Join-Path $out 'src') --label $TrialLabel
if($LASTEXITCODE){throw 'trial identity generation failed'}
if($Patch471 -and $Patch474){throw 'select only one native patch'}
if($Patch471 -or $Patch474){
 $nativePatchDir=if($Patch474){$Patch474}else{$Patch471}
 $nativePatchNames=@('nes_native165.c','nes_native_runtime165.c','nes_runtime_board165.inc','nes_game149_spi.inc','nes_native165_bulk.inc','nes_budget210.c','nes_cost471.h','nes_cost471.c')
 if($Patch474){$nativePatchNames+=@('nes_planner211.c','nes_sink_window184.c','nes_sink_window184.h')}
 foreach($name in $nativePatchNames){Copy-Item -LiteralPath (Join-Path $nativePatchDir $name) -Destination (Join-Path $out ('src/'+$name)) -Force}
 $mk=Join-Path $out 'src/Makefile'
 $mktext=[IO.File]::ReadAllText($mk)
 if(-not $mktext.Contains('SRC += nes_nrom406.c')){throw 'NROM SRC insertion point missing'}
 [IO.File]::WriteAllText($mk,$mktext.Replace('SRC += nes_nrom406.c','SRC += nes_cost471.c nes_nrom406.c'))
 $menu=Join-Path $out 'src/nes_menu_diagnostic.c'
 $s=[IO.File]::ReadAllText($menu).Replace('/sd2snes/nes/nrom16.nes',('/sd2snes/nes/'+$TrialLabel+'.nes')).Replace('/sd2snes/fpga_nrom16.bi3',('/sd2snes/fpga_'+$TrialLabel+'.bi3')).Replace('char text[4096]','char text[6144]')
 [IO.File]::WriteAllText($menu,$s)
}
$arm=Join-Path $root '.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi'
$savedPath=$env:PATH
$mountedWork=$false
$mountedArm=$false
try {
 & subst W: $out
 if($LASTEXITCODE -ne 0){throw 'workspace subst failed'}
 $mountedWork=$true
 & subst V: $arm
 if($LASTEXITCODE -ne 0){throw 'toolchain subst failed'}
 $mountedArm=$true
 $env:PATH='V:/bin;C:/Program Files/Git/usr/bin;C:/altera_lite/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin;'+$savedPath
 Set-Location 'W:/src'
 $make='C:/altera_lite/25.1std/nios2eds/bin/gnu/H-x86_64-mingw32/bin/make.exe'
 $args=@('-r','CONFIG=config-mk3-stm32','AWK=awk','BIN2C=../utils/bin2c.exe','OBJDIR=obj-nes-100','DEPDIR=.dep-nes-100','GBC_DIAG_CFLAGS=-DGBC_DIAGNOSTIC -DGBC_PROBE_G12 -DGBC_SAVE_G12 -DGBC_DUMP_G12','build')
 & $make @args *> (Join-Path $out 'build.log')
 if($LASTEXITCODE -ne 0){throw 'ARM build failed, see build.log'}
 & 'V:/bin/arm-none-eabi-size.exe' 'obj-nes-100/sd2snes.elf' *> (Join-Path $out 'size.log')
 if($LASTEXITCODE -ne 0){throw 'size failed'}
 & 'V:/bin/arm-none-eabi-nm.exe' 'obj-nes-100/sd2snes.elf' *> (Join-Path $out 'symbols.log')
 if($LASTEXITCODE -ne 0){throw 'symbols failed'}
} finally {
 Set-Location -LiteralPath $root
 $env:PATH=$savedPath
 if($mountedWork){& subst W: /D | Out-Null}
 if($mountedArm){& subst V: /D | Out-Null}
 Copy-Item -LiteralPath $out -Destination $archive -Recurse
}
