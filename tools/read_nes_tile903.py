"""Decode the ARM descriptor and the independently timed, consumed FPGA tile."""
import json
import struct
import sys
from pathlib import Path

from read_nes_frame900 import HEADER, TICK, PERIOD, BLANK

ROW=struct.Struct('<6H4B26s12s')
STAGES=('ready','visible','E8_snapshot','E1_opcode','head','show')


def decode(path):
    data=path.read_bytes()
    magic,edition,mode,count,d0,d1,size,capacity=HEADER.unpack_from(data)
    if (magic,edition,size,capacity)!=(0x9001,903,ROW.size,151) or mode>3 or count>capacity or len(data)!=16+size*count:
        raise ValueError('invalid MMC903 file header or length')
    rows=[]
    for tick,g,bg,ia,ea,probe,obj,dirty,valid,bank,wire,d in ROW.iter_unpack(data[16:]):
        r=dict(tick=tick,generation=g,bank=bank,BG=bg,OBJ=obj,map=dirty)
        rows.append(r)
        if bank>1 or not (3000<=tick<3500 if mode==1 else 5500<=tick<6000) or valid!=(3 if mode==3 else 7):
            r['invalid']='window or ARM input/final ACK';continue
        if mode==3:
            if any(wire):r['invalid']='unexpected CONTROL response'
            continue
        flags=wire[2]
        if wire[1]!=0x93 or flags not in (3,7) or int.from_bytes(wire[3:5],'little')!=g:
            r['invalid']='FPGA generation or final ACK';continue
        stamps=struct.unpack_from('<8H',wire,5)
        ages=[(stamps[7]-v)&65535 for v in stamps]
        span=(ages[0]-ages[6])*TICK
        vb=round(span/PERIOD)
        if vb<1 or abs(span-vb*PERIOD)>BLANK:
            r['invalid']='previous display or wrap';continue
        r['VBlanks']=vb
        r['probe_ms']=round(probe*TICK,3)
        r['ARM_from_previous_show_ms']={
            key:[round((ages[0]-age-probe-2)*TICK,3),round((ages[0]-max(0,age-1))*TICK,3)]
            for key,age in [('input',ia),('E0',ea)]}
        if flags==3:
            if any(d):r['invalid']='stale ARM tile'
            continue
        ready,kind,length,offset,gen,token=struct.unpack('<BBHHHI',d)
        if (ready!=1 or kind!=wire[25] or kind>1 or gen!=g or
                token!=int.from_bytes(wire[21:25],'little') or not 0<length<=2048 or length%(16<<kind)):
            r['invalid']='tile identity or length';continue
        # Separate RAM slots may round events straddling the same 512-clock
        # boundary to adjacent ticks. Report the signed difference unchanged.
        if any(a+1<b for a,b in zip(ages[1:6],ages[2:7])):
            r['invalid']='stale or reversed timestamp';continue
        r.update(token=token,kind=('BG','OBJ')[kind],bytes=length,offset=offset,
                 from_previous_show_ms={k:round((ages[0]-v)*TICK,3) for k,v in zip(STAGES,ages[1:7])},
                 adjacent_ms=[round((a-b)*TICK,3) for a,b in zip(ages[1:6],ages[2:7])])
    return dict(mode=mode,dropped=[d0,d1],rows=rows)


if __name__=='__main__':
    print(json.dumps(decode(Path(sys.argv[1])),indent=2))
