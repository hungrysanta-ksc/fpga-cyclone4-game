$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/..").Path
$out=(Resolve-Path "$root/../probes/nes-carts1056").Path
$q='C:/altera_standard/25.1std/questa_fse/win64'
foreach($m in 3,7,21,5){
 $d=Join-Path $out "sim-$m"
 [void][IO.Directory]::CreateDirectory($d)
 $job=Join-Path $env:TEMP ('cart-sim-'+[guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($job)
 Copy-Item -LiteralPath "$out/mapper-$m.hex" -Destination "$job/bus.hex"
 Copy-Item -LiteralPath "$out/board-$m/cart_nrom.sv" -Destination $job
 Copy-Item -LiteralPath "$root/tests/nes-functional/cart1056_tb.sv" -Destination $job
 Push-Location -LiteralPath $job
 try {
  if(!(Test-Path work)){& "$q/vlib.exe" work}
  & "$q/vlog.exe" -sv cart_nrom.sv cart1056_tb.sv *> vlog.log
  if($LASTEXITCODE){throw "mapper $m compile"}
  & "$q/vsim.exe" -c "-gMAPPER=$m" cart1056_tb +trace=bus.hex -do 'onerror {quit -code 1}; run -all; quit -f' *> result.log
  if($LASTEXITCODE -or !(Select-String -Quiet -LiteralPath result.log -Pattern "^# PASS mapper=$m ")){throw "mapper $m trace"}
 } finally {Get-ChildItem -Filter '*.log' | Copy-Item -Destination $d;Pop-Location}
}
