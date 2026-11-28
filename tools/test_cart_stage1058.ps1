$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/..").Path
$out=(Resolve-Path "$root/../probes/nes-carts1058").Path
$base=(Resolve-Path "$out/../nes-carts1057").Path
$q='C:/altera_standard/25.1std/questa_fse/win64'
$job=New-Item -Type Directory -Path (Join-Path $env:TEMP ('cart1058-'+[guid]::NewGuid().ToString('N')))
Push-Location $job.FullName
try {
 Copy-Item "$base/rows.txt","$base/pattern-7.txt" .
 foreach ($version in 1057,1058) {
  $b=(Resolve-Path "$out/../nes-carts$version/board-21").Path
  # Keep HDL paths short and ASCII for the mixed language tools.
  foreach ($n in 'regs_savestates.sv','bus_savestates.vhd','ppu.sv') {Copy-Item "$b/rtl/$n" . -Force}
  Copy-Item "$b/nes_rom_service.sv","$b/cart_nrom.sv","$out/board-7/nes_chr_snapshot.sv","$root/tests/nes-functional/prerender1058_tb.sv","$root/tests/nes-functional/cart_stage1057_tb.sv","$root/tests/nes-functional/page_receipt1058_tb.sv" . -Force
  if($version -eq 1057){& "$q/vlib.exe" work}
  & "$q/vcom.exe" -2008 bus_savestates.vhd *> "$out/vcom-$version.log"
  if($LASTEXITCODE){throw 'vcom'}
  & "$q/vlog.exe" -sv regs_savestates.sv ppu.sv cart_nrom.sv nes_rom_service.sv nes_chr_snapshot.sv prerender1058_tb.sv cart_stage1057_tb.sv page_receipt1058_tb.sv *> "$out/vlog-$version.log"
  if($LASTEXITCODE){throw 'vlog'}
  $tests=if($version -eq 1057){'prerender1058_tb'}else{'prerender1058_tb','cart_stage1057_tb','page_receipt1058_tb'}
  foreach($tb in $tests){
   $extra=@();if($version -eq 1057){$extra=@('+OLD')}
   $log="$out/$version-$tb.log"
   & "$q/vsim.exe" -c -L altera_mf_ver -suppress 3009 $tb @extra -do 'onerror {quit -code 1}; run -all; quit -f' *> $log
   if($LASTEXITCODE -or !(Select-String -Quiet -LiteralPath $log -Pattern '^# PASS')){throw "failed $log"}
  }
 }
} finally {Pop-Location}
