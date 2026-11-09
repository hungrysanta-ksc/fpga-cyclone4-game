"""Bounded adjacent-map pair; retain 682 checked input and first BG plan."""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import once,sha

def prepare(base,out,early_pair=False,handoff=False):
    expected='ee477ad169b3a2830d2002ef17e07316363a68f68e86470c1d7f3d20226c4f2c'
    assert sha(base/'src/obj-nes-100/firmware.stm')==expected
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    p=out/'src/nes_native_sink165.c';s=p.read_text()
    if handoff:
        assert not early_pair
        h=out/'src/nes_native_sink165.h'
        h.write_text(once(h.read_text(),'bool displayed;uint8_t map_next;',
            'bool displayed;uint8_t map_next;bool map_pair683; /* Existing alignment padding. */'),newline='\n')
        s=once(s,'s->map_next=0;s->sequence=0;', 's->map_next=0;s->map_pair683=false;s->sequence=0;')
        s=once(s,'bool map527(struct nes_native_sink165 *s,struct nes_native_video165 *p,uint64_t mask,bool early){',
            '''bool map527(struct nes_native_sink165 *s,struct nes_native_video165 *p,uint64_t mask,bool early){
 /* A planner offer owns only three completed rows. Carry its exact full
  * extent into final output; never fetch the following rows early. The
  * window's last head proves no intervening tile/ordinary packet exists. */
 bool pair=!early && s->map_pair683 && s->plan && s->plan->bank_history==2 &&
     s->plan->window && s->plan->window->last[0]==2 && s->plan->window->last[1]==2;
 s->map_pair683=false;''')
        s=once(s,'  if(!packet(s,early?24:2,2,first*64,p->map+first*64,count*64))return false;',
            '''  bool adjacent=pair && first==(s->map_next&127) && count==3;
  if(!packet(s,(early||adjacent)?24:2,2,first*64,p->map+first*64,count*64))return false;
  pair=false;''')
        s=once(s,'  if(early){s->map_next=(uint8_t)g;break;}',
            '  if(early){s->map_next=(uint8_t)g;s->map_pair683=count==3;break;}')
        p.write_text(s,newline='\n')
        (out/'recipe683.json').write_text(json.dumps(dict(base=expected,source=sha(p),header=sha(h),planner_to_output_handoff=True),indent=2)+'\n')
        return
    s=once(s,'bool map527(struct nes_native_sink165 *s,struct nes_native_video165 *p,uint64_t mask,bool early){',
        '''bool map527(struct nes_native_sink165 *s,struct nes_native_video165 *p,uint64_t mask,bool early){
 /* At most two adjacent full map packets share producer arbitration. The
  * first services BG/END normally; the second retains queue credit, STOP,
  * CRC and SNES acceptance. No pointer or permission outlives this call. */
 unsigned pair=64;''')
    s=once(s,'  if(!packet(s,early?24:2,2,first*64,p->map+first*64,count*64))return false;',
        '''  bool paired=first==pair && count==3;
  if(!packet(s,(early||paired)?24:2,2,first*64,p->map+first*64,count*64))return false;
  pair=!paired && count==3 && s->plan && s->plan->bank_history==2 ? g : 64;''')
    if early_pair:
        s=once(s,'pair=!paired && count==3 && s->plan && s->plan->bank_history==2 ? g : 64;',
            'pair=early && !paired && count==3 && s->plan && s->plan->bank_history==2 && s->plan->ending ? g : 64;')
        s=once(s,'  if(early){s->map_next=(uint8_t)g;break;}',
            '''  if(early){
   s->map_next=(uint8_t)g;
   /* END's quiet-map callback may cross into the final output call. Keep
    * one adjacent full pair together, bounded by live four-credit checks. */
   if(paired || pair!=g || g>61 || ((mask>>g)&7)!=7)break;
  }''')
    p.write_text(s,newline='\n')
    (out/'recipe683.json').write_text(json.dumps(dict(base=expected,source=sha(p),max_pair_bytes=384,END_callback_pair=early_pair),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--early-pair',action='store_true');p.add_argument('--handoff',action='store_true');a=p.parse_args();prepare(a.base,a.out,a.early_pair,a.handoff)
