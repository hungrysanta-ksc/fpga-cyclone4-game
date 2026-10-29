# SPDX-License-Identifier: MIT
"""485 C runtime -> fixed482 board/PSRAM/NES RTL -> actual65816 and STOP.

Functional transaction RPC, seeded verified ROM, modeled native board setup.
Host C is not M4/IRQ timing, and Mesen/RTL do not share a physical timeline.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
for n in ['board','arm','rom','core','out']:
    p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args()
args=[sys.executable,'-X','utf8',str(ROOT/'tools/test_nes_mmc480_live.py'),'--prepare-only']
for n in ['board','arm','rom','core','out']:args+=['--'+n,str(getattr(a,n).resolve())]
subprocess.run(args,check=True)
runner=a.out.parent/(a.out.name+'-runner.py')
s=runner.read_text(encoding='utf8')
assert s.count("rx[1]!=0x79")==1
s=s.replace('rx[1]!=0x79','rx[1]!=0x7b')
extra=r'''
# Host C has no DWT. Model the same128us quiet interval explicitly in RTL;
# this preserves guard checks, but does not model ARM/IRQ execution time.
h=d/'host.c';text=h.read_text()
needle='#include "run136-selected.inc"'
quiet="""static unsigned quiet485_calls;
static bool quiet485(void *ctx,bool (*guard)(void *),unsigned reason,bool progress){
 (void)reason;if(progress)return true;
 if(!guard(ctx))return false;
 quiet485_calls++;rpc(11,10752,NULL,0,NULL,0);
 return guard(ctx);
}
"""
assert text.count(needle)==1;text=text.replace(needle,quiet+needle)
needle='rpc(9,0,NULL,0,NULL,0);'
assert text.count(needle)==1;text=text.replace(needle,'printf("QUIET485 calls=%u model_ns_per_call=128000\\n",quiet485_calls);'+needle)
h.write_text(text)
f=d/'native_fixture.inc';text=f.read_text();needle=' while(!runtime.frames&&nes_runtime165_step(&runtime))'
assert text.count(needle)==1;f.write_text(text.replace(needle,' runtime.transport.wait=quiet485;\n'+needle))
t=d/'join208_tb.sv';text=t.read_text();needle='default:$fatal(1,"bridge timeout/command %0d",op);'
assert text.count(needle)==1;t.write_text(text.replace(needle,'11:begin repeat(a)@(negedge dut.host_clk);join208_reply(0);end\n    '+needle))
'''
needle="exe=prior/'client/sink165.sfc'"
assert s.count(needle)==1
s=s.replace(needle,extra+'\n'+needle)
runner.write_text(s,encoding='utf8',newline='\n')
# argv used by the generated original447 parser, not this wrapper's parser.
sys.argv=[str(runner),'--board',str(a.board),'--rtl',str(a.core),'--rom',str(a.rom),'--out',str(a.out)]
exec(compile(s,str(runner),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_nrom447_run136.py')})
r=json.loads((a.out/'result.json').read_text(encoding='utf8'))
r['scope485']=__doc__
(a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
