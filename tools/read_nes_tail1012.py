"""Decode CRC-qualified cumulative credit observations and align them with the display clock."""
import argparse
import json
import struct
from pathlib import Path
from read_nes_display1010 import ARM_TICK, HEADER, MS, ROW, decode_rows

CAPACITY = 80
TRACE = struct.Struct("<I6H")
PACKET = struct.Struct("<2B6H")
OFFSET = (HEADER.size+CAPACITY*ROW.size+2+3) & ~3
STRIDE = TRACE.size+64*PACKET.size
SIZE = OFFSET+3*STRIDE+ROW.size


def decode(data,edition=1012):
    if edition not in (1012,1014,1023,1024,1025) or len(data)!=SIZE:
        raise ValueError("unsupported tail log edition or length")
    report=decode_rows(data,edition,CAPACITY)
    samples=[]
    for slot,(bg,tiles,chunks,kind,length) in enumerate(((532,3,2,1,64),(529,1,1,0,16))):
        start=OFFSET+slot*STRIDE
        base,gen,count,credits,first_sent,e0,tick=TRACE.unpack_from(data,start)
        if not count:
            continue
        rows=[r for r in report["rows"] if r["generation"]==gen and r["tick"]==tick]
        if len(rows)!=1 or "invalid" in rows[0] or not 1<=count<=64 or count!=credits:
            raise ValueError("incomplete trace or missing display identity")
        r=rows[0]
        desc=bytes.fromhex(r["descriptor_hex"])
        if edition==1025:
            if not (5500<=tick<5750 if slot==0 else 5750<=tick<6000):
                raise ValueError("packet trace outside its sampling window")
        elif (r["BG"],r["OBJ"],r["map"],r["tiles"],r["chunks"],*struct.unpack_from("<BHH",desc,1))!=(bg,18,23,tiles,chunks,kind,length,0):
            raise ValueError("workload mismatch")
        packets=[]
        last_sent=last_credit=0
        for seq in range(count):
            op,section,offset,payload,ready,issue,sent,credit=PACKET.unpack_from(data,start+TRACE.size+seq*PACKET.size)
            if not last_sent<=ready<=issue<=sent<=credit<=e0<65535 or credit<last_credit:
                raise ValueError("invalid ARM packet timestamps")
            packets.append(dict(seq=seq,op=op,section=section,offset=offset,payload=payload,
                                ready=ready,issue=issue,sent=sent,first_credit_observed=credit))
            last_sent,last_credit=sent,credit
        if packets[0]["op"]!=1 or packets[-1]["op"]!=3:
            raise ValueError("missing BEGIN or SEAL")
        s=dict(slot=slot,generation=gen,tick=tick,base_CYCCNT=base,first_sent=first_sent,e0=e0,packets=packets)
        # ARM and FPGA do not share an origin. The age bounds also include query overhead.
        if "final_ACK_to_ARM_E0_ms" in r and "last_tile_to_show_ms" in r:
            lo,hi=r["final_ACK_to_ARM_E0_ms"]
            fpga=(r["final_ACK"]-r["show"])*MS+r["last_tile_to_show_ms"]
            s["last_tile_after_begin_ms_bounds"]=[e0*ARM_TICK-fpga-hi-MS-ARM_TICK,e0*ARM_TICK-fpga-lo+MS+ARM_TICK]
            first,last=s["last_tile_after_begin_ms_bounds"]
            for packet in packets:
                # ARM times are differences of truncated stamps. Include one tick at each limit.
                packet["issue_after_last_tile_ms_bounds"]=[(packet["issue"]-1)*ARM_TICK-last,
                                                           (packet["issue"]+1)*ARM_TICK-first]
        samples.append(s)
    return dict(**report,arm_tick_ms=ARM_TICK,samples=samples)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log",type=Path)
    parser.add_argument("--edition",type=int,choices=(1012,1014,1023,1024,1025),default=1012)
    args=parser.parse_args()
    print(json.dumps(decode(args.log.read_bytes(),args.edition),indent=2))
