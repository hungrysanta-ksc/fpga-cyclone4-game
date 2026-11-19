param()
$ErrorActionPreference='Stop'
$testRoot=Join-Path ([System.IO.Path]::GetTempPath()) 'nes-frame862-wire'
$project=Split-Path $PSScriptRoot -Parent
$board=Join-Path ([System.IO.Path]::GetTempPath()) 'nes-trial816-board862'
$bin='C:/altera_standard/25.1std/questa_fse/win64'
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
Copy-Item -LiteralPath "$board/nes_screen_status151.sv","$board/nes_frame862.sv","$project/tests/nes-functional/tb_nes_frame862.sv" -Destination $testRoot
Push-Location $testRoot
try {
 if(!(Test-Path work)){& "$bin/vlib.exe" work; if($LASTEXITCODE){throw 'vlib'}}
 & "$bin/vlog.exe" -sv nes_screen_status151.sv nes_frame862.sv tb_nes_frame862.sv *> compile.log
 if($LASTEXITCODE){throw 'vlog'}
 & "$bin/vsim.exe" -c tb_nes_frame862 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> wire.log
 if($LASTEXITCODE -or !(Select-String wire.log -Pattern 'PASS862 wire' -Quiet)){throw 'wire bench'}
}finally{Pop-Location}
