"""Fold726 paired admission into its sole runtime caller and one map epilogue.

The first checked-empty grant owns up to two exact adjacent192B packets.
Each E1 still checks actual queue credit/STOP; no producer request is skipped
outside that grant. Cold and original row/END progression remain separate.
"""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from prepare_nes_accept726 import run as prepare726
from nes_raw506 import once,sha

def run(a):
 prepare726(SimpleNamespace(base=a.base,out=a.out,paired=False,shared_pair=True))
 n='nes_native_runtime165.c';s=(a.out/n).read_text()
 s=once(s,' return nes_sink527_early(&s->sink,s->video,s->resident,mode);', ''' /*727 The runtime callback is the only admission owner. Eliminate the
  * separate sink wrapper, retaining its cursor, credit and STOP checks. */
 if(s->sink.map_next>=64)return true;
 if(mode!=2){
  bool ready;
  if(!nes_plan527_map_credit(&s->plan,&ready))return false;
  if(!ready){if(!s->sink.map_next)s->sink.map_next=128;return true;}
 }
 return map527(&s->sink,s->video,
   s->resident->map_stale[s->resident->target]|s->video->map_dirty,mode);''')
 (a.out/n).write_text(s,encoding='utf8',newline='\n')
 n='nes_native_sink165.c';s=(a.out/n).read_text()
 start=s.index('  pair=pairable && count==3 && s->map_pair683;')
 end=s.index('\n }\n return true;\n}',start)
 s=s[:start]+'''  /*727 Consume the producer grant once, through the same continuation
   * as ordinary output. No second pair cursor or completion override. */
  pair=count==3 && (early==3 || (pairable && s->map_pair683));
  s->map_pair683=early==1 && count==3;
  if(early){
   s->map_next=(uint8_t)g;
   if(early!=3)break;
   early=2;
  }'''+s[end:]
 start=s.index('bool nes_sink527_early(');end=s.index('static bool __attribute__((noinline)) same635',start)
 s=s[:start]+s[end:]
 (a.out/n).write_text(s,encoding='utf8',newline='\n')
 n='nes_native_sink165.h';s=(a.out/n).read_text()
 s='\n'.join(line for line in s.split('\n') if not line.startswith('bool nes_sink527_early('))
 assert 'nes_sink527_early' not in s
 (a.out/n).write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=727,base=sha(a.base/'obj-nes-100/firmware.stm'),scope=__doc__,sources={p.name:sha(p) for p in a.out.iterdir()},new_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
