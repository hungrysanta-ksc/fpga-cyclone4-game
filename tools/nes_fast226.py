# SPDX-License-Identifier: MIT
"""Skip redundant BG row reconstruction only when both source/destination are ordinary."""
from pathlib import Path
import argparse,json
from nes_scroll225 import ROOT,BASE,sha,once
from nes_board181 import copy_pins


def planner(s):
    identity = sum((i//2) << (13+i*3) for i in range(16))
    s=once(s,' for(unsigned g=0;g<groups;g++)for(unsigned x=0;x<33;x++){',''' /*226: exceptions are immutable validated positions in this capture.
  * Column0 changes destination fineY for every column. Otherwise only the
  * column containing an exception needs the full row/alternate-tag path.
  * This is not a CHR cache and does not skip any slot lookup or write. */
 for(unsigned g=0;g<groups;g++){
  uint64_t exceptional=0;
  for(unsigned i=0;i<s->counts[3];i++){
   unsigned pos=(s->exceptions[i]>>6)&8191,y=pos/33;
   if(y>=first[g]&&y<end[g])exceptional|=UINT64_C(1)<<(pos%33);
  }
  if(exceptional&1)exceptional=UINT64_C(0x1ffffffff);
  for(unsigned x=0;x<33;x++){''')
    s=once(s,'  for(unsigned y=first[g];y<end[g];y++){',
        f'  uint64_t key=(cell&8191)|UINT64_C(0x{identity:x});\n  if((exceptional>>x)&1){{\n  for(unsigned y=first[g];y<end[g];y++){{')
    s=once(s,'  uint64_t key=cell&8191;for(unsigned f=0;f<16;f++)',
        '  key=cell&8191;for(unsigned f=0;f<16;f++)')
    s=once(s,'  unsigned slot=nes_resident211_slot(resident,p,key,&q);',
        '  } /* full exceptional row mapping; ordinary q.row remains identity */\n  unsigned slot=nes_resident211_slot(resident,p,key,&q);')
    s=once(s,'\n /* No callback retains scratch pointers;',
        '\n } /* compact groups */\n\n /* No callback retains scratch pointers;')
    return s


def runtime(s):
    old='''  if(!guard(s)||!nes_resident211_begin(s->resident,s->content_epoch,true,r->generation,resident_plan213,s)||
     !nes_sink212_begin(&s->sink,s->resident)||
     !planner221(s)||
     !nes_plan200_finish(&s->plan))
   return fail(s,NES_RUNTIME165_DISPLAY);'''
    new='''  uint32_t phase226=s->ticks(s->ctx);
  if(!guard(s)||!nes_resident211_begin(s->resident,s->content_epoch,true,r->generation,resident_plan213,s)||
     !nes_sink212_begin(&s->sink,s->resident))return fail(s,NES_RUNTIME165_DISPLAY);
  nes_budget210_time(B226_BEGIN,s->ticks(s->ctx)-phase226);
  if(!planner221(s))return fail(s,NES_RUNTIME165_DISPLAY);
  phase226=s->ticks(s->ctx);
  if(!nes_plan200_finish(&s->plan))return fail(s,NES_RUNTIME165_DISPLAY);
  nes_budget210_time(B226_FINISH,s->ticks(s->ctx)-phase226);'''
    return once(s,old,new)


def prepare(out):
    prior=BASE/'probes/nes-scroll225/arm01'
    p=json.loads((prior/'preparation-scroll225.json').read_bytes())
    pins=p['copied']|p['changed']|p['added'];copy_pins(prior,out,pins)
    for n,fn in [('nes_planner211.c',planner),('nes_native_runtime165.c',runtime)]:
        f=out/'src'/n;f.write_text(fn(f.read_text()),encoding='utf8',newline='\n')
    f=out/'src/nes_budget210.h';f.write_text(once(f.read_text(),'B221_D0_CLOCK,B210_FIELDS','B221_D0_CLOCK,B226_BEGIN,B226_FINISH,B210_FIELDS'),encoding='utf8',newline='\n')
    f=out/'src/nes_budget210.c';s=f.read_text()
    s=once(s,'if(phase>=B210_RECEIVE&&phase<=B210_SEAL)',
        'if((phase>=B210_RECEIVE&&phase<=B210_SEAL)||phase==B226_BEGIN||phase==B226_FINISH)')
    s=once(s,'budget_schema=222','budget_schema=226')
    s=once(s,'mapdirty,d1_payload,d0_clock','mapdirty,d1_payload,d0_clock,begin_ticks,finish_ticks')
    f.write_text(s,encoding='utf8',newline='\n')
    for n in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
        f=out/'src'/n;f.write_text(f.read_text().replace('225','226'),encoding='utf8',newline='\n')
    changed={n:sha(out/n) for n,h in pins.items() if sha(out/n)!=h}
    assert set(changed)=={'src/'+n for n in ['nes_planner211.c','nes_native_runtime165.c','nes_budget210.c','nes_budget210.h','nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']}
    report=dict(copied=pins,changed=changed,added={},new_fpga=False,new_snes_rom=False,
        added_retained_counter_bytes=96,source_sha256=sha(Path(__file__)),physical=False)
    (out/'preparation-fast226.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    print(json.dumps(prepare(p.parse_args().out)['changed']))
