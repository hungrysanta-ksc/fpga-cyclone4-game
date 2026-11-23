"""Timestamp completed planner records without changing the released MMC955 image."""
import argparse
import json
import re
import shutil
from pathlib import Path
from unittest.mock import patch

from nes_feedback953 import BASE, directory, run
from package_nes_trial955 import WORK
from replay_nes_supply905 import joint, UC_HOOK_CODE, UC_ARM_REG_R1
from test_nes_raw506_joint import wire_plan
from fixture_nes_port914 import fixture
from test_nes_banks557 import MASTER, host_after, batches, crc
from nes_companion952 import complete_row_set, replay, supply

CANDIDATE = WORK.parent/'nes-ready958-short'


def prepare():
    link = CANDIDATE/'link'
    shutil.copytree(WORK/'link', link)
    path = link/'src/nes_plan_service200.c'
    old = b'if(p->count<15 || !p->obj_start)return true;'
    new = b'if(!p->obj_start || p->count<(encoded[0]==0x81?12:15))return true;'
    data = path.read_bytes()
    assert data.count(old)==1
    path.write_bytes(data.replace(old,new))


def policy(temp, phase, mode):
    # Both arms use the same scheduler. Measured replies from an unrelated
    # absolute timestamp must not be injected after the wire schedule changes.
    with complete_row_set():
        replay(temp,phase,'cold','banked',wrap=lambda base:supply(base,'checked'),
               tag='958'+mode,work_arm=WORK if mode=='control' else CANDIDATE,edition=955)


def feedback(temp,phase,close=False):
    base=directory(temp,phase,'958mark','cold')
    d=base/'gen906'
    origin=int((d/'origin914.txt').read_text())
    log=(d/'timing958.log').read_text(errors='replace')
    first=re.search(r'E8914 difference edge=(\d+) token=(\d+/\d+) flags=(\d+/\d+) count=(\d+/\d+)',log)
    assert first.groups()[1:]==('0/0','1/0','6/6')
    edge=origin+int(first[1])
    expected=bytes.fromhex(json.loads((base/'e9wire914-906.jsonl').read_text().splitlines()[6])[1])
    captured=[]
    late=None
    if close:
        previous=directory(temp,phase,'958credit','cold')/'gen906'
        text=(previous/'timing958.log').read_text(errors='replace')
        row,=re.findall(r'E8914 difference edge=(\d+) token=(\d+)/(\d+) flags=1/0 count=7/7',text)
        assert row[1]==row[2] and re.search(r'E8914 compared=\d+ different=1\b',text)
        late=int((previous/'origin914.txt').read_text())+int(row[0])

    def wrap(parent):
        class Credit(supply(parent,'checked')):
            verified=None
            def snapshot557(self,tx,start):
                sample=host_after(start+7.5*MASTER/2625000,3)
                if self.generation==906 and tx[0]==0xe9 and self.accepted==6 and captured:
                    assert len(captured)==1 and bytes(tx)==expected
                    self.rpc(sample)
                    self.verified=self.e9_snapshot557=sample
                    return self.response(tx)
                reply=super().snapshot557(tx,start)
                if self.generation==906 and tx[0]==0xe8 and round(sample)==edge:
                    assert reply[3:6]==bytes([0,0,6]) and not any(reply[6:18])
                    out=bytearray(reply)
                    out[3]=1
                    out[19]=crc(out[1:19],8,7,0)
                    captured.append(edge)
                    return bytes(out)
                if self.generation==906 and tx[0]==0xe8 and round(sample)==late:
                    assert len(captured)==2 and reply[3:6]==bytes([0,0,7])
                    out=bytearray(reply)
                    out[3]=1
                    out[19]=crc(out[1:19],8,7,0)
                    captured.append(late)
                    return bytes(out)
                return reply

            def seal557(self,tx,t):
                if self.verified is None:
                    return super().seal557(tx,t)
                assert bytes(tx)==expected and self.generation==906 and self.accepted==6
                rows=batches(self)
                assert len(rows)==6
                rows.append(dict(seal=t,sample=self.verified,count=tx[3],first=self.plan_at))
                captured.append(round(t))
                self.verified=None
        return Credit
    with complete_row_set():
        replay(temp,phase,'cold','banked',wrap=wrap,tag='958closed' if close else '958credit',
               work_arm=WORK,edition=955)
    assert len(captured)==2+int(close)
    if close:
        a=previous.parent
        b=directory(temp,phase,'958closed','cold')
        for f in ('window.csv','packets.jsonl','producer.jsonl','e9wire914-906.jsonl'):
            assert (a/f).read_bytes()==(b/f).read_bytes(), f
        before=json.loads((a/'events.json').read_bytes())
        after=json.loads((b/'events.json').read_bytes())
        changed,=[(x,y) for x,y in zip(before,after,strict=True) if x!=y]
        x,y=changed
        assert (x['generation'],x['opcode'])==(906,'0xe8')
        assert {**x,'reply':y['reply']}==y and round(host_after(x['start']+7.5*MASTER/2625000,3))==late


