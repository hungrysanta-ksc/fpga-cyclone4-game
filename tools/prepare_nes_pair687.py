"""Extend the checked warm-map prefix into bounded adjacent packet pairs."""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import once,sha

def prepare(base,out,shared_gap=False,renew_head=False,pending_first=False):
    proof=json.loads(Path('analysis/seal686-verification.json').read_text())
    assert sha(base/'src/obj-nes-100/firmware.stm')==proof['firmware']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    p=out/'src/nes_native_sink165.c';s=p.read_text()
    s=once(s,'bool pair=early!=1 && s->map_pair683 && s->plan && s->plan->bank_history==2 &&',
        'bool pairable=early!=1 && s->plan && s->plan->bank_history==2 &&')
    s=once(s,' s->map_pair683=false;\n for(unsigned g=s->map_next&127;g<64;){',
        ''' bool pair=pairable && s->map_pair683;
 unsigned next=s->map_next&127;
 s->map_pair683=false;
 for(unsigned g=next;g<64;){''')
    s=once(s,'bool adjacent=pair && first==(s->map_next&127) && count==3;',
        'bool adjacent=pair && first==next && count==3;')
    s=once(s,'  pair=false;\n  if(early)',
        '''  /* At most two exact192B map packets per producer query. Every
   * packet retains checked queue credit/CRC/STOP; gaps and short tails query.
   * BG-complete/row callbacks still return after their original one packet. */
  pair=pairable && !adjacent && count==3;next=g;
  if(early)''')
    if shared_gap:
        # Existing gap scan already proves adjacency; no second next cursor.
        s=once(s,' unsigned next=s->map_next&127;\n','')
        s=once(s,' for(unsigned g=next;g<64;){',' for(unsigned g=s->map_next&127;g<64;){')
        s=once(s,'if(!((mask>>g)&1)){g++;continue;}','if(!((mask>>g)&1)){g++;pair=false;continue;}')
        s=once(s,'bool adjacent=pair && first==next && count==3;','bool adjacent=pair && count==3;')
        s=once(s,'pair=pairable && !adjacent && count==3;next=g;','pair=pairable && !adjacent && count==3;')
    if renew_head:
        assert shared_gap
        # The normal packet can begin behind a tile; after successful
        # arbitration/send it becomes the last map head. Use that completed
        # operation for the next packet, not the stale entry-time head.
        s=once(s,'s->plan->window && s->plan->window->last[0]==2 && s->plan->window->last[1]==2;\n bool pair=pairable && s->map_pair683;',
            's->plan->window;\n bool pair=pairable && s->map_pair683 && s->plan->window->last[0]==2 && s->plan->window->last[1]==2;')
    if pending_first:
        assert renew_head
        s=once(s,'pair=pairable && !adjacent && count==3;',
            '''/* A ready, already owned tile retains producer priority. Only
   * an empty producer or completed receipt can lend its next query slot. */
  pair=pairable && !adjacent && count==3 && !s->plan->bulk_pending;''')
    p.write_text(s,newline='\n')
    (out/'recipe687.json').write_text(json.dumps(dict(base=proof['firmware'],shared_gap=shared_gap,renew_head=renew_head,pending_first=pending_first,changed={p.name:sha(p)},
        bound=('Warm successful normal map send renews ownership; prior head is required only for initial frontier handoff. '
               if renew_head else 'Warm entry-time map head only. ')+
              'Pair of exact contiguous192B packets. No wire/CRC/credit change, no cold/row-frontier expansion.'),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--shared-gap',action='store_true')
    p.add_argument('--renew-head',action='store_true')
    p.add_argument('--pending-first',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,a.shared_gap,a.renew_head,a.pending_first)
