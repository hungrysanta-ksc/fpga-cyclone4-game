# SPDX-License-Identifier: MIT
"""Changed RAM inference and actual board-top routing; no repeated core boot."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['prepared','prior','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 a.out.mkdir(parents=True,exist_ok=False)
 files=['nes_native_frame165.sv','nes_native_planes165.sv','nes_native_compact_planes165.sv','nes_native_raster_frame165.sv','nes_native_fill165.sv','nes_native_fetch165.sv','nes_native_spi165.sv','fxpak_nes_screen137_top.sv','nes_domain_reset124.sv','nes_run_observer134.sv','nes_pad_trace156.sv','nes_ppu_history157.sv','nes_game_pad150.sv','nes_dac162.sv','nes_screen_status151.sv','nes_sink_bridge165.sv','nes_sink_bus165.sv','nes_sink_spi165.sv']
 for n in files:shutil.copy2(a.prepared/n,a.out/n)
 shutil.copy2(a.prepared/'sink-program.hex',a.out/'sink-program.hex')
 tbs=['native_frame_lease165_tb.sv','native_planes165_tb.sv','native_spi165_tb.sv','sink_board165_tb.sv']
 for n in tbs:shutil.copy2(ROOT/'tests/nes-functional'/n,a.out/n)
 # Compile actual board peripheral wiring. Only the CPU/loader lifecycle and
 # its existing SPI group are a boundary stub; full real core is synthesized.
 s=(a.prepared/'nes_live_joint.sv').read_text();header=s[:s.index(');')+2]
 outputs=[]
 for names in re.findall(r'output wire\s+(?:\[[^\]]+\]\s*)?([\w,]+)',header.replace(',output wire','\noutput wire')):outputs+=[n for n in names.split(',') if n]
 values={'out_host_clk':'CLKIN','out_host_locked':'!ext_reset','out_run_enable':'test_run','out_observe_reset':'ext_reset||!test_run','out_rom_fault':'test_fault','out_native_spi_fault':'test_native_fault','out_sample':"16'h8000",'out_spi_selected':"!ext_SPI_SS&&(command==8'h60||command==8'hd0)&&count>=8"}
 stub=header+'''
reg test_run=1,test_fault=0,test_native_fault=0;
reg [7:0] command=0,shift=0;integer count=0;
always @(posedge ext_SPI_SCK or posedge ext_SPI_SS)begin
 if(ext_SPI_SS)begin count<=0;command<=0;shift<=0;end
 else begin shift<={shift[6:0],ext_SPI_MOSI};count<=count+1;if(count==7)command<={shift[6:0],ext_SPI_MOSI};end
end
'''+''.join('assign '+n+'='+values.get(n,"'0")+';\n' for n in outputs)+'endmodule\n'
 (a.out/'core_stub.sv').write_text(stub)
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*map(str,args)],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:];return s
 def sim(module,args,label):return run('vsim',['-c','work.'+module,*args,'-do','onerror {quit -code 1}; run -all; quit -f'],label)
 run('vlib',['work'],'vlib');run('vlog',['-sv','-mfcu',*files,*tbs,'core_stub.sv'],'vlog')
 lease=sim('native_frame_lease165_tb',[],'lease');assert 'PASS' in lease
 pair=a.prior/'nes-native-pair165/planes01';pin=json.loads((a.prior/'nes-native-pair165/evidence-manifest.json').read_bytes())
 cases=[]
 for frame,mode in [(12,0),(15,0),(12,2)]:
  n=f'frame-{frame}-mode-{mode}';src=pair/(n+'.tsv');assert sha(src)==pin['planes01/'+src.name]
  shutil.copy2(src,a.out/src.name);sim('native_planes165_tb',[f'+INPUT={src.name}',f'+OUTPUT={n}.dump',f'+MODE={mode}'],n)
  for suffix in ['.dump','.dump.events','.dump.old']:
   src=pair/(n+suffix);assert sha(src)==pin['planes01/'+src.name]
   assert (a.out/src.name).read_bytes()==src.read_bytes(),src.name
  cases.append(n)
 spi=a.prior/'nes-native-spi165/spi04';pin=json.loads((a.prior/'nes-native-spi165/evidence-manifest.json').read_bytes())
 assert sha(spi/'records.hex')==pin['spi04/records.hex'];shutil.copy2(spi/'records.hex',a.out/'records.hex')
 for phase in [0,3.5]:
  label='phase'+str(phase);sim('native_spi165_tb',[f'-gPHASE={phase}','+COUNT=1717'],label)
  src=spi/(label+'.transactions.txt');assert sha(src)==pin['spi04/'+src.name]
  assert (a.out/'transactions.txt').read_bytes()==src.read_bytes()
  shutil.copy2(a.out/'transactions.txt',a.out/src.name)
 board=sim('sink_board165_tb',[],'board');assert 'PASS SINKBOARD165' in board
 result=dict(passed=True,lease=[x.strip() for x in lease.splitlines() if 'PASS' in x],replayed_cases=cases,spi_phases=2,spi_records=1717,board=[x.strip() for x in board.splitlines() if 'PASS' in x],scope='Actual board peripheral top with core lifecycle stub; RAM changed modules actual replay and lease test; full real core synthesis is separate.',prepared_sources={n:sha(a.prepared/n) for n in files},public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_sink_board165.py','tools/nes_sink_board165.py','tools/nes_native_ram_board165.py','tests/nes-functional/sink_board165_tb.sv']})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