def trace(temp, phase):
    marks = []
    original = joint.Runtime.__init__

    def attach(cpu, args, link):
        original(cpu, args, link)

        def emitted(u, pc, size, user):
            if cpu.generation != 906:
                return
            record = bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1), 40))
            if int.from_bytes(record[:2], 'little') != 906:
                raise ValueError('wrong planner owner')
            marks.append(dict(tick=cpu.clock, wire=wire_plan(record).hex()))

        pc = cpu.syms['nes_plan200_emit']
        cpu.u.hook_add(UC_HOOK_CODE, emitted, begin=pc, end=pc)

    sources = [BASE] if phase == 1 else [BASE, '953feedback']
    with patch.object(joint.Runtime, '__init__', attach):
        run(temp, phase, 'cold', sources, '958mark', work_arm=WORK, edition=955)
    folder = directory(temp, phase, '958mark', 'cold')
    baseline = directory(temp, phase, '955final', 'cold')
    for name in ('events.json','window.csv','packets.jsonl','producer.jsonl','e9wire914-906.jsonl'):
        if (folder/name).read_bytes() != (baseline/name).read_bytes():
            raise ValueError(f'passive trace changed {name}')
    if not marks:
        raise ValueError('missing ARM plan events')
    (folder/'emit958.json').write_text(json.dumps(marks)+'\n')


def fixtures(temp, phase, mode):
    tag='958'+mode
    folder = directory(temp, phase, tag, 'cold')
    for g in (905,906):
        fixture(temp,phase,True,g,tag,include_bg=True)
    d = folder/'gen906'
    origin = int((d/'origin914.txt').read_text())
    events = json.loads((folder/'events.json').read_bytes())
    idx=6 if mode in ('credit','closed') else 5
    e9 = [e for e in events if e.get('generation')==906 and e.get('opcode')=='0xe9'][idx]
    start = e9['start']
    n = e9['bytes']-8
    at = lambda bits: round(host_after(start + bits*MASTER/2625000,3))-origin
    edges = [at(7.5), *(at(8*(4+i)+7.5) for i in range(n))]
    (d/'admission954.txt').write_text(str(idx)+' '+' '.join(map(str,edges))+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp', type=Path)
    p.add_argument('phase', type=int, choices=(1,2))
    p.add_argument('--fixtures',choices=('mark','credit','closed','short'))
    p.add_argument('--policy',choices=('prepare','short','control','credit','closed'))
    a = p.parse_args()
    if a.policy=='prepare':
        prepare()
    elif a.policy in ('credit','closed'):
        feedback(a.temp,a.phase,close=a.policy=='closed')
    elif a.policy:
        policy(a.temp,a.phase,a.policy)
    elif a.fixtures:
        fixtures(a.temp,a.phase,a.fixtures)
    else:
        trace(a.temp, a.phase)
