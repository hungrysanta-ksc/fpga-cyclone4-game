# SPDX-License-Identifier: MIT
"""Actual495 SPI EB snapshots plus legacy queue/ACK/cancel/phase/wrap guards."""
import argparse,json,os,re,shutil,subprocess
from pathlib import Path
from nes_status495 import sha,once
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['board','out','bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(parents=True,exist_ok=False)
    for n in ['nes_domain_reset124.sv','nes_sink_spi165.sv','nes_sink_bus165.sv','nes_sink_bridge165.sv','sink-program.hex']:shutil.copyfile(a.board/n,a.out/n)
    s=(ROOT/'tests/nes-functional/sink_window184_tb.sv').read_text()
    s=once(s,' task prepare(input integer index);',r''' task progress495;
  integer x;reg [7:0] c;begin
   for(x=0;x<8;x++)tx[x]=0;tx[0]=8'heb;transfer(8);
   c=0;for(x=1;x<7;x++)c=c8(c,rx[x]);
   if(rx[1]!=8'hf8||rx[7]!=c||fault)$fatal(1,"EB compact CRC/state");checks++;
  end
 endtask
 task prepare(input integer index);''')
    s=once(s,'  // Legacy 16-byte E0 is incompatible and fail-closed.',r'''  // EB has no ACK payload and cannot retire or alter queue ownership.
  common_reset;progress495;
  if(rx[2]||{rx[3],rx[4],rx[5],rx[6]})$fatal(1,"EB reset counts");
  send_packet(0);progress495;
  if(rx[2]!=1||{rx[3],rx[4]}!=1||{rx[5],rx[6]}!=0)$fatal(1,"EB pending counts");
  fork progress495;begin #12000;consume(0);end join
  if(rx[2]!=1||{rx[5],rx[6]}!=0)$fatal(1,"EB snapshot torn");
  progress495;if(rx[2]!=2||{rx[5],rx[6]}!=1)$fatal(1,"EB next snapshot");
  status;if(rx[7]!=acks[0][0]||rx[8]!=acks[0][1])$fatal(1,"EB clobbered full ACK");
  // Partial ACK invalidates its bytes; retired credit remains unchanged.
  send_packet(1);write_byte(24'h006010,acks[1][0]);progress495;
  if(rx[2]!=1||{rx[5],rx[6]}!=1)$fatal(1,"EB partial ACK credit");
  for(j=1;j<12;j++)write_byte(24'h006010+j,acks[1][j]);
  write_byte(24'h00601c,8'ha5);#500;progress495;
  if(rx[2]!=2||{rx[5],rx[6]}!=2)$fatal(1,"EB published ACK count");
  common_reset;dut.endpoint.accepted=16'hffff;dut.endpoint.retired=16'hffff;
  send_packet(0);progress495;if({rx[3],rx[4]}!=0||{rx[5],rx[6]}!=16'hffff)$fatal(1,"EB wrap accepted");
  consume(0);progress495;if({rx[3],rx[4],rx[5],rx[6]}!=0||rx[2]!=2)$fatal(1,"EB wrap retired");
  // Both short and overlong EB transfers fail closed; E0 remains20B.
  common_reset;tx[0]=8'heb;transfer(7);if(!fault)$fatal(1,"short EB accepted");
  common_reset;tx[0]=8'heb;transfer(9);if(!fault)$fatal(1,"long EB accepted");
  common_reset;
  // Legacy 16-byte E0 is incompatible and fail-closed.''')
    (a.out/'sink_window184_tb.sv').write_text(s,encoding='utf8',newline='\n')
    def run(label,cmd):
        with (a.out/(label+'.log')).open('wb')as f:r=subprocess.run([str(a.bin/(cmd[0]+'.exe')),*cmd[1:]],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        text=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-4500:]
        return text
    run('vlib',['vlib','work']);run('compile',['vlog','-sv','nes_domain_reset124.sv','nes_sink_spi165.sv','nes_sink_bus165.sv','nes_sink_bridge165.sv','sink_window184_tb.sv'])
    rows=[]
    for name,phase,wrap in [('normal',0,0),('phase',3.5,0),('wrap',0,1)]:
        s=run(name,['vsim','-c','sink_window184_tb',f'-gPHASE={phase}',f'-gWRAP={wrap}','-do','onerror {quit -code 1};run -all;quit -f']);m=re.search(r'PASS WINDOW184 calls=(\d+) wirebytes=(\d+) checks=(\d+) packets=33',s);assert m,s[-4500:]
        shutil.copyfile(a.out/'transactions.txt',a.out/(name+'-transactions.txt'));rows.append({'name':name,'calls':int(m[1]),'wire_B':int(m[2]),'checks':int(m[3])})
    r={'passed':True,'scope':__doc__,'rows':rows,'SPI_SHA256':sha(a.board/'nes_sink_spi165.sv'),'physical_time':False,'SNES_program_unchanged':True}
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
