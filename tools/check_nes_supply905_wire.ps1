$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$temp=[IO.Path]::GetTempPath()
$board=Join-Path $temp 'nes-trial816-board905'
$test=Join-Path $temp 'nes-supply905-wire'
New-Item -ItemType Directory -Force $test | Out-Null
foreach($name in 'nes_sink_bridge165','nes_sink_bus165','nes_sink_spi165','nes_domain_reset124','nes_screen_status151','nes_supply905','nes_bulk_aperture188','nes_plan_spi200','nes_native_arbiter165'){
 Copy-Item "$board/$name.sv" -Destination $test
}
Copy-Item "$board/sink-program.hex" -Destination $test
$s=Get-Content -Raw "$root/tests/nes-functional/tb_nes_frame900.sv"
$s=$s.Substring(0,$s.IndexOf(' initial begin')).Replace('tb_nes_frame900','tb_supply905')
$s=$s.Replace(' nes_screen_status151 monitor(', ' nes_screen_status151 monitor(.writer903(wptr),.reader903(rptr),.ready903(ready),.snap903(1''b0),.ret905(take905&&ready&&taken==head_token),.units905(length[11:4]),.first905(first905),.evt905(ev),.kind903(!head_token[0]),.token903(taken),')
$s=$s.Replace('r[k]=miso','r[k]=sel ? miso : pmiso')
$cases=Get-Content -Raw "$root/tests/nes-functional/supply905_cases.svh"
# Declare ports before the monitor to prevent implicit one-bit declarations.
$i=$cases.IndexOf(' nes_bulk_aperture188')
$s=$s.Replace(' nes_screen_status151 monitor(',($cases.Substring(0,$i)+"`n nes_screen_status151 monitor("))
($s+$cases.Substring($i)+"`nendmodule")|Set-Content "$test/tb_supply905.sv"
Push-Location $test
try{
 if(!(Test-Path work)){& "$bin/vlib.exe" work;if($LASTEXITCODE){throw 'vlib'}}
 & "$bin/vlog.exe" -sv @(Get-ChildItem *.sv -Name) *> compile.log
 if($LASTEXITCODE){throw 'compile'}
 & "$bin/vsim.exe" -c tb_supply905 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> wire.log
 if($LASTEXITCODE -or !(Select-String wire.log -Pattern 'PASS905 first' -Quiet)){throw 'wire 905'}
}finally{Pop-Location}
