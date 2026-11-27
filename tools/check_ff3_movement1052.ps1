param([string]$Work=(Join-Path $PSScriptRoot '../../probes/nes-ff3-movement1052'))
$ErrorActionPreference='Stop'
$board=(Resolve-Path "$Work/board-c").Path
$out=(Resolve-Path $Work).Path
$tb=(Resolve-Path "$PSScriptRoot/../tests/nes-functional/ff3_movement1052_tb.sv").Path
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$scratch=New-Item -Type Directory -Path (Join-Path $env:TEMP ('ff3-motion-'+[guid]::NewGuid().ToString('N')))
Push-Location $scratch.FullName
try {
 & "$bin/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib'}
 & "$bin/vlog.exe" -sv "$board/nes_display1010.sv" $tb
 if($LASTEXITCODE){throw 'vlog'}
 & "$bin/vsim.exe" -c ff3_movement1052_tb -do 'onerror {quit -code 1};run -all;quit -f' *> "$out/trace.log"
 if($LASTEXITCODE -or !(Select-String -LiteralPath "$out/trace.log" -SimpleMatch 'PASS1052')){throw 'trace test'}
}finally{Pop-Location}
& "$PSScriptRoot/check_ff3_chr1051.ps1" -Board $board -Report $out
