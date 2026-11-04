"""Exercise cross-page slots, palette changes and real exception records on the linked planner."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from check_nes_game478 import Machine
from check_nes_wire600 import ROOT, pin, read, sha
from analyze_nes_wire600 import Receiver, display_guards
from nes_transfer512 import legacy_packets


def cases(geom):
    raster=1056*2+224+128*8+128*4
    counts=struct.unpack_from('<6H',geom,5728)
    assert counts[3]==0
    normal=[y for y in range(224) if not (struct.unpack_from('<Q',geom,raster+8*y)[0]>>49)&1]
    y=normal[0]
    row=(geom[2112+y]>>3)*33
    unique=list(dict.fromkeys(x&8191 for x in struct.unpack_from('<%dH'%counts[0],geom)))
    assert len(unique)>=3
    for mode in ('page31','wrap63','exception_column','exception_zero'):
        b=bytearray(geom)
        start=31 if mode=='page31' else 63
        for line in normal:
            at=raster+8*line;v=struct.unpack_from('<Q',b,at)[0]
            struct.pack_into('<Q',b,at,(v&~1055)|(start&31)|((start&32)<<5))
        for x in range(33):
            struct.pack_into('<H',b,2*(row+x),unique[x&1]|((x&3)<<13))
        if mode.startswith('exception'):
            x=4 if mode=='exception_column' else 0
            struct.pack_into('<I',b,raster-512,(unique[2]<<19)|((y*33+x)<<6))
            struct.pack_into('<H',b,5728+6,1)
        yield mode,bytes(b)


def corpus(args,palette):
    pins=read(args.data/'result.json')
    assert pins['passed']
    old,new=(Machine(src,palette) for src in (args.control,args.candidate))
    frames=[]
    for seq,g in enumerate(range(905,976),1):
        files=[args.data/f'frame{g}.{ext}' for ext in ('geometry','raw')]
        for f in files:
            pin(f,pins['evidence_files'][f.name])
        b,raw=(f.read_bytes() for f in files)
        packets,_,_=legacy_packets(b,raw,g)
        x,y=(m.frame(packets,b,raw,g,seq) for m in (old,new))
        assert x['state_sha256']==y['state_sha256'] and x['plans']==y['plans'],g
        frames.append(dict(generation=g,bank=y['bank'],plans=len(y['plans']),state=y['state_sha256'],
                           old=x['planner_instructions'],new=y['planner_instructions']))
    args.report.write_text(json.dumps(dict(frames=frames,control=sha(args.control/'obj-nes-100/firmware.stm'),
        candidate=sha(args.candidate/'obj-nes-100/firmware.stm')),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('control','candidate','data','report'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--corpus',action='store_true')
    a=p.parse_args(); g=954
    geom=a.data/'frame954.geometry';raw=a.data/'frame954.raw'
    for f in (geom,raw):
        pin(f,read(ROOT/'analysis/body581-verification.json')['inputs'][f.name])
    raw=raw.read_bytes();results=[]
    palette=re.search(r'\{(.+?)\}',(a.control/'nes_palette165.inc').read_text())[1]
    if a.corpus:
        corpus(a,struct.pack('<64H',*map(int,palette.split(','))))
        raise SystemExit
    for label,b in cases(geom.read_bytes()):
        packets,_,_=legacy_packets(b,raw,g)
        outputs=[]
        for src in (a.control,a.candidate):
            m=Machine(src,struct.pack('<64H',*map(int,palette.split(','))))
            r=m.frame(packets,b,raw,g,1)
            outputs.append(r)
        old,new=outputs
        for field in ('state_sha256','plans','tiles','bank','source_SPI_calls'):
            assert old[field]==new[field],(label,field)
        results.append(dict(case=label,geometry_sha256=hashlib.sha256(b).hexdigest(),state=new['state_sha256'],
                            plans=len(new['plans']),control_instructions=old['planner_instructions'],
                            candidate_instructions=new['planner_instructions']))
    packets,_,_=legacy_packets(geom.read_bytes(),raw,g)
    m=Receiver(a.candidate,bytes(128))
    m.start(packets);m.bad_crc=True
    assert not m.pump() and m.index==0 and m.state_value()==5
    m.start(packets)
    for _ in range(6):
        assert m.pump()
    assert m.index==6
    addr=0x20013000;token=(m.start_token+6)&65535
    abort=struct.pack('>HHQ',0xe002,g,0)
    m.u.mem_write(addr,abort)
    assert m.call('nes_native165_packet',[m.state,token,addr,len(abort)]) and m.state_value()==0
    m.u.mem_write(addr,packets[-1])
    assert not m.call('nes_native165_packet',[m.state,token+1,addr,len(packets[-1])])
    m.receive(packets,geom.read_bytes(),raw,g)
    a.report.write_text(json.dumps(dict(control=sha(a.control/'obj-nes-100/firmware.stm'),
        candidate=sha(a.candidate/'obj-nes-100/firmware.stm'),cases=results,
        receive_guards=['bad CRC no POP','ABORT after six POPs','late COMMIT rejected','cold full receive'],
        display_guards=display_guards(a.candidate,g,packets)),indent=2)+'\n')
