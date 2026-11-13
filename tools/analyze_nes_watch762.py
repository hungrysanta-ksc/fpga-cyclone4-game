# SPDX-License-Identifier: MIT
"""Bind the 753 bus trace, checked receiver schedule, Quartus result and first BG grant."""
import argparse
import bisect
import csv
import json
from pathlib import Path
from analyze_nes_credit753 import partition
from analyze_nes_static751 import phase
from nes_raw506 import sha
from test_nes_service509_schedule import Calendar

def read(path):
    return json.loads(path.read_text(encoding='utf8'))

def records(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))

def analyze(t):
    base=t/'nes-bg707-board04'
    project=t/'nes-watch762-05'
    board=project/'board'
    pins=Path('src/fpga/pin.qsf')
    qsf=(board/'board.qsf').read_text()
    wanted=[s for s in pins.read_text().splitlines() if s.startswith('set_location_assignment') and
            ('SNES_PAWR_IN' in s or 'SNES_PA_IN[' in s)]
    assert len(wanted)==9 and all(s in qsf and s not in (base/'board.qsf').read_text() for s in wanted)
    fit=(board/'fit762.log').read_text(errors='replace')
    assert 'requires 57 memory locations' in fit and 'device has 56' in fit
    rtl=t/'nes-watch762-rtl04'
    assert all('PASS762' in (rtl/f'phase-{n}.log').read_text() for n in (0,8))
    for path in rtl.glob('nes*.sv'):
        assert sha(path)==sha(board/path.name)
    cal=Calendar(t/'nes-service509-rom03')
    result=dict(selected=753,physical_test=False,scope='PA port writes, not PPU internal VRAM readback',
                added_board_pins=wanted,required_M9K=57,available_M9K=56,placed_STA=False,
                ROM_free_B=read(project/'client/build.json')['physical_free_B'],phases={},faults={},
                artifacts={f:sha(board/f) for f in ['board.qsf','board.sdc','fit762.log','nes_map_watch762.sv',
                   'nes_sink_bus165.sv','nes_sink_spi165.sv','nes_sink_bridge165.sv','fxpak_nes_screen137_top.sv']})
    for n in (1,2):
        original=t/f'nes-credit753-prefix{n}'
        trace=t/f'nes-watch762-base{n}'
        checked=t/f'nes-watch762-run{n}'
        exp={}
        for _,_,h,_ in map(json.loads,(original/'packets.jsonl').read_text().splitlines()):
            b=bytes.fromhex(h)
            if b[:2]==bytes((2,2)):
                g=int.from_bytes(b[8:10],'little')
                exp.setdefault(g,{}).update(enumerate(b[16:],int.from_bytes(b[10:12],'little')))
        info=dict(audit=read(trace/'audit.json'),compared={},runs={},schedule_hashes={})
        for label,folder,client in [('753',original,Path('../probes/nes-static751/sharedfast')),
                                    ('762',checked,project/'client')]:
            fw=sha(Path('../probes/nes-credit753/arm-prefix/src/obj-nes-100/firmware.stm'))
            d=phase(t,'sharedfast',n,client=client,folder=folder,firmware=fw)
            info['runs'][label]=dict(dense_ms=d['dense_ms'],ACK_clock=d['ACK'],display957=d['intervals'][957],
                 wait957=d['final_wait957'],line951=d['line951'],intervals={g:d['intervals'][g] for g in (908,911,952)},
                 grant_lines=d['map_latch_lines'],OBJ_line=d['OBJ']['line'],E8_margin_to_749_clocks=-d['E8_delta_clocks'],
                 E8_end_margin_to_749_clocks=d['E8_749_end']-d['E8_end'],protected=d['guarded_schedule'])
            assert d['guarded_schedule'] and d['E8_end']<=d['E8_749_end'] and d['E8_delta_clocks']<=0
        # The schedule model supplies a decoded peripheral response. Bind its
        # ACK to the final RTL CRC/coverage-port exclusion over every long DMA.
        e1=[e for e in read(checked/'events.json') if e.get('opcode')=='0xe1']
        pk=[bytes.fromhex(json.loads(line)[2]) for line in (checked/'packets.jsonl').read_text().splitlines()]
        assert len(e1)==len(pk) and all(e['packet_opcode']==b[0] and e['bytes']==len(b)+3 for e,b in zip(e1,pk))
        refs=[e for e,b in zip(e1,pk) if b[1]==2 or b[0]==1]
        arm=None
        checks=0
        for event in records(checked/'wire762.csv'):
            if event['event']=='arm':
                assert arm is None
                arm=int(event['clock'])
            elif event['event']=='read':
                assert arm is not None and event['byte']=='128'
                end=int(event['clock'])
                assert all(e['clock']<arm or end<e['start'] for e in refs)
                arm=None
                checks+=1
        assert arm is None and checks>=2
        info['reference_port_disjoint_checks']=checks
        for g in (952,957):
            for loc in (trace,checked):
                r=[x for x in records(loc/'wire762.csv') if int(x['g'])==g]
                w=[x for x in r if x['event']=='write']
                src=0xd800 if g==952 else 0x5800
                assert len(w)==1536
                for i,x in enumerate(w):
                    assert [int(x[k]) for k in ('source','port','byte')]==[src+i,0x2118+i%2,exp[g][2048+i]]
                if loc==checked:
                    last=int(w[-1]['clock']);done=int(r[-1]['clock'])
                    assert r[-1]['byte']=='128' and r[-1]['event']=='read'
                    win=[x for x in records(checked/'window.csv') if int(x['g'])==g and x['op']=='3']
                    reveal,=[int(x['clock']) for x in win if x['event']=='reveal']
                    ack,=[int(x['clock']) for x in win if x['event']=='ack' and x['value']=='1']
                    assert last<done<reveal<ack
                    info['compared'][g]=dict(bytes=1536,last=last,result=done,reveal=reveal,ACK=ack)
        for g in range(905,958):assert sha(original/f'frame-{g}.rgb')==sha(checked/f'frame-{g}.rgb')
        for f in ('window.csv','wire762.csv','events.json','joint.json','client.sfc'):
            info['schedule_hashes'][f]=sha(checked/f)
        rows=read(original/'obj-phases.json')['957']['cache611']
        bg=[x for x in rows if x[0]==0 and x[-1]=='ROM']
        assert len(bg)==24
        request,grant,response=bg[0][2:5]
        assert cal.select(request)==(grant,response)
        q,r=divmod(request,cal.period)
        idx=bisect.bisect_left(cal.starts,r)
        def absolute(k):
            period,i=divmod(k,len(cal.starts))
            return (q+period)*cal.period+cal.starts[i]
        c=partition(original)
        info['input_ROM']=dict(blocks_before_956_ACK=c['blocks_before_ACK'],
            source_to_planner_ms=c['total']/21477.272,
            occupancy_ms={k:v/21477.272 for k,v in c['costs'].items()},first_request=request,first_grant=grant,
            BG_ROM_reads=len(bg),first_wait_ms=(grant-request)/21477.272,
            advance_for_24_prior_grants_ms=(request-absolute(idx-24))/21477.272,
            grant_trace=cal.summary['trace_SHA256'])
        result['phases'][n]=info
    for n,k in enumerate(('data','stop'),1):
        f=t/f'nes-watch762-{k}01';r=read(f/'result.json')
        assert r['commits']==52 and r['last_status']==0 and sha(f/'retained.rgb')==sha(t/f'nes-watch762-run{n}/frame-956.rgb')
        assert not any(x['g']=='957' and (x['event']=='reveal' or (x['event']=='ack' and x['op']=='3')) for x in records(f/'window.csv'))
        result['faults'][k]=dict(commits=52,phase=n,retained_RGB=sha(f/'retained.rgb'),writes=sha(f/'wire762.csv'))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp),indent=2)+'\n',encoding='utf8')
