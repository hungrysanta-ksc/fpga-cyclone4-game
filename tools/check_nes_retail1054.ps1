$ErrorActionPreference='Stop'
$work=(Resolve-Path "$PSScriptRoot/../../probes/nes-pair1054").Path
$bin='C:/altera_standard/25.1std/questa_fse/win64'
foreach($kind in 'rom','ram'){
 $src="$work/board-$kind-retail"
 $out=New-Item -ItemType Directory -Path "$work/sim-$kind" -Force
 $scratch=New-Item -ItemType Directory -Path (Join-Path $env:TEMP ("nes1054-"+[guid]::NewGuid().ToString("N")))
 Push-Location $scratch
 try{
  & "$bin/vlib.exe" work
  & "$bin/vlog.exe" -sv "$src/nes_rom_loader.sv" "$src/nes_rom_spi.sv" "$PSScriptRoot/../tests/nes-functional/nes_retail1054_tb.sv" *> "$out/vlog.log"
  if($LASTEXITCODE){throw 'vlog'}
  $n=if($kind -eq 'rom'){786432}else{524288}
  & "$bin/vsim.exe" -c "-gTOTAL=$n" nes_retail1054_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> "$out/result.log"
  if($LASTEXITCODE -or !(Select-String -LiteralPath "$out/result.log" -SimpleMatch 'PASS1054')){throw "test failed $kind"}
 }finally{Pop-Location}
}
