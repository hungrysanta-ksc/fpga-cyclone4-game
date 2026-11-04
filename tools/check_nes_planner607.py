"""Compare planner binaries using identical warm histories and the same live input RTL."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from analyze_nes_wire600 import Receiver, display_guards
from check_nes_rows604 import check_geometry, fixture, simulate
from check_nes_wire600 import ROOT, read, sha
from trace_nes_overlap606 import Transfers


class PacketTrace(Transfers):
    def output_exchange(self, tx):
        if hasattr(self, 'stream') and tx[0] in (0xe1, 0xe9, 0xea):
            self.stream.append(bytes(tx))
        return super().output_exchange(tx)


def exercise(d, src, args, link, candidate):
    rows = []
    driver = read(ROOT/'analysis/whole580-verification.json')['phases'][0]['parameters']['driver_extra_us']
    for g in (954, 952):
        geom, raw = fixture(args.data, d, g)
        for name, project in [('control', src), ('direct', args.direct/'src'), ('prefix', args.prefix/'src')]:
            m = PacketTrace(project, False, 400)
            lut = re.search(r'\{(.+?)\}', (project/'nes_palette165.inc').read_text())[1]
            m.u.mem_write(m.lut, struct.pack('<64H', *map(int, lut.split(','))))
            assert link.request('reset') == 'OK'
            m.start(link, g, args.warm, driver, 'normal')
            m.io, m.prefix, m.emits, m.stream = [], [], [], []
            for _ in range(512):
                assert m.call('nes_runtime165_step', [m.rt])
                if m.saw_ea:
                    break
            assert m.saw_ea and m.saw_seal and m.state_value() == 0
            check_geometry(m, geom, raw)
            if name == 'control':
                packets = m.stream
                video = bytes(m.u.mem_read(m.video, m.layout['nes_native_video165']['size']))
            assert m.stream == packets
            assert bytes(m.u.mem_read(m.video, len(video))) == video
            commit = m.prefix[-1]['confirmed_ms']
            first = m.first_bg['end_ns']/1e6
            overhead = sum(e['end']-e['start'] for e in m.io if commit <= e['start'] and e['end'] <= first)
            fw = project/'obj-nes-100/firmware.stm'
            row = dict(generation=g, variant=name, firmware_B=fw.stat().st_size, firmware_sha256=sha(fw),
                       receiver_B=m.layout['nes_native165']['size'], prefix6_ms=m.prefix[5]['confirmed_ms'],
                       commit_ms=commit, first_E9_ms=first, planner_ms=first-commit-overhead,
                       seal_ms=next(e['end'] for e in m.io if e.get('packet')==3),
                       EA_ms=next(e['end'] for e in m.io if e['op']=='0xea'),
                       packets=len(packets), stream_sha256=hashlib.sha256(b''.join(
                           struct.pack('>H',len(b))+b for b in packets)).hexdigest(),
                       video_sha256=hashlib.sha256(video).hexdigest(), wire_B=sum(e['n'] for e in m.io))
            if g==954:
                r=Receiver(project,bytes(128));r.start(m.blocks)
                for _ in range(6):
                    assert r.pump()
                tok=(r.start_token+6)&65535
                abort=m.blocks[0][:3]+bytes.fromhex('e002'+'00'*8)
                at=0x20013000;r.u.mem_write(at,abort)
                assert r.call('nes_native165_packet',[r.state,tok,at,len(abort)]) and r.state_value()==0
                r.u.mem_write(at,m.blocks[-1])
                assert not r.call('nes_native165_packet',[r.state,(tok+1)&65535,at,len(m.blocks[-1])])
                r.receive(m.blocks,geom,raw,g)
                row['guards']=display_guards(project,g,m.blocks)
            rows.append(row)
            (d/'partial.json').write_text(json.dumps(rows,indent=2))
    return rows


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('board','probe','arm','direct','prefix','warm','data','out','report'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    report=simulate(a,'compare',a.arm/'src',True,exercise)
    a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
