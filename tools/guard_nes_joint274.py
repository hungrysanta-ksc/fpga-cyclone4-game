# SPDX-License-Identifier: MIT
"""Exercise split boundaries through the retained270 RTL and its STOP guards.

The pinned270 generated testbench is a harness fixture, not new RTL. New274
ARM packets replace its input; transport CRC is recomputed after mutations.
"""
from pathlib import Path
import argparse,json,shutil
from nes_delta231 import BASE,ROOT,sha,once
from probe_nes_joint264 import packets
from probe_nes_joint261 import run

CASES={
 39:'STOP after first224B CGRAM fragment, before remaining16B',
 40:'STOP after first235B dense manifest fragment',
 41:'unaligned second CGRAM fragment descriptor, valid transport CRC',
 42:'gap before second dense manifest fragment, valid transport CRC',
 43:'replayed sequence on second CGRAM fragment, valid transport CRC',
 44:'second CGRAM fragment redirected to OAM; required CGRAM receipt absent',
}

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--questa-bin',type=Path,required=True)
 a=ap.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 prior=BASE/'probes/nes-joint270/guards01'
 r=json.loads((prior/'result.json').read_text());assert r['passed']
 pins={}
 # Copy immutable stimulus and source evidence; compile a new local work library.
 for p in prior.iterdir():
  if p.is_file() and p.suffix in ('.sv','.c','.hex','.lens','.desc','.cfg','.expected','.palette','.records','.txt'):
   shutil.copyfile(p,d/p.name);pins[str(p)]=sha(p)
 for name,h in r['rtl_hashes'].items():assert sha(d/name)==h
 assert sha(d/'joint266_tb.sv')==r['TB_sha256']
 packet_path=BASE/'probes/nes-joint274/arm01/frame905.packets'
 pp=packets(packet_path);pins[str(packet_path)]=sha(packet_path)
 assert len(pp)==60
 (d/'all905.hex').write_text(''.join(f'{v:02x}\n' for p in pp for v in p),newline='\n')
 (d/'all905.lens').write_text('\n'.join(f'{v:x}' for v in [len(pp),*map(len,pp)])+'\n',newline='\n')
 s=(d/'joint266_tb.sv').read_text()
 s=once(s,'      if(!injected264)begin','''      if(!injected264)begin
       if(all263[at]==2&&all263[at+1]==3&&all263[at+10]==224&&all263[at+11]==0)begin
        if(GNEG==41&&j==10)begin tx[j+1]=225;injected264=1;end
        if(GNEG==43&&j==2)begin tx[j+1]=tx[j+1]-1'b1;injected264=1;end
        if(GNEG==44&&j==1)begin tx[j+1]=4;injected264=1;end
       end
       if(GNEG==42&&all263[at]==10&&all263[at+10]==235&&j==10)begin
        tx[j+1]=236;injected264=1;
       end''')
 s=once(s,' initial begin : result264',''' initial begin : split_cancel274
  if(GNEG==39)begin
   wait(dut.flow.state==dut.flow.ORET&&dut.flow.header[0]==2&&
        dut.flow.header[1]==3&&dut.flow.startpos==0&&dut.flow.plen==224);
   @(negedge host_clk);disable bus263;bus_read=1;bus_write=1;
   injected264=1;test_abort=1;
  end
  if(GNEG==40)begin
   wait(dut.flow.state==dut.flow.ORET&&dut.flow.header[0]==10&&
        dut.flow.startpos==0&&dut.flow.plen==235);
   @(negedge host_clk);disable bus263;bus_read=1;bus_write=1;
   injected264=1;test_abort=1;
  end
 end
 initial begin : result264''')
 s=once(s,'  wait(source_fault);disable bus263;bus_read=1;',
        '  wait(source_fault);if(GNEG>=39&&!injected264)$fatal(1,"split guard not injected");disable bus263;bus_read=1;')
 s=s.replace('PASS DIRECT266','PASS SPLIT274')
 (d/'joint266_tb.sv').write_text(s,encoding='utf-8',newline='\n')
 run('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',
     ['-O2','-std=c99','-Wall','-Wextra','-Werror','-shared','nes_producer264.c','-o','producer263.dll'],d,'native')
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib')
 run(a.questa_bin/'vlog.exe',['-sv',*r['rtl_hashes'],'joint266_tb.sv'],d,'vlog')
 guards=[]
 for i in [3,23,29,*CASES]:
  log=run(a.questa_bin/'vsim.exe',['-c','-sv_lib','producer263','work.joint266_tb',
      f'-gGNEG={i}','+LAST=905','-do','onerror {quit -code 1};run -all;quit -f'],d,f'guard{i}',180)
  assert f'PASS SPLIT274 GNEG={i}' in log;guards.append(i)
  print('guard',i,'PASS',flush=True)
 result=dict(passed=True,guards=guards,new_cases=CASES,scope=__doc__,
  rtl_hashes={n:sha(d/n) for n in r['rtl_hashes']},TB_sha256=sha(d/'joint266_tb.sv'),
  script_sha256=sha(Path(__file__)),pins=pins)
 shutil.copyfile(__file__,d/Path(__file__).name)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')

if __name__=='__main__':main()
