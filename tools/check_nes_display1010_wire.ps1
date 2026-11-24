$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$board=Join-Path ([IO.Path]::GetTempPath()) 'nes-display1010-boardD'
$test=Join-Path ([IO.Path]::GetTempPath()) 'nes-display1010-wire'
New-Item -ItemType Directory -Force $test | Out-Null
Copy-Item -LiteralPath "$project/../probes/nes-display1010/tb_nes_display1010.sv" -Destination $test
$bin='C:/altera_standard/25.1std/questa_fse/win64'
Push-Location $test
try{
 if(!(Test-Path work)){& "$bin/vlib.exe" work;if($LASTEXITCODE){throw 'vlib'}}
 $files=foreach($name in 'nes_sink_bridge165','nes_sink_bus165','nes_sink_spi165','nes_domain_reset124','nes_screen_status151','nes_display1010'){Join-Path $board "$name.sv"}
 Copy-Item -LiteralPath "$board/sink-program.hex" -Destination .
 & "$bin/vlog.exe" -sv @files tb_nes_display1010.sv *> compile1010.log
 if($LASTEXITCODE){throw 'vlog: inspect compile1010.log'}
 & "$bin/vsim.exe" -c tb_nes_display1010 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> wire1010.log
 if($LASTEXITCODE -or !(Select-String wire1010.log 'PASS1010 cold' -Quiet)){throw 'wire: inspect wire1010.log'}
}finally{Pop-Location}
