"""Export actual E9 wire payloads and the matching ROM calendar from 913."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from nes_overlap913 import LeadingRecord, OUT, work, peer, monitor
from test_nes_service509_schedule import Calendar
from prepare_nes_opening818 import ADVENTURE_SHA
from nes_raw506 import sha
from test_nes_obj609 import lanes
from test_nes_banks557 import MASTER, host_after


class FixtureLink(LeadingRecord):
    def accept(self,tx,t):
        if tx[0]==0xe9:
            name='e9wire914.jsonl' if self.generation==912 else f'e9wire914-{self.generation}.jsonl'
            with (self.a.out/name).open('a') as log:
                print(json.dumps([t,tx.hex()]),file=log)
        return super().accept(tx,t)


def fixture(temp,phase,cold,g=912,tag='914wire',*,include_bg=False,earlier_origin=None,initial_polls=False):
    case=f'nes-tile821-obj-jointmirror-p{phase}-{tag}-{"cold" if cold else "warm"}-pair'
    run=temp/case
    name='e9wire914.jsonl' if g==912 else f'e9wire914-{g}.jsonl'
    d=run if g==912 else run/f'gen{g}'
    d.mkdir(exist_ok=True)
    events=[json.loads(line) for line in (run/name).read_text().splitlines()]
    packet=json.loads((run/'banks904.json').read_bytes())[str(g)]['banks557']
    assert [e[0] for e in events]==[p['seal'] for p in packet]
    origin=int(events[0][0])-2048
    if earlier_origin is not None:
        origin=min(origin,earlier_origin)
    wire=[];sizes=[];length=0
    for end,body in events:
        data=bytes.fromhex(body);n=int.from_bytes(data[1:3],'little')
        assert data[0]==0xe9 and n==len(data)-8
        # Board RAM owns the complete packet only on the CRC-accepted seal.
        # Write bytes on earlier host edges. No byte is speculatively eligible.
        sizes.append((round(end-origin),n,data[3],int.from_bytes(data[-4:-2],'big')))
        wire.extend(data[4:-4]);length+=n
    cal=Calendar(temp/'nes-service509-rom03')
    ends=int(json.loads((run/'verified905.json').read_bytes())['final_ACK'][1])+2*357368
    grants=[period*cal.period+at-origin for period in range(origin//cal.period,ends//cal.period+1)
            for at,_ in cal.pairs if origin<=period*cal.period+at<=ends]
    (d/'wire914.hex').write_text(''.join(f'{b:02x}\n' for b in wire))
    (d/'batch914.txt').write_text(''.join('%d %d %d %d\n'%b for b in sizes))
    (d/'grants914.txt').write_text(''.join(f'{x}\n' for x in grants))
    (d/'origin914.txt').write_text(str(origin))
    records=[json.loads(s) for s in (run/'producer.jsonl').read_text().splitlines()]
    returned=dict(json.loads((run/'returns904.json').read_bytes()))
    jobs=[j for j in records if j['generation']==g]
    token_map={j['token']:i+1 for i,j in enumerate(jobs)}
    polls=[]
    for e in json.loads((run/'events.json').read_bytes()):
        if e['generation']!=g or e.get('opcode')!='0xe8' or (not initial_polls and e['start']<events[0][0]):continue
        reply=bytes.fromhex(e['reply'])
        assert reply[3] in (0,1,2) and reply[6] in (0,1)
        sample=round(host_after(e['start']+7.5*MASTER/2625000,3)-origin)
        token=token_map[int.from_bytes(reply[14:18],'little')] if reply[6] else 0
        polls.append((sample,reply[3],int.from_bytes(reply[4:6],'big'),token))
    (d/'polls914.txt').write_text(''.join('%d %d %d %d\n'%poll for poll in polls))
    (d/'sizes914.txt').write_text(f"{len(jobs)} {sum(j['bytes'] for j in jobs)}\n")
    (d/'tokens914.txt').write_text(''.join(f"{j['kind']} {j['bytes']} {int(j['producer'])-origin} {returned[j['token']]-origin}\n" for j in jobs))
    capture=[]
    owned=False
    for line in (temp/'nes-gap904/hits-obj/stim.tsv').read_text().splitlines():
        op,a,b,c=map(int,line.split())
        if op==0:owned=a==g
        if op==1 and owned and (not cold or g<907):capture.append(f'{a} {b} {c}\n')
    (d/'cap914.txt').write_text(''.join(capture))
    rom=Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes'
    assert sha(rom)==ADVENTURE_SHA
    chr_bytes=rom.read_bytes()[-131072:]
    (d/'chr914.hex').write_text(''.join(f'{b:02x}\n' for b in chr_bytes))
    expected=bytearray(16384 if include_bg else 8192)
    for _,raw in json.loads((temp/f'nes-gap904/data-obj/obj/frame{g}/plans.json').read_bytes()):
        q=bytes.fromhex(raw)
        assert q[6] in ((0,1,2) if include_bg else (1,2))
        for idx,addr in lanes(q):
            expected[(8192 if include_bg and q[6]==1 else 0)+32*int.from_bytes(q[2:4],'little')+idx]=chr_bytes[addr]
    (d/'expected914.hex').write_text(''.join(f'{b:02x}\n' for b in expected))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('temp',type=Path)
    ap.add_argument('phase',type=int)
    ap.add_argument('--cold',action='store_true')
    ap.add_argument('--lead-in',action='store_true')
    a=ap.parse_args()
    with patch.object(peer,'PeerLink',FixtureLink),patch.object(peer,'CLIENT',OUT/'consumer'),patch.object(peer,'monitor',monitor):
        tag='914lead' if a.lead_in else '914wire'
        peer.compare(a.temp,a.phase,a.cold,True,edition=907,work_arm=work('idle'),run_id=tag)
    for g in ((910,911) if a.lead_in else (912,)):
        fixture(a.temp,a.phase,a.cold,g,tag)
