"""Build bounded queue pacing or bulk-prioritized map issue experiments."""
import argparse
from pathlib import Path
import shutil
from check_nes_wire600 import ROOT,pin,read
from nes_raw506 import once


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--map-only',action='store_true')
    p.add_argument('--bulk-map',action='store_true')
    p.add_argument('--obj-map',action='store_true')
    a=p.parse_args()
    pin(a.base/'src/obj-nes-100/firmware.stm',read(ROOT/'analysis/quiet608-palette.json')['ARM'])
    shutil.copytree(a.base,a.out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    if a.bulk_map or a.obj_map:
        f=a.out/'src/nes_plan_service200.c'
        # In FLUSH, flag 2 is rejected by poll; flag 1 returns E9 above.
        # The only other nonzero flag is submitted/repeated bulk (4).
        # OBJ-only preserves BG supply opportunities without frame IDs.
        condition='p->bulk[1]' if a.obj_map else 'flags==4'
        s=once(f.read_text(),'if(flags==0 && (p->quiet_map||allow_payload)){',
               f'if((flags==0 || ({condition} && p->quiet_map)) && (p->quiet_map||allow_payload)){{')
        f.write_bytes(s.encode())
        raise SystemExit
    f=a.out/'src/nes_sink_window184.c';s=f.read_text()
    if a.map_only:
        s=once(s,'static bool credit(struct nes_sink_window184 *s){',
                 'static bool credit(struct nes_sink_window184 *s){\n unsigned limit=s->last[1]==2?1:4;')
        s=once(s,'if((uint16_t)(s->sent-s->retired)<4)return true;',
                 'if((uint16_t)(s->sent-s->retired)<limit)return true;')
        s=once(s,'bool done=(uint16_t)(s->sent-s->retired)<4;',
                 'bool done=(uint16_t)(s->sent-s->retired)<limit;')
    else:
        s=once(s,'if((uint16_t)(s->sent-s->retired)<4)return true;',
                 'if(s->sent==s->retired)return true;')
        s=once(s,'bool done=(uint16_t)(s->sent-s->retired)<4;',
                 'bool done=s->sent==s->retired;')
    f.write_bytes(s.encode())
