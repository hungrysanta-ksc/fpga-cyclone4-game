# SPDX-License-Identifier: MIT
"""Descriptor/reference corruption, STOP, ordered/final ACK and RAM freeze."""
from pathlib import Path
import argparse,json,shutil
from nes_delta231 import BASE,ROOT,sha,once
from probe_nes_joint264 import packets
from probe_nes_joint261 import run
from nes_joint275 import patch
from nes_inline275 import unwrap

CASES={
39:'syntax-valid wrong receipt first granule',
40:'range count beyond consumed descriptor',
41:'wrong original-payload reference offset',
42:'manifest reference exceeds held payload',
43:'bad inline logical length',
44:'unknown program opcode',
45:'STOP while fetching reference operands',
46:'STOP during referenced hash data',
47:'STOP after DMA ACK before reference execution',
48:'missing final finish operand, valid recomputed transport CRC',
49:'wrong hash repeat pattern',
50:'wrong hash start identity',
51:'reference receipt type redirected from CGRAM to OAM',
52:'RLE literal token falsely represented as a zero run',
53:'RLE literal reference points at the token rather than its data',
}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--reuse',type=Path,help='Reuse PASS logs only after exact RTL, TB and original stimulus checks')
 ap.add_argument('--questa-bin',type=Path,required=True);a=ap.parse_args()
 d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 prior=BASE/'probes/nes-joint270/guards01';r=json.loads((prior/'result.json').read_text());pins={}
 for p in prior.iterdir():
  if p.is_file() and p.suffix in ('.sv','.c','.hex','.lens','.desc','.cfg','.expected','.palette','.records','.txt'):
   shutil.copyfile(p,d/p.name);pins[str(p)]=sha(p)
 patch(d)
 packet_path=Path('C:/Users/mohallo/AppData/Local/Temp/nes-joint275/arm02/frame905.packets')
 pp=packets(packet_path);pins[str(packet_path)]=sha(packet_path)
 (d/'all905.hex').write_text(''.join(f'{v:02x}\n' for p in pp for v in p))
 (d/'all905.lens').write_text('\n'.join(f'{v:x}' for v in [len(pp),*map(len,pp)])+'\n')
 s=(d/'joint266_tb.sv').read_text()
 s=s.replace("dut.flow.queue.buffer[{dut.flow.queue.retired[1:0],8'd0}+i]",
             "dut.flow.queue.buffer[{dut.flow.queue.retired[1:0],8'd0}+i+(dut.flow.inline275?2:0)]")
 s=once(s,"n=sizes263[k+1];tx[0]=8'he1;", """n=sizes263[k+1];
     if(GNEG==48&&all263[at]==0&&all263[at+2]==3)begin n=n-1;injected264=1;end
     tx[0]=8'he1;""")
 s=once(s,'transfer(n+3);at+=n;packetbytes263+=n+3;',
        'transfer(n+3);at+=sizes263[k+1];packetbytes263+=n+3;')
 s=once(s,'      if(!injected264)begin',r'''      if(!injected264)begin
       if(all263[at]==0)begin
        if((GNEG==52||GNEG==53)&&all263[at+2]==11&&all263[at+12]==235)injected264=1;
        if(all263[at+2]==2&&all263[at+3]==3)begin
         if(GNEG==39&&j==all263[at+1]+4)begin tx[j+1]^=1;injected264=1;end
         if(GNEG==40&&j==all263[at+1]+6)begin tx[j+1]=15;injected264=1;end
         if(GNEG==51&&j==3)begin tx[j+1]=4;injected264=1;end
        end
        if(all263[at+2]==2&&all263[at+3]==5&&all263[at+12]==0)begin
         if(GNEG==41&&j==all263[at+1]+7)begin tx[j+1]^=1;injected264=1;end
         if(GNEG==49&&j==all263[at+1]+8)begin tx[j+1]=2;injected264=1;end
         if(GNEG==50&&j==all263[at+1]+4)begin tx[j+1]=0;injected264=1;end
        end
        if(GNEG==42&&all263[at+2]==10&&j==all263[at+1]+4)begin tx[j+1]=255;injected264=1;end
        if(GNEG==43&&j==1)begin tx[j+1]=255;injected264=1;end
        if(GNEG==44&&j==all263[at+1]+3)begin tx[j+1]=255;injected264=1;end
       end''')
 s=once(s,' initial begin : result264',r'''
 initial begin : inline_cancel275
  if(GNEG>=45&&GNEG<=47)begin
   case(GNEG)
    45:wait(dut.flow.state==dut.flow.RCAP&&dut.flow.at==1);
    46:wait(dut.flow.state==dut.flow.RDATA&&dut.flow.header[20]==9);
    47:wait(dut.flow.state==dut.flow.OSETUP&&dut.flow.header[0]==7);
   endcase
   @(negedge host_clk);disable bus263;bus_read=1;bus_write=1;
   injected264=1;test_abort=1;
  end
 end
 initial begin : result264''')
 s=once(s,'  wait(source_fault);disable bus263;bus_read=1;',
        '  wait(source_fault);if(GNEG>=39&&!injected264)$fatal(1,"guard not injected");disable bus263;bus_read=1;')
 s=s.replace('PASS DIRECT266','PASS INLINE275')
 (d/'joint266_tb.sv').write_text(s,encoding='utf-8',newline='\n')
 reusable=[]
 if a.reuse:
  for name in [*r['rtl_hashes'],'joint266_tb.sv','all905.hex','all905.lens']:
   assert sha(d/name)==sha(a.reuse/name),name
  for i in [3,4,23,29,*CASES]:
   p=a.reuse/f'guard{i}.log'
   if p.exists() and f'PASS INLINE275 GNEG={i}' in p.read_text():
    shutil.copyfile(p,d/p.name);pins[str(p.resolve())]=sha(p);reusable.append(i)
 run('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',
  ['-O2','-std=c99','-Wall','-Wextra','-Werror','-shared','nes_producer264.c','-o','producer263.dll'],d,'native')
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib')
 run(a.questa_bin/'vlog.exe',['-sv',*r['rtl_hashes'],'joint266_tb.sv'],d,'vlog')
 guards=[]
 for i in [3,4,23,29,*CASES]:
  if i in reusable:guards.append(i);continue
  if i in (52,53):
   changed=[]
   for physical in pp:
    logical,program=unwrap(physical)
    if logical[0]==10 and int.from_bytes(logical[10:12],'little')==235:
     count=len(logical)-16;assert 1<=count<=128
     q=bytearray(logical[:16]);q[0]=11;q[12:14]=(count+2).to_bytes(2,'little')
     q+=bytes([3,count-1])+logical[16:]
     program=bytes([12,count]) if i==52 else bytes([10,count,17])
     physical=bytes([0,len(q)-1])+q+program
    changed.append(physical)
   (d/'all905.hex').write_text(''.join(f'{v:02x}\n' for p in changed for v in p))
   (d/'all905.lens').write_text('\n'.join(f'{v:x}' for v in [len(changed),*map(len,changed)])+'\n')
   (d/f'guard{i}.packets').write_bytes(b''.join(len(p).to_bytes(2,'little')+p for p in changed))
  log=run(a.questa_bin/'vsim.exe',['-c','-sv_lib','producer263','work.joint266_tb',f'-gGNEG={i}','+LAST=905',
   '-do','onerror {quit -code 1};run -all;quit -f'],d,f'guard{i}',180)
  assert f'PASS INLINE275 GNEG={i}' in log;guards.append(i);print('guard',i,'PASS',flush=True)
 result=dict(passed=True,guards=guards,reused_exact_evidence=reusable,new_cases=CASES,scope=__doc__,
  rtl_hashes={n:sha(d/n) for n in r['rtl_hashes']},TB_sha256=sha(d/'joint266_tb.sv'),pins=pins)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
