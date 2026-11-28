"""Decode the paired first-block and four-batch hardware observer, referenced to previous show."""
import argparse
import json
import struct
from pathlib import Path

from read_nes_display1010 import ARM_TICK, MS
from read_nes_ingress1029 import CAPACITY, HEADER, INGRESS, OFFSET, ROW, SIZE


def sample(data, i, edition=1034):
    first_tick=100 if edition==1054 else 3000
    if edition==1054:
        edition=1035  # The CHR-ROM FPGA event layout is identical.
    tick, gen, bg, ia, ea, probe, obj, dirty, valid, bank, h, desc = ROW.unpack_from(data, HEADER.size+i*ROW.size)
    result = dict(tick=tick, generation=gen)
    token = int.from_bytes(desc[8:], 'little')
    if (valid != 7 or not first_tick <= tick < 6000 or bank > 1 or ea > ia or max(ia, probe) == 65535
            or h[1] != (0xa5 if edition==1035 else 0xa4) or h[30:] != bytes((15,165)) or h[2:4] != struct.pack('<H',gen)
            or not desc[0] or desc[6:8] != h[2:4] or h[12:16] != desc[8:]):
        raise ValueError('incomplete identity or observation')
    first, end, last_d2, first_duration, retire, packed, ingress_gen, blocks = INGRESS.unpack_from(data, OFFSET+i*INGRESS.size)
    ready_age, size = divmod(packed, 1<<24)
    duration = (end-first) & 0xffffffff
    d2_offset = (last_d2-first) & 0xffffffff
    if (ingress_gen != gen or not 1 <= blocks <= size <= 256*blocks or ready_age>127
            or not 0 < first_duration <= d2_offset <= duration < 84000000):
        raise ValueError('invalid checked D1/D2/D0 record')
    if edition==1034 and not 0 < retire <= duration:
        raise ValueError('invalid retirement time')
    prev, seal = struct.unpack_from('<HH',h,16)
    show = int.from_bytes(h[22:24],'little')
    ack = int.from_bytes(h[28:30],'little')
    origin = h[6] | ((h[21]&3)<<8)
    query = h[7] | (((h[21]>>2)&3)<<8)
    n = (h[21]>>4)&7
    if not prev <= seal <= show <= ack:
        raise ValueError('display timestamps wrap or are unordered')
    q = ack-prev + ((query-ack)&1023)
    span = (query-origin)&1023
    start = q-span
    if not (0 <= start <= seal-prev <= ack-prev <= q < 1023
            and span < 255 and span*MS <= (ia+probe+2)*ARM_TICK+MS):
        raise ValueError('unresolved clock alignment')
    after_d0 = [(q-1)*MS-(ia+probe+2)*ARM_TICK,(q+1)*MS-ia*ARM_TICK]
    d1 = [t-duration/84000 for t in after_d0]
    # FPGA latches the D1 opcode during the first SPI call. Before saturation
    # this gives a conservative ready interval even without a shared clock.
    ready = [None if ready_age==127 else d1[0]-(ready_age+1)*MS,
             d1[1]+first_duration/84000-ready_age*MS]
    if edition==1035:
        ready[1]=d1[1]+first_duration/84000-max(0,ready_age-1)*MS+0.0002 if ready_age<127 else None
    result.update(BG=bg, OBJ=obj, map=dirty, tiles=h[4], chunks=h[5], bank=bank,
                  first_block_ready_ms=ready, first_D1_call_ms=d1,
                  last_checked_D2_ms=[t+d2_offset/84000 for t in d1], last_confirmed_D0_ms=after_d0,
                  first_E9_command_tick=start, SEAL_tick=seal-prev, show_tick=show-prev, final_ACK_tick=ack-prev)
    if edition==1035 and blocks>=3:
        if retire & 0x8080 != 0x8080:
            raise ValueError('missing checked capture interval')
        a,b=retire&127,(retire>>8)&127
        lag=retire>>16
        result['previous_commit_D2_response_ms']=None if lag==65535 else [d1[0]-(lag+1)*ARM_TICK,d1[1]-lag*ARM_TICK]
        result.update(release_to_capture_ticks=a,capture_to_offer_ticks=b)
        def earlier(interval,count):
            if count==127 or None in interval:
                return [None,None]
            # One coarse tick and the synchronizer/one-edge sampling skew.
            return [interval[0]-(count+1)*MS-0.0002,interval[1]-max(0,count-1)*MS+0.0002]
        cap=earlier(ready,b)
        result.update(capture_start_ms=cap,previous_collector_release_ms=earlier(cap,a))
    if not (1 <= n <= 5 and 1 <= h[5] <= 4 and (edition==1035 or h[21]&128)):
        return dict(**result, detail_unavailable='insufficient or excess events')
    def relative(byte):
        age=(byte-origin)&255
        if age>span or start+age>seal-prev:
            raise ValueError('batch event outside captured generation')
        return start+age
    accepts = [relative(v) for v in h[8:8+min(n,4)]]
    returns = [relative(v) for v in h[24:24+h[5]]]
    if accepts!=sorted(accepts) or returns!=sorted(returns) or token<h[5]-1:
        raise ValueError('invalid batch ordering')
    if edition==1035:
        if n!=len(returns) or any(w>r for w,r in zip(accepts,returns)):
            raise ValueError('unpaired bank publication and retirement')
        result['banks']=[dict(token=token-len(returns)+i+1,writer_tick=w,return_tick=r)
                         for i,(w,r) in enumerate(zip(accepts,returns))]
        if n>=2:
            boundary=max(returns[0],accepts[1])
            result['second_bank_after_first_return_ticks']=dict(
                waiting_for_publication=boundary-returns[0],published_head_to_return=returns[1]-boundary)
        return result
    group = relative(h[20])
    if group<accepts[0] or group>returns[-1]:
        raise ValueError('invalid plan timing')
    # SPI packets and returned tile groups have independent boundaries and counts.
    return dict(**result, E9_accept_ticks=accepts, E9_list_complete=n<=4, last_group_start_tick=group,
                bank_returns=[dict(token=token-len(returns)+1+j,tick=v) for j,v in enumerate(returns)])


def decode(data, expected=1034):
    magic,edition,mode,count,_,_,size,capacity=HEADER.unpack_from(data)
    if expected not in (1034,1035,1054) or (magic,edition,size,capacity,len(data))!=(0x9001,expected,ROW.size,CAPACITY,SIZE) or count>capacity or mode!=0:
        raise ValueError(f'not an MMC{expected} game trace')
    rows=[]
    for i in range(count):
        try:
            rows.append(sample(data,i,edition))
        except ValueError as exc:
            rows.append(dict(index=i,unresolved=str(exc)))
    return dict(fpga_tick_ms=MS, rows=rows)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('file',type=Path)
    p.add_argument('--edition',type=int,choices=(1034,1035,1054),default=1034)
    args=p.parse_args()
    print(json.dumps(decode(args.file.read_bytes(),args.edition),indent=2))
