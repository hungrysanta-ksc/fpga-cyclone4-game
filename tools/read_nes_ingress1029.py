"""Read generation-qualified D1 and D2 durations and bound ARM/FPGA clock alignment."""
import argparse
import json
import struct
from pathlib import Path

from read_nes_tail1012 import CAPACITY, HEADER, MS, OFFSET, ROW, SIZE, decode_rows
from read_nes_display1010 import ARM_TICK

INGRESS = struct.Struct('<6I2H')


def boundaries(data, index, row):
    if 'supply_ms' not in row or 'last_tile_to_show_ms' not in row:
        return None
    raw = ROW.unpack_from(data, HEADER.size + index*ROW.size)
    ia, _, probe = raw[3:6]
    origin, query, last = struct.unpack_from('<3H', raw[-2], 6)
    prev, seal, ack = (row[k] for k in ('previous_show','SEAL','final_ACK'))
    q = ack-prev + ((query-ack) & 1023)
    first = q - ((query-origin) & 1023)
    final = q - ((query-last) & 1023)
    if not (0 <= first <= final <= seal-prev <= ack-prev <= q < 1023):
        return None
    # The query takes place between ARM acquisition start and finish. Input age and
    # probe duration truncate to 512 cycles. FPGA stamp differences lose < 1 tick.
    completed = [(q-1)*MS - (ia+probe+2)*ARM_TICK, (q+1)*MS - ia*ARM_TICK]
    to_e9 = [ia*ARM_TICK-(q-first+1)*MS, (ia+probe+2)*ARM_TICK-(q-first-1)*MS]
    return dict(previous_show_to_input_complete_ms=completed, input_complete_to_first_E9_ms=to_e9,
                previous_show_to_first_E9_ms=first*MS, first_E9_to_writer_ms=(final-first)*MS,
                writer_to_SEAL_ms=(seal-prev-final)*MS, previous_show_to_SEAL_ms=(seal-prev)*MS,
                SEAL_to_show_ms=row['seal_to_show_ms'], previous_show_to_ACK_ms=(ack-prev)*MS)


def decode(data, edition):
    if edition not in (1029,1030,1031,1032) or len(data)!=SIZE:
        raise ValueError('invalid edition or size')
    report = decode_rows(data,edition,CAPACITY)
    for i,row in enumerate(report['rows']):
        if 'final_ACK' not in row:
            continue
        first,end,d1,restore,retire,size,gen,blocks = INGRESS.unpack_from(data,OFFSET+i*INGRESS.size)
        if not blocks:
            continue
        if edition in (1031,1032):
            age,size=divmod(size,1<<24)
            if age>127:
                raise ValueError('invalid D2 first-block age')
            row['ready_to_D1_ms']=[age*32768/84000, (age+1)*32768/84000 if age<127 else None]
        duration = (end-first)&0xffffffff
        gaps = duration-d1-restore-retire
        if gen!=row['generation'] or gaps<0 or duration>=84000000 or not blocks<=size<=256*blocks:
            raise ValueError('inconsistent completed input record')
        row['input'] = dict(blocks=blocks, payload_bytes=size, first_D1_to_last_return_ms=duration/84000,
                            D1_ms=d1/84000, restore_and_check_ms=restore/84000,
                            D2_and_D0_ms=retire/84000, between_blocks_ms=gaps/84000)
        timing=boundaries(data,i,row)
        if timing:
            row['timing']=timing
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('file',type=Path)
    data=p.parse_args().file.read_bytes()
    print(json.dumps(decode(data,HEADER.unpack_from(data)[1]),indent=2))
