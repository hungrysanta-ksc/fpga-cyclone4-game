# SPDX-License-Identifier: MIT
"""Prepare184 identity and bounded post-STOP queue diagnostic fields; not release approval."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_clip178 import replace
from nes_board181 import copy_pins

def prepare(prior,out):
 p=json.loads((prior/'preparation-window184.json').read_bytes());pins=p['copied']|p['changed']|p['added'];copy_pins(prior,out,pins);changed={}
 def write(n,s):(out/n).write_text(s,encoding='utf8',newline='\n');changed[n]=sha(out/n)
 for n in ['nes_sink_window184.c','nes_sink_window184.h']:write('src/'+n,(ROOT/'src/nes/firmware'/n).read_text())
 for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
  s=(out/n).read_text()
  for a,b in [('NES-GAME-183','NES-GAME-184'),('GAME 183','GAME 184'),('game183.nes','game184.nes'),('fpga_n183.bi3','fpga_n184.bi3'),('last-183.txt','last-184.txt'),('NES183 seq=','NES184 seq='),('nes-progress-183.txt','nes-progress-184.txt'),('NES-GAME183-DEV','NES-GAME184-DEV')]:s=s.replace(a,b)
  if n.endswith('nes_menu_diagnostic.c'):
   s=replace(s,' extra=nes_sink_io170_format(text+n,4096-(unsigned)n);\n if(extra<0)return;',
    r''' extra=snprintf(text+n,4096-(unsigned)n,"sink_window_schema=184\nsink_window_error=%u\nsink_window_sent=%u\nsink_window_retired=%u\nsink_window_flags=%u\nsink_window_ack=%u\n",native_runtime165.transport.error,native_runtime165.transport.sent,native_runtime165.transport.retired,native_runtime165.transport.status_flags,native_runtime165.transport.ack_status);
 if(extra<0||(unsigned)extra>=4096-(unsigned)n)return;''')
  write(n,s)
 r=dict(copied=pins,changed=changed,added={},hardware_package=False,baseline_firmware=sha(prior/'src/obj-nes-100/firmware.stm'),public_sources={n:sha(ROOT/n) for n in ['tools/nes_window184_trial.py','src/nes/firmware/nes_sink_window184.c','src/nes/firmware/nes_sink_window184.h']})
 for n in ['preparation-window184-trial.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();print(json.dumps(prepare(a.prior,a.out)['changed']))
