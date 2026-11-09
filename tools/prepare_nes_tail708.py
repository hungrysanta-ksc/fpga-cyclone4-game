"""Move immutable section5 prefix before final map, preserving final tables/SEAL.

No wire ABI, producer priority, credit, receipt or display ownership change.
scroll moves only scroll; prefix also moves padding. This separates short
receive and long restore cost. initialized keeps the original packet order.
Both retain the section5 table tail directly before the existing SEAL barrier.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def prepare(base,out,mode):
    assert sha(base/'obj-nes-100/firmware.stm')=='b5c42303c6831190f77c95367bd1640e3e575caea8e3909af27e2587ad5eb600'
    s=(base/'nes_native_sink165.c').read_text()
    if mode=='initialized':
        # Every transmitted byte is written explicitly: header0..15 and the
        # exact payload16..16+n. Keep the ACK zeroed for failure diagnostics.
        s=once(s,'uint8_t b[256]={0},ack[12]={0};','uint8_t b[256],ack[12]={0};')
        out.mkdir(parents=True,exist_ok=False)
        (out/'nes_native_sink165.c').write_text(s,encoding='utf8',newline='\n')
        (out.parent/(out.name+'-recipe.json')).write_text(json.dumps(dict(stage=708,mode=mode,base=sha(base/'nes_native_sink165.c'),changed=sha(out/'nes_native_sink165.c'),scope='Remove only redundant TX initialization; original order and ACK initialization retained.'),indent=2)+'\n')
        return
    a=s.index(' if(!map527(s,p,r->map_upload,false))')
    b=s.index('  /* Canonical raw CHR',a)
    maps=s[a:b];s=s[:a]+s[b:]
    a=s.index(' bool same=same635(s,p);');b=s.index(' if(!span(s,5,0,p->hdma',a)
    ordinary=s[a:b];s=s[:a]+s[b:]
    if mode in ('scroll','credit'):
        anchor=' if(!span(s,5,0,p->hdma,p->hdma_size))return false;'
        s=once(s,anchor,anchor+'\n'+maps+ordinary)
        if mode=='credit':
            # Do not precede the first accepted map or consume its reserved
            # adjacent-map offer. The usual room policy keeps a bulk slot.
            s=once(s,anchor,''' bool early708=s->plan && s->plan->bank_history==2 && s->plan->window &&
     s->plan->window->last[1]==2 && !s->map_pair683 &&
     (uint16_t)(s->plan->window->sent-s->plan->window->retired)<3;
 if(early708 && !span(s,5,0,p->hdma,p->hdma_size))return false;''')
            anchor=' if(p->patch_count){\n  /* Section5'
            s=once(s,anchor,' if(!early708 && !span(s,5,0,p->hdma,p->hdma_size))return false;\n'+anchor)
        out.mkdir(parents=True,exist_ok=False)
        (out/'nes_native_sink165.c').write_text(s,encoding='utf8',newline='\n')
        (out.parent/(out.name+'-recipe.json')).write_text(json.dumps(dict(stage=708,mode=mode,base=sha(base/'nes_native_sink165.c'),changed=sha(out/'nes_native_sink165.c'),scope=__doc__),indent=2)+'\n')
        return
    s=once(s,' if(!span(s,5,0,p->hdma,p->hdma_size))return false;',
           ' /*708 The validated immutable prefix can use existing ordinary credit\n'
           '  * while tile/ROM work continues. Final table tail still precedes SEAL. */\n'
           ' unsigned offset=p->hdma_size;\n'
           ' if(!span(s,5,0,p->hdma,p->hdma_size))return false;')
    s=once(s,'static const uint8_t zero[240]={0};unsigned offset=p->hdma_size;',
           'static const uint8_t zero[240]={0};')
    assert mode=='prefix'
    anchor='  /* Read the enclosing object representation'
    pos=s.index(anchor)
    s=s[:pos]+' }\n'+maps+ordinary+' if(p->patch_count){\n'+s[pos:]
    out.mkdir(parents=True,exist_ok=False)
    (out/'nes_native_sink165.c').write_text(s,encoding='utf8',newline='\n')
    (out.parent/(out.name+'-recipe.json')).write_text(json.dumps(dict(stage=708,mode=mode,base=sha(base/'nes_native_sink165.c'),changed=sha(out/'nes_native_sink165.c'),scope=__doc__),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--mode',choices=['initialized','scroll','credit','prefix'],default='prefix')
    a=p.parse_args();prepare(a.base,a.out,a.mode)
