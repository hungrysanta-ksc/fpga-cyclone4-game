"""Decode only the selected, complete token sequence and its source tiles."""
import json
import struct
import sys
from pathlib import Path
from read_nes_frame900 import HEADER

ROW=struct.Struct('<6H4B16s12s')
CAP=124
SIZE=16+CAP*ROW.size+4+320*8
MS=32768/84000

def decode(path,expected_edition=905):
    data=path.read_bytes()
    magic,edition,mode,count,d0,d1,size,capacity=HEADER.unpack_from(data)
    if expected_edition not in (905,907) or (magic,edition,size,capacity,len(data))!=(
            0x9001,expected_edition,ROW.size,CAP,SIZE+2*(expected_edition==907)) or mode>3 or count>CAP:
        raise ValueError('wrong supply trace edition or truncated SD write')
    selected,score=struct.unpack_from('<2H',data,16+CAP*size)
    if selected>count:raise ValueError('invalid detail index')
    table=memoryview(data)[16+CAP*size+4:]
    rows=[]
    def word(a,i):return int.from_bytes(a[i:i+2],'little')
    for i in range(count):
        tick,g,bg,ia,ea,probe,obj,dirty,flags,bank,h,desc=ROW.unpack_from(data,16+i*size)
        r=dict(tick=tick,generation=g,BG=bg,OBJ=obj,map=dirty,bank=bank,
               probe_total_ms=round(probe*MS/64,3))
        rows.append(r)
        if bank>1 or not (3000<=tick<3500 if mode==1 else 5500<=tick<6000) or flags!=(3 if mode==3 else 7):
            r['invalid']='window, input, ACK, or trace transaction';continue
        if ea>ia:
            r['invalid']='final ACK before input completion';continue
        r['input_to_final_ACK_ms']=round((ia-ea)*MS/64,3)
        if mode==3:continue
        if h[1]!=0x95 or word(h,2)!=g:
            r['invalid']='trace generation';continue
        nt,nc=h[4:6]
        origin,anchor,last=struct.unpack_from('<3H',h,6)
        token=int.from_bytes(h[12:16],'little')
        def elapsed(v):return round(((v-origin)&1023)*MS,3)
        r.update(tiles=nt,chunks=nc,E9_to_query_ms=elapsed(anchor))
        if ia==65535 or ia>=65472:
            r['invalid']='clock ambiguity';continue
        # ARM sampled before the SPI query. The total query duration is a
        # conservative bound, including optional detail readback.
        arm_to_e9=ia*MS/64-elapsed(anchor)
        r['input_to_first_E9_ms_bounds']=[round(arm_to_e9-MS,3),round(arm_to_e9+MS+r['probe_total_ms'],3)]
        if nc:
            ready,kind,n,offset,gen,tok=struct.unpack('<BBHHHI',desc)
            if not (ready==1 and kind<=1 and gen==g and tok==token and 0<n<=2048 and n%(16<<kind)==0):
                r['invalid']='ARM descriptor / FPGA token';continue
            r.update(last_token=tok,last_kind=kind,last_bytes=n,last_offset=offset,E9_to_last_publish_ms=elapsed(last))
        if selected!=i+1:continue
        if not (0<nc<63 and 0<nt<255 and r.get('last_kind')==1):
            raise ValueError('incomplete selected generation')
        pos=0;chunks=[]
        for j in range(nc):
            rec=struct.unpack_from('<I',table,(256+j)*8)[0]
            tok=token-nc+1+j
            k=(rec>>19)&1;bank_id=(rec>>20)&1;units=(rec>>11)&255
            if rec>>21!=tok%2048 or bank_id!=(tok-1)%2 or not units or units%(1<<k):
                raise ValueError('return identity, bank, or tile length mismatch')
            tiles=[]
            for _ in range(units>>k):
                if pos>=nt:raise ValueError('too many consumed tiles')
                v=int.from_bytes(table[pos*8:pos*8+5],'little');pos+=1
                n=v>>30
                t=dict(grants=n)
                if n:
                    a,b,c=[(v>>s)&1023 for s in (0,10,20)]
                    t.update(first_request_ms=elapsed(a),first_grant_ms=elapsed(b),last_grant_ms=elapsed(c))
                    if not (t['first_request_ms']<=t['first_grant_ms']<=t['last_grant_ms']<=elapsed(rec&1023)):
                        raise ValueError('request/grant/return order or timestamp wrap')
                tiles.append(t)
            chunks.append(dict(token=tok,bank=bank_id,kind=['BG','OBJ'][k],bytes=units*16,
                               returned_after_E9_ms=elapsed(rec&1023),tiles=tiles))
            misses=[t for t in tiles if t['grants']]
            chunks[-1].update(ROM_grants=sum(t['grants'] for t in tiles),
                first_ROM_request_ms=misses[0]['first_request_ms'] if misses else None,
                last_ROM_grant_ms=misses[-1]['last_grant_ms'] if misses else None,
                longest_first_grant_wait_ms=max((round(t['first_grant_ms']-t['first_request_ms'],3)
                                                 for t in misses),default=0))
            if j and chunks[-2]['returned_after_E9_ms']>chunks[-1]['returned_after_E9_ms']:
                raise ValueError('bank returns out of order')
        if pos!=nt or chunks[-1]['bytes']!=r['last_bytes'] or chunks[-1]['kind']!='OBJ':
            raise ValueError('tile stream and validated ARM descriptor disagree')
        r['detail']=chunks
    return dict(mode=mode,dropped=[d0,d1],selected=selected,rows=rows,
                displayed55=struct.unpack_from('<H',data,SIZE)[0] if edition==907 else None)

if __name__=='__main__':print(json.dumps(decode(Path(sys.argv[1])),indent=2))
