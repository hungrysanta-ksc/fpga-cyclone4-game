"""Lend one existing checked bulk service before719's bounded map-DMA wait.

Keep727 map pairs and BG production. Consume/receipt ownership stays with
the normal E1/65816/FPGA path; no early bank return or display completion.
Share729's independently checked span costs only, not its ordinary bypass.
"""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from nes_raw506 import once,sha
from prepare_nes_tail729 import run as costs

def run(a):
 costs(SimpleNamespace(base=a.base,out=a.out,owned=False,cheap_oam=True))
 p=a.out/'nes_native_sink165.c';s=p.read_text()
 s=once(s,'   unsigned left=w->poll_limit;', '''   /*730 The complete map run is already queued. Service one checked
    * producer through its normal owned descriptor before entering the
    * existing empty-queue DMA opportunity. The following drain includes
    * that real bulk receipt; no bank is returned by this ARM call alone.
    * Keep the original absolute deadline, not a new delay after service. */
   if(!nes_plan200_progress(s->plan,NES_ORDINARY553))return fail(s,5);
   unsigned left=w->poll_limit;''')
 if a.ready_chain:
  s=once(s,'   if(!nes_plan200_progress(s->plan,NES_ORDINARY553))return fail(s,5);', '''   /*730B Reuse the existing ready-chain drain policy: a real bulk receipt
    * returns its bank before querying the next descriptor. An empty producer
    * yields immediately; no FINAL wait for future ROM and no early ACK. */
   if(!nes_plan200_progress(s->plan,NES_HDMA554))return fail(s,5);''')
 p.write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe730.json')).write_text(json.dumps(dict(stage=730,ready_chain=a.ready_chain,scope=__doc__,base=sha(a.base/'obj-nes-100/firmware.stm'),sources={p.name:sha(p)},new_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--ready-chain',action='store_true')
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
