# SPDX-License-Identifier: MIT
"""Pin-level observation test, actual default window; private FLOAT wrapper."""
from pathlib import Path
import argparse,json,os,re,shutil
from nes_clock_observation087 import materialize
from nes_spi_boot import ROOT,put,run,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--short-window',action='store_true')
 p.add_argument('--mutation',choices=['same-clock','live-snapshot','memory-enable'])
 a=p.parse_args();assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 out=a.out.resolve();assert str(out).isascii();out.mkdir(parents=True,exist_ok=False)
 files=materialize(out)
 for n in ['tools/nes_clock_observation087.py','tools/nes_clock_observation087_test.py','tests/nes-functional/clock_observation087_tb.sv']:
  shutil.copy2(ROOT/n,out/('executed-'+Path(n).name))
 top=out/'fxpak_nes_diagnostic_top.sv';module=out/'nes_clock_observation087.sv'
 if a.mutation=='same-clock':put(top,top.read_text().replace('.ref_clk(SNES_SYSCLK)','.ref_clk(CLKIN)'))
 if a.mutation=='memory-enable':put(top,top.read_text().replace('assign ROM_1CE=1;','assign ROM_1CE=0;'))
 if a.mutation=='live-snapshot':
  s=module.read_text();s=s.replace('reg [127:0] snapshot=0;',"wire [127:0] snapshot={8'd0,8'd16,32'(WINDOW),published_count,window_sequence,4'b0,published_gap,ever_gap,live,valid,8'h87};")
  s=re.sub(r"      if\(\{shift\[6:0\],mosi_sync\[1\]\}==8'hc0\).*?8'h87\};",'',s,flags=re.S);put(module,s)
 shutil.copy2(ROOT/'tests/nes-functional/clock_observation087_tb.sv',out/'tb.sv')
 for tool,args in [('vlib',['work']),('vlog',['-sv',*files,'tb.sv'])]:run([a.questa_bin/(tool+'.exe'),*args],out,tool)
 cases=[]
 window=80000 if a.short_window else 8000000
 matrix=[(25,1250000),(22.727273,1375000),(23.280423,1342330)]
 if a.mutation:matrix=matrix[:1]
 for i,(half,count) in enumerate(matrix):
  realized_half=round(half*1000)/1000
  expected=round(window*125/(2*realized_half*16))
  try:log=run([a.questa_bin/'vsim.exe','-c','clock_observation087_tb',f'+HALF={half}',f'+COUNT={expected}',f'-gWINDOW={window}','-do','onerror {quit -code 1}; run -all; quit -f'],out,'case'+str(i),600)
  except RuntimeError:
   if not a.mutation:raise
   log=(out/f'case{i}.log').read_text(errors='replace')
  if a.mutation:
   expected={'same-clock':'ABSENT_REFERENCE_FALSE_VALID','live-snapshot':'TORN_SNAPSHOT','memory-enable':'MEMORY_NOT_PARKED'}[a.mutation]
   assert '** Fatal:' in log and expected in log;cases.append(dict(expected_failure=expected));break
  assert '** Fatal:' not in log and '** Error:' not in log
  match=re.search(r'PASS OBSERVATION087 count=(\d+) commands=254 coherent=1 both_halt_parked=1',log);assert match
  cases.append(dict(reference_half_ns=half,realized_half_ns=realized_half,expected_count=expected,count=int(match[1]),commands_rejected=254,coherent=True,both_halt_parked=True))
 put(out/'result.json',json.dumps(dict(candidate='NES-CLOCK-OBSERVATION-087',cases=cases,mutation=a.mutation,window_cycles=window,sources={n:sha(out/n) for n in files},hardware_execution=False,installable=False),indent=2)+'\n')
 print('PASS observation087 '+str(cases),flush=True)

if __name__=='__main__':main()
