$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/..").Path
$out=[IO.Directory]::CreateDirectory("$root/../probes/nes-ff3-display1037").FullName
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$work=New-Item -Type Directory -Path (Join-Path $env:TEMP ('ff3-display-'+[guid]::NewGuid().ToString('N')))
$src=Join-Path $work.FullName 'board'
$py="$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
& $py "$root/tools/prepare_ff3_display1037.py" $src
if($LASTEXITCODE){throw 'board preparation failed'}
& $py "$root/tools/ff3_chr_fixture1037.py" $work.FullName
if($LASTEXITCODE){throw 'FF3 CHR reference failed'}
$baseline=Join-Path $root '../probes/nes-kirby1035/board-times/nes_native_compact181.sv'
[IO.File]::WriteAllText("$work/compact_reference.sv",([IO.File]::ReadAllText($baseline)).Replace('module nes_native_compact181(', 'module nes_compact_reference('))
foreach($version in 'original','changed'){
 $apu=if($version -eq 'original'){Join-Path $root '../probes/nes-kirby1035/board-times/rtl/apu.sv'}else{"$src/rtl/apu.sv"}
 $mixer=[regex]::Match([IO.File]::ReadAllText($apu),'(?s)module APUMixer \(.*?endmodule').Value
 if(!$mixer){throw 'APU mixer module missing'}
 if($version -eq 'original'){$mixer=$mixer.Replace('module APUMixer (','module APUMixer_reference (')}
 [IO.File]::WriteAllText("$work/mixer-$version.sv",$mixer)
}
Push-Location $work
try {
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib failed'}
 & "$bin/vcom.exe" -2008 "$src/rtl/bus_savestates.vhd" "$src/rtl/savestates.vhd" *> "$out/palette-vcom.log"
 if($LASTEXITCODE){throw 'palette reference VHDL failed'}
 foreach($version in 'original','changed'){
  $ppu=if($version -eq 'original'){Join-Path $root '../probes/nes-kirby1035/board-times/rtl/ppu.sv'}else{"$src/rtl/ppu.sv"}
  $palette=[regex]::Match([IO.File]::ReadAllText($ppu),'(?s)module PaletteRam\s*\(.*?endmodule').Value
  if(!$palette){throw 'palette module missing'}
  if($version -eq 'original'){$palette=$palette.Replace('module PaletteRam','module PaletteRam_reference')}
  [IO.File]::WriteAllText("$work/palette-$version.sv","import regs_savestates::*;`n"+$palette)
 }
 $referenceDir=[IO.Directory]::CreateDirectory("$work/reference/rtl")
 Copy-Item (Join-Path $root '../probes/nes-kirby1035/board-times/rtl/ppu.sv') $referenceDir.FullName
 & $py -c "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from prepare_ff3_oam1037 import share_oam;share_oam(Path('reference'),compact=False)" "$root/tools"
 if($LASTEXITCODE){throw '1041 reference generation failed'}
 $oamOriginal=[IO.File]::ReadAllText("$referenceDir/ppu.sv")
 $oamChanged=[IO.File]::ReadAllText("$src/rtl/ppu.sv")
 foreach($pair in @(@('reference',$oamOriginal),@('changed',$oamChanged))){
  $body=[regex]::Match($pair[1],'(?s)module OAMEval\s*\(.*?endmodule').Value
  if(!$body){throw 'OAM module missing'}
  if($pair[0] -eq 'reference'){$body=$body.Replace('module OAMEval(', 'module oam_reference(')}
  [IO.File]::WriteAllText("$work/oam-$($pair[0]).sv","import regs_savestates::*;`n"+$body)
 }
 & "$bin/vlog.exe" -sv "$src/rtl/regs_savestates.sv" "$work/oam-reference.sv" "$work/oam-changed.sv" "$root/tests/nes-functional/ff3_oam1042_tb.sv" *> "$out/oam-vlog.log"
 if($LASTEXITCODE){throw 'OAM compile failed'}
 & "$bin/vsim.exe" -c -L altera_mf_ver ff3_oam1042_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/oam-sim.log"
 if($LASTEXITCODE -or !(Select-String -Path "$out/oam-sim.log" -SimpleMatch 'PASS FF3 OAM')){throw 'OAM comparison failed'}
 & "$bin/vlog.exe" -sv "$src/rtl/regs_savestates.sv" "$work/palette-original.sv" "$work/palette-changed.sv" "$root/tests/nes-functional/ff3_palette1039_tb.sv" *> "$out/palette-vlog.log"
 if($LASTEXITCODE){throw 'palette comparator failed to compile'}
 & "$bin/vsim.exe" -c ff3_palette1039_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/palette-sim.log"
 if($LASTEXITCODE -or !(Select-String -Path "$out/palette-sim.log" -SimpleMatch 'PASS FF3 palette')){throw 'palette comparison failed'}
 & "$bin/vlog.exe" -sv "$work/mixer-original.sv" "$work/mixer-changed.sv" "$root/tests/nes-functional/ff3_mixrom_tb.sv" "$work/compact_reference.sv" "$src/nes_native_compact181.sv" "$root/tests/nes-functional/ff3_map_history_tb.sv" "$src/nes_run_observer134.sv" "$root/src/nes/nes_checkpoint_spi.sv" "$root/tests/nes-functional/ff3_spi_tb.sv" "$src/nes_chr_snapshot.sv" "$src/nes_tile205.sv" "$src/nes_source_tile192.sv" "$root/tests/nes-functional/ff3_display_tb.sv" *> "$out/display-vlog.log"
 if($LASTEXITCODE){throw 'vlog failed'}
 & "$bin/vsim.exe" -c ff3_mixrom_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/mixrom-sim.log"
 if($LASTEXITCODE -or !(Select-String -Path "$out/mixrom-sim.log" -SimpleMatch 'PASS FF3 mixer')){throw 'mixer mismatch'}
 & "$bin/vsim.exe" -c ff3_map_history_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/capture-map-sim.log"
 if($LASTEXITCODE -or !(Select-String -Path "$out/capture-map-sim.log" -SimpleMatch 'PASS FF3 capture')){throw 'capture map comparison failed'}
 & "$bin/vsim.exe" -c ff3_display_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/display-sim.log"
 if($LASTEXITCODE -or !(Select-String -Path "$out/display-sim.log" -SimpleMatch 'PASS FF3 8192B')){throw 'display simulation failed'}
 & "$bin/vsim.exe" -c ff3_spi_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/state-spi-sim.log"
 if($LASTEXITCODE -or !(Select-String -Path "$out/state-spi-sim.log" -SimpleMatch 'PASS FF3 state SPI')){throw 'state SPI simulation failed'}
 & "$bin/vsim.exe" -c -gLINK=1 ff3_spi_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/state-link-sim.log"
 if($LASTEXITCODE -or !(Select-String -Path "$out/state-link-sim.log" -SimpleMatch 'PASS linked FF3')){throw 'SPI to checkpoint walker failed'}
 & "$bin/vsim.exe" -c -gBOOT=1 ff3_spi_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/boot-sram.log"
 if($LASTEXITCODE -or !(Select-String -Path "$out/boot-sram.log" -SimpleMatch 'PASS FF3 boot SRAM')){throw 'boot battery simulation failed'}
}finally{Pop-Location}
