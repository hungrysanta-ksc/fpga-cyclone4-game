# SPDX-License-Identifier: MIT
"""Measure exact archived frame payloads, without predicting gameplay FPS.

This offline lower-bound experiment assumes an explicitly inherited base image.
It is not an implementation of delta packets or a persistent pattern cache.
"""
from pathlib import Path
import argparse, json, math
from nes_game147 import sha

SECTIONS = ['bg', 'obj', 'map', 'cgram', 'oam', 'hdma']


def measure(old, new):
    sections=[]
    for name in SECTIONS:
        a=(old/(name+'.bin')).read_bytes();b=(new/(name+'.bin')).read_bytes()
        # New candidate inherits its named base; extension bytes must be sent.
        ranges=[];i=0
        while i<len(b):
            if i<len(a) and a[i]==b[i]:i+=1;continue
            start=i;i+=1
            while i<len(b) and not(i<len(a) and a[i]==b[i]):i+=1
            ranges.append((start,i))
        rebuilt=bytearray(a[:len(b)])
        rebuilt.extend(bytes(len(b)-len(rebuilt)))
        for start,end in ranges:rebuilt[start:end]=b[start:end]
        assert bytes(rebuilt)==b
        sections.append(dict(name=name,before_bytes=len(a),full_bytes=len(b),
                             changed_bytes=sum(e-s for s,e in ranges),ranges=len(ranges),
                             baseline_sha256=sha(old/(name+'.bin')),target_sha256=sha(new/(name+'.bin'))))
    full=sum(s['full_bytes'] for s in sections);delta=sum(s['changed_bytes'] for s in sections)
    packets=sum(math.ceil(s['full_bytes']/240) for s in sections)+2
    return dict(sections=sections,full_payload_bytes=full,changed_byte_lower_bound=delta,
                full_payload_ideal_spi_ms=full*8/2625000*1000,
                table_only_ideal_spi_ms=5152*8/2625000*1000,
                ideal_wire_bytes_per_60hz=2625000/8/60,
                full_packet_count=packets,
                scope='Two existing modeled SMB3 frames, exact byte comparison and base inheritance reconstruction. Ignores DMA alignment/range merging/descriptors/ACK/polling/producer bytes/CPU time; NOT deployable delta protocol or FPS. No stable-slot remapping measured.')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['old','new','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    r=measure(a.old,a.new);r['public_source_sha256']=sha(Path(__file__))
    a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    print(json.dumps(r))
