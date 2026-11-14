# SPDX-License-Identifier: MIT
"""Drive the fitted dual-bank, 65816 consume port and E8 snapshot with replay observations."""
import argparse
import csv
import json
import re
import subprocess
from pathlib import Path
from nes_raw506 import sha
from test_nes_raw506_joint import MASTER

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ('nes_domain_reset124','nes_native_mailbox206','nes_bulk_aperture188',
           'nes_tile_bulk206','nes_bulk_control194','nes_plan_spi200')


def fixture(trace, owner):
    with (trace/'window.csv').open() as f:
        rows = list(csv.DictReader(f))
    previous, = [int(r['clock']) for r in rows if (r['g'],r['op'],r['event'])==('968','3','ack')]
    packets = [json.loads(x) for x in (trace/'packets.jsonl').read_text().splitlines()]
    releases = [list(map(int,x.split())) for x in (owner/'consume776.tsv').read_text().splitlines()]
    assert [r[1] for r in releases] == [158,159,160,161]
    assert json.loads((owner/'audit.json').read_text())['frames']==66
    payload = bytearray()
    for index,token,release in releases:
        _,_,header,data = packets[index-1]
        h=bytes.fromhex(header)
        assert h[0]==7 and int.from_bytes(h[8:10],'little')==969 and int.from_bytes(h[16:20],'little')==token
        payload.extend(bytes.fromhex(data))
    assert len(payload)==144
    q = json.loads((trace/'obj-phases.json').read_bytes())['969']
    plans = q['obj_plans']
    assert [p['slot'] for p in plans]==[2,4,5,8]
    origin = q['end_accepted']
    responses = q['cache611']
    assert len(responses)==32 and all(r[-1]=='OBJ_capture' for r in responses)
    # Completed-tile stimulus. Four masked OBJ records request 8,12,8,4 bytes.
    clocks=[origin]+[responses[i][4] for i in (7,19,27,31)]
    assert clocks[-1]==q['last_obj_rom_response']
    release=[r[2] for r in releases]
    def ns(t):
        return round((t-origin)*1e9/MASTER)
    polls=[]
    for e in json.loads((trace/'events.json').read_bytes()):
        if e['generation']==969 and e.get('opcode')=='0xe8' and origin<e['start']<release[-1]:
            b=bytes.fromhex(e['reply'])
            polls.append((ns(e['start']),int.from_bytes(b[14:18],'little') if b[6] else -1))
    assert any(k==161 for _,k in polls)
    data = [*map(ns,clocks),*map(ns,release),*payload,len(polls)]
    return (' '.join(map(str,data))+'\n'+''.join(f'{t} {k}\n' for t,k in polls),
            dict(origin=origin,previous=previous,releases=release,END_check=q['banks557'][-1]['release'],queries=polls))


def run(args):
    args.out.mkdir(parents=True,exist_ok=False)
    pins=json.loads((ROOT/'analysis/bg707-verification.json').read_bytes())['inputs']
    expected={**pins['base'],**pins['changed']}
    files=[args.board/(name+'.sv') for name in SOURCES]
    for f in files:
        assert sha(f)==expected[f.name],f
    def command(name,options,log):
        with (args.out/log).open('wb') as out:
            subprocess.run([str(args.bin/(name+'.exe')),*map(str,options)],cwd=args.out,stdout=out,
                           stderr=subprocess.STDOUT,check=True)
    command('vlib',['work'],'vlib.log')
    command('vlog',['-sv',*files,ROOT/'tests/nes_obj_owner776_tb.sv'],'vlog.log')
    cases={}
    for version in ('763','767'):
        for phase in (1,2):
            key=f'{version}-p{phase}'
            text, row=fixture(args.temp/f'nes-cost768-{key}-ext',args.temp/f'nes-owner776-{key}')
            (args.out/f'{key}.txt').write_text(text)
            log=key+'.log'
            command('vsim',['-c','nes_obj_owner776_tb',f'+fixture={key}.txt','-do','run -all; quit -f'],log)
            transcript=(args.out/log).read_text(encoding='ascii',errors='replace')
            assert 'PASS776' in transcript and '** Fatal:' not in transcript,log
            match=re.search(r'OWNER776 sealed_ns=(\d+) head_ns=(\d+) release_ns=(\d+)',transcript)
            row['RTL_ns']=list(map(int,match.groups()))
            cases[key]=row
    command('vsim',['-c','nes_obj_owner776_tb','+fixture=767-p2.txt','+stop_while_sealed',
                    '-do','run -all; quit -f'],'stop.log')
    assert 'PASS776_STOP' in (args.out/'stop.log').read_text(encoding='ascii',errors='replace')
    (args.out/'result.json').write_text(json.dumps(dict(cases=cases,stop_at_two_sealed=True,pins={f.name:sha(f) for f in files}),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('board','temp','bin','out'):
        p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())
