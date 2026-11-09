"""Renew the stopped-tick step counter once per actual step, not every guard."""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    f=a.base/'nes_native_runtime165.c'
    assert sha(f)=='ce83ae11d1e9b1c84d1f8a32333fb819b52c6f537ef5cd9d0ff01dc90f4a54ab'
    s=f.read_text();start=s.index(' uint32_t now=s->ticks(s->ctx);');end=s.index(' if(!s->service(s->ctx))',start)
    block=s[start:end];s=s[:start]+s[end:]
    s=once(s,' /* Backstop if the external tick stops; not an elapsed-time estimate. */',
        ' /* Only step increments this counter. Keep per-transaction service,\n  * clock faults and ownership checks in guard(), without redundant reads. */\n'+block+' /* Backstop if the external tick stops; not an elapsed-time estimate. */')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/f.name).write_text(s,newline='\n')
    (a.out.parent/'prepare-arm694.json').write_text(json.dumps(dict(base=sha(f),candidate=sha(a.out/f.name),scope=__doc__),indent=2)+'\n')
