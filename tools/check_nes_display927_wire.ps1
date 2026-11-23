$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$bin='C:/altera_standard/25.1std/questa_fse/win64'
$temp=[IO.Path]::GetTempPath()
$board=Join-Path $temp 'nes927-verified/nes-trial816-board927'
$test=Join-Path $temp 'nes-display927-wire'
New-Item -ItemType Directory -Force $test | Out-Null
foreach($name in 'nes_sink_bridge165','nes_sink_bus165','nes_sink_spi165','nes_domain_reset124','nes_screen_status151','nes_display927'){
 Copy-Item -LiteralPath "$board/$name.sv" -Destination $test
}
Copy-Item -LiteralPath "$board/sink-program.hex" -Destination $test
$s=Get-Content -Raw "$project/tests/nes-functional/tb_nes_frame900.sv"
$s=$s.Substring(0,$s.IndexOf(' initial begin')).Replace('monitor.trace.now','monitor.trace.timer[24:9]')
$s=$s.Replace(' nes_screen_status151 monitor(', " reg e9=0,writer=0;`n nes_screen_status151 monitor(.first905(e9),.writer903(writer),")
$needle="a='h7fe200;pa=4;"
$s=$s.Replace($needle, @'
   a='h7fe000;pa='h18;#150;pawr=0;rd=0;#200;rd=1;pawr=1;#160;exp_t[1]=monitor.trace.timer[24:9];#7200;
   a='h7fe100;pa='h22;#150;pawr=0;rd=0;#200;rd=1;pawr=1;#160;#7200;
   a='h7fe200;pa=4;
'@)
$s+=@'
 task stamp(input integer slot,input integer expected);
  reg [15:0] actual;
  actual={snapshot[9+2*slot],snapshot[8+2*slot]};
  if(((expected-actual)&16'hffff)>1 || ^actual===1'bx)$fatal(1,"stamp %d expected %d actual %d",slot,expected,actual);
 endtask
 initial begin
  #130;reset=0;active=1;#1000;
  packet(904,1,0,0);packet(904,3,0,0);exp_t[6]=exp_t[4];
  packet(905,1,0,0);
  e9=1;#48;e9=0;#6800;writer=1;#120;exp_t[8]=monitor.trace.timer[24:9];
  a='h7f7000;pa='h19;#150;pawr=0;rd=0;#200;rd=1;pawr=1;#160;exp_t[7]=monitor.trace.timer[24:9];
  packet(905,3,0,0);query();
  if(fault || {snapshot[1],snapshot[3],snapshot[2],snapshot[4]}!==32'h9703897f ||
     snapshot[5]!==8'h1c || ((exp_t[6]-{snapshot[7],snapshot[6]})&16'hffff)>1)$fatal(1,"wire header flags=%x ports=%x",snapshot[4],snapshot[5]);
  stamp(0,exp_t[8]);stamp(1,exp_t[2]);stamp(2,exp_t[1]);stamp(3,exp_t[3]);
  stamp(4,exp_t[4]);stamp(5,exp_t[5]);stamp(6,exp_t[9]);stamp(7,exp_t[7]);
  begin integer fd;fd=$fopen("reply927.hex","w");$fdisplay(fd,"00");
   for(integer k=1;k<24;k++)$fdisplay(fd,"%02x",snapshot[k]);$fclose(fd);end
  packet(906,1,0,0);packet(906,3,0,1);query();
  if(!fault || snapshot[4][6])$fatal(1,"invalid receipt accepted");
  active=0;#400;query();if(snapshot[4]!==0)$fatal(1,"STOP did not clear receipt");
  $display("PASS927 wire generation, tile, SEAL, first and last DMA ports, previous reveal, ACK, bad identity and STOP");$finish;
 end
endmodule
'@
$s|Set-Content "$test/tb_nes_frame900.sv"
Push-Location $test
try {
 if(!(Test-Path work)){& "$bin/vlib.exe" work;if($LASTEXITCODE){throw 'vlib'}}
 & "$bin/vlog.exe" -sv @(Get-ChildItem *.sv -Name) *> compile.log
 if($LASTEXITCODE){throw 'compile'}
 & "$bin/vsim.exe" -c tb_nes_frame900 -do 'onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0' *> wire.log
 if($LASTEXITCODE -or !(Select-String wire.log -Pattern 'PASS927 wire' -Quiet)){throw 'wire 927'}
} finally {Pop-Location}
