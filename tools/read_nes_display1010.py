"""Decode the 55–60 s display observer without equating FPGA retirement and ARM E0."""
import argparse
import json
import struct
from pathlib import Path

from read_nes_frame900 import HEADER
from read_nes_supply905 import CAP, MS

ROW=struct.Struct('<6H4B32s12s')
ARM_TICK=512/84000

def kirby_boundaries(header, origin, published, query, acquisition_ms):
    # Input precedes the first E9. An acquisition spanning an 8-bit wrap
    # could alias two occurrences of the same stamp; do not guess an epoch.
    if acquisition_ms >= 255*MS:
        return {'unresolved': '8-bit timestamp window'}
    span=(query-origin)&1023
    if span>=255 or span*MS>acquisition_ms+MS:
        return {'unresolved': 'query and input windows disagree'}
    start,done,end,head=header[26:30]
    stamps=dict(plan=start,done=done,END=end,head_E8=head)
    req,grant=bool(header[9]&64),bool(header[9]&128)
    if req!=grant:
        return {'unresolved': 'incomplete foreground transaction'}
    if req:
        stamps['first_request'],stamps['first_grant']=header[10:12]
    age={name:(stamp-origin)&255 for name,stamp in stamps.items()}
    age['writer']=(published-origin)&1023
    order=['plan']+(['first_request','first_grant'] if req else [])+['done','END','writer','head_E8']
    if not all(age[a]<=age[b] for a,b in zip(order,order[1:])) or age['head_E8']>span:
        return {'unresolved': 'event order or frame association'}
    return {'foreground_read':req,'ticks_from_first_E9':age,
            'ms_from_first_E9':{k:round(v*MS,4) for k,v in age.items()}}


def decode(path):
    data=path.read_bytes()
    if len(data)!=HEADER.size+CAP*ROW.size+2:
        raise ValueError('incomplete frame log')
    return decode_rows(data,1010,CAP)

def decode_rows(data,expected_edition,expected_capacity):
    magic,edition,mode,n,d0,d1,size,capacity=HEADER.unpack_from(data)
    if (magic,edition,size,capacity)!=(0x9001,expected_edition,ROW.size,expected_capacity) or n>capacity or mode>3:
        raise ValueError('wrong trace header')
    rows=[]
    for i in range(n):
        tick,g,bg,ia,ea,probe,obj,dirty,valid,bank,h,desc=ROW.unpack_from(data,16+i*ROW.size)
        row=dict(tick=tick,generation=g,BG=bg,OBJ=obj,map=dirty,bank=bank)
        rows.append(row)
        start = 3000 if mode==1 or (edition in (1025,1027,1028) and mode in (0,3)) else 5500
        stop = 3500 if mode==1 else 6000
        if not start<=tick<stop or bank>1 or ea>ia:
            row['invalid']='window, bank or ARM age'
            continue
        if mode==3:
            if valid!=3 or any(h):
                row['invalid']='control unexpectedly queried'
            continue
        if (valid!=7 or h[1]!=0xa1 or int.from_bytes(h[2:4],'little')!=g or
            h[30:]!=bytes((15,165)) or bool(h[5])!=bool(desc[0]) or
            (h[5] and h[12:16]!=desc[8:12])):
            row['invalid']='incomplete or mismatched record'
            continue
        prev,seal,dma,show,ack=struct.unpack_from('<5H',h,16)
        if not (prev<=dma<=show<=ack and prev<=seal<=show):
            row['invalid']='inconsistent clocks'
            continue
        row.update(previous_show=prev,SEAL=seal,last_DMA=dma,show=show,final_ACK=ack,
                   input_to_E0_ms=(ia-ea)*ARM_TICK,tiles=h[4],chunks=h[5],
                   descriptor_hex=desc.hex(),
                   spacing_ms=(show-prev)*MS,seal_to_show_ms=(show-seal)*MS,
                   dma_to_show_ms=(show-dma)*MS)
        # The SPI anchor is ten bits. A long ARM acquisition could span a wrap.
        # Exclude saturated ages and defer costs from cross-clock classification.
        if max(ia,ea,probe)==65535 or (ia+probe+2)*ARM_TICK>=(1024-1)*MS:
            continue
        origin,query,last=struct.unpack_from('<3H',h,6)
        if edition==1027:
            origin,query,last=(h[6+i]|(((h[9]>>(i*2))&3)<<8) for i in range(3))
            if h[5]:
                row['last_slot_run']=kirby_boundaries(h,origin,last,query,(ia+probe+2)*ARM_TICK)
        age=(query-ack)&1023
        supply=(last-origin)&1023
        after=(query-last)&1023
        if h[5] and ((query-origin)&1023)==after+supply:
            row['supply_ms']=supply*MS
            if after>=((query-show)&1023):
                row['last_tile_to_show_ms']=((show-last)&1023)*MS
        lo=max(0,(age-1)*MS-(ea+probe+2)*ARM_TICK)
        hi=(age+1)*MS-ea*ARM_TICK
        if hi>=lo:
            row['final_ACK_to_ARM_E0_ms']=[lo,hi]
    return dict(rows=rows,dropped=[d0,d1],displayed55=struct.unpack_from('<H',data,HEADER.size+capacity*ROW.size)[0],
                fpga_tick_ms=MS)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('log',type=Path)
    print(json.dumps(decode(parser.parse_args().log),indent=2))
