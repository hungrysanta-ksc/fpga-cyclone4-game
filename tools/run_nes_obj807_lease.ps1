$ErrorActionPreference='Stop'
$board=Join-Path $env:LOCALAPPDATA 'Temp/nes-fortress804-board'
$job=Join-Path $env:TEMP ('nes-obj807-'+[guid]::NewGuid().ToString('N'))
$bin='C:/altera_standard/25.1std/questa_fse/win64'
New-Item -ItemType Directory -Path $job | Out-Null
foreach($name in 'nes_native_export203.sv','nes_capture_lease201.sv'){
 Copy-Item -LiteralPath (Join-Path $board $name) -Destination $job
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'nes_obj807_lease_tb.sv') -Destination $job
Push-Location $job
try{
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib failed'}
 & "$bin/vlog.exe" nes_native_export203.sv nes_capture_lease201.sv nes_obj807_lease_tb.sv
 if($LASTEXITCODE){throw 'vlog failed'}
 & "$bin/vsim.exe" -batch -do 'run -all; quit -f' work.nes_obj807_lease_tb -l sim.log
 if($LASTEXITCODE -or !(Select-String -LiteralPath sim.log -SimpleMatch 'OBJ807_EXPORT_LEASE_PASS')){throw "Lease regression failed in $job"}
}finally{Pop-Location}
