"""Replay the 657 firmware, client and DMA schedule with the other plane filled on a BG miss."""
import runpy
from pathlib import Path
from unittest.mock import patch
from nes_raw506 import once

run_module=runpy.run_module

def execute(name,*args,**kwargs):
    if name!="test_nes_board611":
        return run_module(name,*args,**kwargs)
    path=Path(__file__).with_name(name+".py")
    src=once(path.read_text(),"                line[addr%16]=expected","""                line[addr%16]=expected
                if kind==0:
                    line[(addr%16)^8]=native_chr[addr^8]""")
    if emit:
        src=once(src,"pending.extend((g,kind,slot,addr,tile[j]) for j,addr in lanes(q))","""pair=kind==0 and q[8:24]==bytes(i//2 for i in range(16)) and q[24:40]==bytes([255])*16
                pending.extend((g,kind,slot,addr,tile[j],pair) for j,addr in lanes(q))""")
        src=once(src,"g,kind,slot,addr,expected=pending.popleft()","g,kind,slot,addr,expected,pair=pending.popleft()")
        src=once(src,"if a.reference_cache or kind==0:", """if kind==0:
            if pair and addr&8:
                assert native_chr[addr]==expected
                link.allocations.append(dict(requested=t,grant=t,response=t))
                link.phases[g].setdefault('cache611',[]).append([kind,addr,t,t,t,'BG_peer'])
                return t
            delay=1
        elif a.reference_cache:""")
    if one_word:
        src=once(src,"if tag!=addr//16:tag=addr//16;line={}","tag=addr//16;line={}")
    ns=dict(__file__=str(path),__name__="__main__",native_chr=rom.read_bytes()[-131072:])
    exec(compile(src,str(path),"exec"),ns)

if __name__=="__main__":
    import argparse,sys
    from check_nes_fault641 import digest,evidence
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument("--game",type=Path,required=True)
    parser.add_argument("--one-word",action="store_true");parser.add_argument("--emit",action="store_true");opts,rest=parser.parse_known_args();emit=opts.emit;rom=opts.game;one_word=opts.one_word
    assert digest(rom)==evidence("mmc480-verification.json")["live_functional"]["rom_sha256"]
    sys.argv[1:]=rest
    with patch.object(runpy,"run_module",execute):
        runpy.run_module("test_nes_direct653",run_name="__main__")
