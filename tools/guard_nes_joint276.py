# SPDX-License-Identifier: MIT
"""Original descriptor/STOP guards across the unified source/receipt core."""
from pathlib import Path
import argparse,json,shutil
from nes_delta231 import BASE,ROOT,sha,once
from nes_joint276 import patch
from probe_nes_joint264 import packets
from probe_nes_joint261 import run

CASES={
39:'STOP after first224B consumed CGRAM fragment',
40:'STOP after first235B dense manifest fragment',
41:'unaligned second CGRAM descriptor',
42:'gap before second dense manifest fragment',
43:'replayed sequence on second CGRAM fragment',
44:'CGRAM fragment redirected to OAM, required receipt absent',
45:'STOP during original descriptor metadata load',
46:'STOP with original payload read outstanding',
47:'STOP during shared core receipt RAM update',
48:'STOP during shared core CRC byte update',
49:'STOP during shared core completion response',
}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--questa-bin',type=Path,required=True);ap.add_argument('--cases',default='1-49')
 a=ap.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 prior=BASE/'probes/nes-joint270/guards01';r=json.loads((prior/'result.json').read_text());assert r['passed'];pins={}
 for p in prior.iterdir():
  if p.is_file() and p.suffix in ('.sv','.c','.hex','.lens','.desc','.cfg','.expected','.palette','.records','.txt'):
   shutil.copyfile(p,d/p.name);pins[str(p)]=sha(p)
 for n,h in r['rtl_hashes'].items():assert sha(d/n)==h
 assert sha(d/'joint266_tb.sv')==r['TB_sha256']
 patch(d)
 pp=packets(BASE/'probes/nes-joint274/arm01/frame905.packets');assert len(pp)==60
 (d/'all905.hex').write_text(''.join(f'{v:02x}\n' for p in pp for v in p),newline='\n')
 (d/'all905.lens').write_text('\n'.join(f'{v:x}' for v in [len(pp),*map(len,pp)])+'\n',newline='\n')
 s=(d/'joint266_tb.sv').read_text()
 s=once(s,' always @(posedge clk)if(dut.h_valid&&h_ready)hashes264++;',
 ''' always @(posedge clk)if((dut.h_valid&&h_ready)||
  (dut.core.encoder.local_event276&&dut.core.encoder.local_kind276==5&&
   (dut.core.encoder.state==dut.core.encoder.H_BYTES||dut.core.encoder.state==dut.core.encoder.H_SCROLL)))hashes264++;''')
 s=once(s,'      if(!injected264)begin','''      if(!injected264)begin
       if(all263[at]==2&&all263[at+1]==3&&all263[at+10]==224&&all263[at+11]==0)begin
        if(GNEG==41&&j==10)begin tx[j+1]=225;injected264=1;end
        if(GNEG==43&&j==2)begin tx[j+1]=tx[j+1]-1'b1;injected264=1;end
        if(GNEG==44&&j==1)begin tx[j+1]=4;injected264=1;end
       end
       if(GNEG==42&&all263[at]==10&&all263[at+10]==235&&j==10)begin tx[j+1]=236;injected264=1;end''')
 s=once(s,' initial begin : result264',''' initial begin : descriptor_cancel276
  case(GNEG)
   39:wait(dut.flow.state==dut.flow.ORET&&dut.flow.header[0]==2&&dut.flow.header[1]==3&&
            {dut.flow.header[11],dut.flow.header[10]}==0&&dut.flow.plen==224);
   40:wait(dut.flow.state==dut.flow.ORET&&dut.flow.header[0]==10&&
            {dut.flow.header[11],dut.flow.header[10]}==0&&dut.flow.plen==235);
   45:wait(dut.core.encoder.state==dut.core.encoder.P_LOAD&&dut.core.encoder.row_i==3);
   46:wait(dut.core.encoder.state==dut.core.encoder.P_RECV);
   47:wait(dut.core.encoder.left_row&&dut.core.encoder.state==dut.core.encoder.V_RWRITE);
   48:wait(dut.core.encoder.local_event276&&dut.core.encoder.local_kind276==5&&
            dut.core.encoder.state==dut.core.encoder.H_SCROLL);
   49:wait(dut.core.encoder.state==dut.core.encoder.P_RETURN);
  endcase
  if(GNEG==39||GNEG==40||GNEG>=45)begin
   @(negedge clk);disable bus263;bus_read=1;bus_write=1;injected264=1;test_abort=1;
  end
 end
 always @(posedge clk)if(!reset&&dut.desc_valid276&&dut.desc_ready276)
  if(!dut.core.output_phase||dut.core.encoder.q_pending||source_fault)$fatal(1,"source/query alias collision");
 initial begin : result264''')
 s=once(s,'  wait(source_fault);disable bus263;bus_read=1;',
        '  wait(source_fault);if(GNEG>=39&&!injected264)$fatal(1,"descriptor guard not injected");disable bus263;bus_read=1;')
 s=s.replace('PASS DIRECT266','PASS DESCRIPTOR276')
 (d/'joint266_tb.sv').write_text(s,encoding='utf-8',newline='\n')
 run('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',
     ['-O2','-std=c99','-Wall','-Wextra','-Werror','-shared','nes_producer264.c','-o','producer263.dll'],d,'native')
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib')
 run(a.questa_bin/'vlog.exe',['-sv',*r['rtl_hashes'],'joint266_tb.sv'],d,'vlog')
 cases=[]
 for group in a.cases.split(','):
  if '-' in group:
   lo,hi=map(int,group.split('-'));cases.extend(range(lo,hi+1))
  else:cases.append(int(group))
 guards=[]
 for i in cases:
  log=run(a.questa_bin/'vsim.exe',['-c','-sv_lib','producer263','work.joint266_tb',f'-gGNEG={i}','+LAST=905',
      '-do','onerror {quit -code 1};run -all;quit -f'],d,f'guard{i}',180)
  assert f'PASS DESCRIPTOR276 GNEG={i}' in log;guards.append(i);print('guard',i,'PASS',flush=True)
 result=dict(passed=True,guards=guards,new_cases=CASES,scope=__doc__,rtl_hashes={n:sha(d/n) for n in r['rtl_hashes']},
  TB_sha256=sha(d/'joint266_tb.sv'),script_sha256=sha(Path(__file__)),pins=pins)
 shutil.copyfile(__file__,d/Path(__file__).name)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')

if __name__=='__main__':main()
