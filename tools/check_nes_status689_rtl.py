"""Clock-by-clock688/689 boundary comparison plus maximal packet and snapshot races."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from nes_raw506 import once,sha

def prepare(a):
    a.out.mkdir(parents=True,exist_ok=False)
    files=['nes_sink_bus165.sv','nes_sink_spi165.sv','nes_sink_bridge165.sv','nes_domain_reset124.sv','sink-program.hex']
    for n in files:shutil.copyfile(a.board/n,a.out/n)
    for n in files[:3]:
        s=(a.base/n).read_text()
        for old in ('nes_sink_bus165','nes_sink_spi165','nes_sink_bridge165'):s=s.replace(old,old+'_reference')
        (a.out/('reference_'+n)).write_text(s,newline='\n')
    s=Path('tests/nes-functional/progress680_tb.sv').read_text().replace('module progress680_tb;','module status689_tb;\n parameter real HALF=190.476;')
    s=s.replace('#190.476','#(HALF)')
    begin=s.index(' nes_sink_bridge165 dut(');end=s.index('\n always #',begin)
    instance=s[begin:end].replace('nes_sink_bridge165 dut','nes_sink_bridge165_reference reference')
    for name in ('selected','miso','oe','dir','pc','fault','sreset','dout','pads'):
        instance=re.sub(r'\('+name+r'\)', '('+name+'_ref)',instance)
    s=s[:end]+'''
 wire selected_ref,miso_ref,oe_ref,dir_ref,pc_ref,fault_ref,sreset_ref;
 wire [7:0] dout_ref;wire [15:0] pads_ref;
'''+instance+'''
 integer compared=0;
 always @(negedge clk)if(!reset)begin
  if({selected,oe,dir,pc,fault,sreset,pads}!=={selected_ref,oe_ref,dir_ref,pc_ref,fault_ref,sreset_ref,pads_ref})$fatal(1,"boundary controls differ");
  if(selected&&miso!==miso_ref)$fatal(1,"SPI bit differs");
  if(!oe&&dir&&dout!==dout_ref)$fatal(1,"SNES byte differs");
  if({dut.endpoint.accepted,dut.endpoint.retired,dut.endpoint.progress,dut.ready,dut.length}!==
     {reference.endpoint.accepted,reference.endpoint.retired,reference.endpoint.progress,reference.ready,reference.length})$fatal(1,"credit/event timing differs");
  compared++;
 end
'''+s[end:]
    s=s.replace('force dut.mp=1;','force dut.mp=1;force reference.mp=1;').replace('release dut.mp;','release dut.mp;release reference.mp;')
    s=s.replace("dut.endpoint.retired=16'hffff;", "dut.endpoint.retired=16'hffff;reference.endpoint.accepted=16'hffff;reference.endpoint.retired=16'hffff;")
    s=once(s,'  $display("PASS680 checks=%0d phase=%0f",checks,PHASE);$finish;', '''
  // Eight maximal packets cross both queue slots and the 256-byte offset wrap.
  restart();
  for(int n=0;n<8;n++)begin
   reg [15:0] crc;
   prepare(n);head[12]=240;
   tx[0]='he1;crc=c16('hffff,tx[0]);
   for(int k=0;k<256;k++)begin tx[k+1]=k<16?head[k]:(k*37+n*19);crc=c16(crc,tx[k+1]);end
   tx[257]=crc[15:8];tx[258]=crc[7:0];transfer(259);
   if(dut.length!==256)$fatal(1,"max packet length");
   for(int k=0;k<256;k++)begin
    address='h400000+k;rn=0;wn=1;#150;
    if(oe||!dir||dout!==tx[k+1])$fatal(1,"max packet byte %0d",k);
    rn=1;#50;
   end
   // Snapshot is immutable while ACK bytes and the queued head change.
   fork status();begin #16000;publish();end join
   event_write();expect_flags(10);
  end
  // STOP cannot tear an already captured response, but cancels the next one.
  fork status();begin #16000;stop=1;end join
  expect_flags(2);stop=0;expect_flags(2);
  // High length bytes and low-byte overflow must never expose a record.
  for(int mode=0;mode<5;mode++)begin
   reg [15:0] crc;
   restart();prepare(0);head[12]=mode<3?0:(mode==3?241:255);head[13]=mode<3?(1<<mode):0;
   crc=c16('hffff,'he1);tx[0]='he1;
   for(int k=0;k<16;k++)begin tx[k+1]=head[k];crc=c16(crc,head[k]);end
   tx[17]=crc[15:8];tx[18]=crc[7:0];transfer(19);status();
   if(!fault||dut.endpoint.accepted!=0||dut.ready)$fatal(1,"invalid length published");
  end
  $display("PASS689 checks=%0d compared=%0d phase=%0f half=%0f",checks,compared,PHASE,HALF);$finish;''')
    (a.out/'status689_tb.sv').write_text(s,newline='\n')
    commands=[('vlib',['work']),('vlog',['-sv',*files[:-1],*('reference_'+n for n in files[:3]),'status689_tb.sv'])]
    commands.extend((f'vsim{i}',['-c','status689_tb',f'-gPHASE={phase}',f'-gHALF={half}','-do','onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0']) for i,(phase,half) in enumerate(((0,190.476),(8,190.476),(0,47.619),(8,47.619))))
    for name,args in commands:
        tool='vsim' if name.startswith('vsim') else name
        with (a.out/(name+'.log')).open('wb') as log:subprocess.run([a.bin/(tool+'.exe'),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=180,check=True)
        if tool=='vsim':assert 'PASS689' in (a.out/(name+'.log')).read_text()
    result=dict(passed=True,pins={n:sha(a.out/n) for n in files},reference={n:sha(a.base/n) for n in files},bench=sha(a.out/'status689_tb.sv'),
        runs=[re.search(r'PASS689[^\n]+',(a.out/f'vsim{i}.log').read_text())[0] for i in range(4)],
        scope='Sampled host-clock external/control equivalence; real serial SPI/SNES strobes; max payload and overlapping ACK/STOP. Not exhaustive formal proof or placed timing simulation.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result['runs']))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('bin','base','board','out'):p.add_argument('--'+k,type=Path,required=True)
    prepare(p.parse_args())
