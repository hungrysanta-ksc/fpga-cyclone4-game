$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$bin='C:/altera_standard/25.1std/questa_fse/win64'
foreach($edition in 900,901){
 $board=Join-Path ([IO.Path]::GetTempPath()) "nes-trial816-board$edition"
 $test=Join-Path ([IO.Path]::GetTempPath()) "nes-frame900-wire$edition"
 New-Item -ItemType Directory -Force -Path $test | Out-Null
 foreach($name in 'nes_sink_bridge165','nes_sink_bus165','nes_sink_spi165','nes_domain_reset124','nes_screen_status151','nes_frame900'){
  Copy-Item -LiteralPath "$board/$name.sv" -Destination $test
 }
 Copy-Item -LiteralPath "$board/sink-program.hex","$project/tests/nes-functional/tb_nes_frame900.sv" -Destination $test
 Push-Location $test
 try{
  if(!(Test-Path work)){& "$bin/vlib.exe" work;if($LASTEXITCODE){throw 'vlib'}}
  & "$bin/vlog.exe" -sv @(Get-ChildItem *.sv -Name) *> compile.log
  if($LASTEXITCODE){throw "compile $edition"}
  & "$bin/vsim.exe" -c tb_nes_frame900 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> wire.log
  if($LASTEXITCODE -or !(Select-String wire.log -Pattern 'PASS900 checked' -Quiet)){throw "wire $edition"}
 }finally{Pop-Location}
}
