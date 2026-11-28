param([string]$Work=(Join-Path $PSScriptRoot '../../probes/nes-dq4-movement1061'))
$ErrorActionPreference='Stop'
$out=(Resolve-Path $Work).Path
$q='C:/altera_standard/25.1std/questa_fse/win64'
$base=Get-Content -Raw "$out/../nes-carts1059/board-7/nes_chr_snapshot.sv"
$source=Get-Content -Raw "$PSScriptRoot/../tests/nes-functional/page_receipt1058_tb.sv"
$source=$source.Replace('wire fine,conflict,ready;', 'wire fine,conflict,ready;reg [7:0] live[0:8191], mirror[0:8191];')
$monitor='
 integer i,j,copies=0;
 initial for(i=0;i<8192;i=i+1)live[i]=i^(i>>5);
 always @(negedge clk) if(!s.we_n)begin
   mirror[s.ram_addr[12:0]]=s.write_data;copies=copies+1;
 end
 task verify;begin
   for(j=0;j<8192;j=j+1)if(mirror[j]!==live[j])$fatal(1,"mismatch %d",j);
 end endtask
 task tick;'
$tb=$source.Replace('task tick;', $monitor).Replace(".scan_data(8'hc3)",'.scan_data(live[s.scan_addr])')
$tb=$tb.Replace('group_id=group_addr;', 'live[{group_addr,7''h57}]=~live[{group_addr,7''h57}];group_id=group_addr;')
$tb=$tb.Replace('if(mask!==0)', 'verify();if(mask!==0)').Replace('put(47);','copies=0;put(47);')
$tb=$tb.Replace('if(fine || mask','verify();$display("COPIED %0d",copies);if(fine || mask')
$scratch=New-Item -ItemType Directory -Path (Join-Path $env:TEMP ('battle-mirror-'+[guid]::NewGuid().ToString('N')))
Push-Location $scratch.FullName
try {
 & "$q/vlib.exe" work
 if($LASTEXITCODE){throw 'vlib'}
 Set-Content tb.sv $tb
 foreach($block in 512,128){
   $sv=$base
   if($block -eq 128){
     $sv=$sv.Replace('reg [15:0] dirty','reg [63:0] dirty').Replace('p<16','p<64').Replace('changed_group[5:2]==p','changed_group==p').Replace('scan_addr[12:9]','scan_addr[12:7]').Replace('&scan_addr[8:0]','&scan_addr[6:0]')
   }
   Set-Content mirror.sv $sv
   & "$q/vlog.exe" -sv mirror.sv tb.sv *> "$out/battle-$block-compile.log"
   if($LASTEXITCODE){throw 'vlog'}
   & "$q/vsim.exe" -c -suppress 3009 page_receipt1058_tb -do 'onerror {quit -code 1};run -all;quit -f' *> "$out/battle-$block.log"
   $expected=if($block -eq 512){1536}else{640}
   if($LASTEXITCODE -or !(Select-String "$out/battle-$block.log" -Quiet -Pattern "^# COPIED $expected$") -or !(Select-String "$out/battle-$block.log" -Quiet -Pattern '^# PASS_PAGE')){throw "mirror $block"}
 }
}finally{Pop-Location}
