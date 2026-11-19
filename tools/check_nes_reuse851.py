"""Compare exact map references emitted by the SPI owner to independently captured cells."""
import argparse
import binascii
import json
from pathlib import Path
import struct

from check_nes_input848 import run
from check_nes_serial654 import bench
from nes_direct653 import encode
from nes_raw506 import once
from build_nes_game164 import palette
from check_nes_game478 import Machine,sha


def reference(data):
    def expected(geometry,raw,g):
        packets,counts,arrays=encode(geometry,raw,g)
        prior=data/f'frame{g-1}.geometry'
        if not prior.exists():
            return packets,counts,arrays
        prior=prior.read_bytes()
        prior_count=struct.unpack_from('<H',prior,5728)[0]
        start=0
        for i,wire in enumerate(packets):
            if start==counts[0]:
                break
            end=min(counts[0],start+(84 if start else 80))
            cells=geometry[2*start:2*end]
            if end<=prior_count and cells==prior[2*start:2*end]:
                prefix=b'' if start else wire[:12]
                packets[i]=prefix+struct.pack('>5H',0xfffe,g,start,end-start,binascii.crc_hqx(cells,65535))
            start=end
        return packets,counts,arrays
    return expected


def cold_after_stop(template):
    # The existing bench stops a partially encoded generation. Replay the same
    # cells after common reset; neither stale RAM nor an old credit may be used.
    return once(bench(template),'  request(8\'hd2,16\'hffff,0);','''  @(negedge nes);generation=g+2;owned=1;wait(dut.available);
  if(dut.block_match || dut.history_valid || dut.following || dut.read_seen)
   $fatal(1,"reuse survived STOP");
  request(8'hd2,16'hffff,0);''')


def plain_control(arm,data,out):
    m=Machine(arm,palette())
    rows=[]
    for serial,w in enumerate(json.loads((data/'work.json').read_bytes()),1):
        g=w['g']
        geo=(data/f'frame{g}.geometry').read_bytes()
        raw=(data/f'frame{g}.raw').read_bytes()
        result=m.frame(encode(geo,raw,g)[0],geo,raw,g,serial)
        rows.append([g,result['receive_instructions']])
    out.write_text(json.dumps(dict(firmware=sha(arm/'obj-nes-100/firmware.stm'),frames=rows)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('board','data','arm','out'):
        p.add_argument(name,type=Path)
    p.add_argument('--plain-control',action='store_true')
    a=p.parse_args()
    if a.plain_control:
        plain_control(a.arm,a.data,a.out)
    else:
        run(a.board,a.data,a.arm,a.out,encoder=reference(a.data),adapt=cold_after_stop)
