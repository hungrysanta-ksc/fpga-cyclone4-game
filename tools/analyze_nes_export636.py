# SPDX-License-Identifier: MIT
"""Compare checked display, input ownership, board slack and physical ROM capacity."""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from analyze_nes_dma542 import csv_groups, one, read, sha, ms, partition


def run(folder,reference,*,expected_bg_hits=48):
    j=read(folder/'joint.json')
    assert j['passed'] and j['commits']==j['map_WRAM_VRAM_verified']==53 and j['last_status']==1
    assert j['max_bulk_banks']<=2
    events=read(folder/'events.json')
    cpu=csv_groups(folder/'window.csv')
    costs=partition(folder)
    obj=read(folder/'obj-phases.json')
    cache=Counter(r[5] for v in obj.values() for r in v.get('cache611',[]))
    assert cache['BG_hit']==expected_bg_hits and cache['OBJ_capture']==1200
    previous=None
    rows={}
    early=Counter()
    snapshots=[]
    conservative_margins=[]
    status_margins=[]
    release_upper_bound=None
    for g in range(905,958):
        for name in (f'frame-{g}.rgb',f'map-{g}.bin'):
            assert sha(folder/name)==sha(reference/name),(folder,g,name)
        reveal,ack=[one([r for r in cpu[g] if r['op']==3],key) for key in ('reveal','ack')]
        assert ack['value']==1 and ack['clock']==j['frames'][g-905]['ACK_masterclock']
        inputs=[e for e in events if e.get('opcode') in ('0xd1','0xd2','0xd3') and e.get('input_generation',e['generation'])==g]
        pops=[e for e in inputs if e['opcode']=='0xd2']
        commit,=[e for e in inputs if e['opcode']=='0xd3']
        assert commit['generation']==g and pops[-2]['clock']<=commit['start']<commit['clock']<=pops[-1]['start']
        if g>905:
            # NES release happens when the post-D3 COMMIT record is enqueued.
            # The host's final D2 pop is a conservative upper bound on it.
            conservative_margins.append(inputs[0]['start']-release_upper_bound)
            statuses=[e for e in events if e.get('input_generation')==g and e.get('opcode')=='0xd0' and e['clock']<=inputs[0]['start']]
            assert statuses
            status_margins.append(statuses[-1]['start']-release_upper_bound)
            oldack=j['frames'][g-906]['ACK_masterclock']
            ea=next(e for e in events if e['generation']==g-1 and e.get('opcode')=='0xea')
            assert oldack<=ea['start']<=ea['clock']<=commit['start']
            ahead=[e for e in pops if e['generation']<g]
            assert all(e['generation']==g-1 and e['clock']<=ea['start'] for e in ahead)
            early[g]=len(ahead)
            assert early[g]<=7
            if g<=956:
                ready=one([e for e in events if e['generation']==g+1],'source_begin')['capture_ready']
                snapshots.append(ready-240*341*4-ea['clock'])
            if g>=950:
                rows[g]=dict(interval_VB=reveal['frame']-previous['frame'],line=reveal['line'],ACK=ack['clock'],
                             interval_ms=ms(reveal['clock']-previous['clock']),final_waits=costs[g]['final_wait_count'],
                             pops_before_old_ACK=sum(e['clock']<=oldack for e in ahead),pops_before_EA=early[g],
                             seventh_pop_after_old_ACK_ms=ms(pops[6]['clock']-oldack),
                             prior_SEAL_to_ACK_ms=ms(oldack-next(e['clock'] for e in events if e['generation']==g-1 and e.get('packet_opcode')==3)),
                             first_D1=inputs[0]['start'],old_ACK=oldack,old_EA=ea['clock'],D3=commit['start'])
        period=341*262*4
        phase=j['parameters']['ROM_phase']
        release_upper_bound=((int(pops[-1]['clock']-phase)//period)+1)*period+phase+240*341*4
        previous=reveal
    # Conservative eligibility proxy: final bulk ACK, accepted END and complete capture,
    # all before the previous SEAL. Occupied SPI is not available for next input.
    old_bulk=max(r['clock'] for r in cpu[950] if r['op']==7 and r['event']=='ack')
    seal=next(e['start'] for e in events if e['generation']==950 and e.get('packet_opcode')==3)
    elig=max(old_bulk,obj['950']['end_accepted'],one([e for e in events if e['generation']==951],'source_begin')['capture_ready'])
    busy=sum(max(0,min(seal,e['clock'])-max(elig,e['start'])) for e in events if e['event']=='SPI')
    seven=[e for e in events if e.get('input_generation')==951 and e.get('opcode')=='0xd1'][:7]
    missing=seven[rows[951]['pops_before_old_ACK']:]
    advance=dict(last_unpopped_blocks_full_D1_wire_ms=sum(e['bytes'] for e in missing)*8*1000/2625000,
                 elapsed_ms=ms(seal-elig),busy_SPI_ms=ms(busy),remaining_upper_ms=ms(seal-elig-busy))
    return dict(rows=rows,sealed952={k:costs[952][k] for k in ('SEAL_to_ACK_ms','serviced_VBlank_wait_ms','DMA_B','final_wait_count')},before_SEAL950=advance,min_ready_status_after_conservative_capture_clocks=min(status_margins),min_first_D1_after_conservative_ready_clocks=min(conservative_margins),early_histogram=dict(Counter(early.values())),cache=cache,min_bank_reuse_gap_clocks=min(snapshots),
                dense_VB=sum(rows[g]['interval_VB'] for g in range(951,956)),
                dense_mean_ms=sum(rows[g]['interval_ms'] for g in range(951,956))/5,
                last_ACK=j['frames'][-1]['ACK_masterclock'],pins={key:sha(folder/key) for key in ('joint.json','events.json','window.csv','seal528.csv')},
                measured={k:j[k] for k in ('firmware_SHA256','client_SHA256','max_bulk_banks','SysTick_calls','wire_B','parameters','ROM_read_allocations')})


def board(path):
    out=path/'output_files'
    fit=(out/'board.fit.summary').read_text()
    sta=(out/'board.sta.summary').read_text()
    assert 'Fitter Status : Successful' in fit
    keys=('Setup','Hold','Recovery','Removal','Minimum Pulse Width')
    slack={k:min(map(float,re.findall(r"Model "+k+r" [^\n]+\nSlack : ([-\d.]+)",sta))) for k in keys}
    m9k=int(re.search(r'; M9Ks +; ([\d,]+)',(out/'board.fit.rpt').read_text(errors='replace'))[1].replace(',',''))
    assert not re.search(r'TNS +: -',sta)
    with (path/'io612.tsv').open() as f:
        io=list(csv.DictReader(f,delimiter='\t'))
    io_min={n:min(float(r['slack']) for r in io if r['port']==n) for n in ('ROM_1CE','ROM_2CE','ROM_OE')}
    return dict(M9K=m9k,ROM_pin_min_setup_ns=io_min,fit={k:int(re.search(re.escape(k)+r' : ([\d,]+)',fit)[1].replace(',','')) for k in
                     ('Total logic elements','Total combinational functions','Dedicated logic registers','Total memory bits')},
                minimum_slack_ns=slack,SHA={p.name:sha(p) for p in (out/'board.fit.summary',out/'board.sta.summary',out/'board.sof')})


def main(a):
    root,build=a.traces,a.build
    results=[]
    for i in (1,2):
        ref=root/f'nes-seal625-tables-bg-{i}'
        modes={tag:run(root/f'nes-export636-run{i}{tag}',ref) for tag in ('d','e','f','g','h')}
        for cand,ctrl in [('d','e'),('f','g'),('h','g')]:
            r,b=modes[cand],modes[ctrl]
            assert r['measured']['parameters']==b['measured']['parameters'] and r['measured']['client_SHA256']==b['measured']['client_SHA256']
            assert set(b['early_histogram'])=={0}
            if cand=='h':
                # A later readiness boundary is observationally identical in this
                # no-prefetch control: no positive D0 was issued that early.
                assert b['min_ready_status_after_conservative_capture_clocks']>=0
            r['last_ACK_delta_ms']=ms(r['last_ACK']-b['last_ACK'])
            r['dense_delta_VB']=r['dense_VB']-b['dense_VB']
            r['gates']=dict(seven=r['rows'][951]['pops_before_old_ACK']==7,display951=r['rows'][951]['interval_VB']==3 and r['rows'][951]['line']<=246,
                            no_final_wait957=r['rows'][957]['final_waits']==0,cache_reuse=r['min_bank_reuse_gap_clocks']>=0,conservative_capture=r['min_first_D1_after_conservative_ready_clocks']>=0,
                            dense_and_ACK=r['dense_delta_VB']<0 and r['last_ACK_delta_ms']<0)
        results.append(modes)
    out=dict(scope='Linked ARM + emulated 65816; SPI/IRQ/ROM calendar; separate FPGA RTL/FIT/STA. Not physical FPS.',
             phases=results,Flash_B=(build/'arm02/src/obj-nes-100/firmware.stm').stat().st_size,
             BSS_B=int((build/'arm02/size.log').read_text(encoding='utf-8-sig').splitlines()[1].split()[2]),
             board={p:board(root/p) for p in ('nes-trial613-board01','nes-export636-board01')},
             board_changes=read(root/'nes-export636-board01/inputs636.json'),boot=read(root/'nes-export636-boot01/result.json'),
             checks={p:read(build/(p+'.json')) for p in ('rx02','inplace02','arm02','menu02','reports02')},
             rtl={p:read(root/('nes-export636-'+p)/'result.json') for p in ('rom01','cache01','boundary01','lifecycle02')})
    out['rtl']['lifecycle02']['pass_line']=next(line for line in (root/'nes-export636-lifecycle02/vsim.log').read_text().splitlines() if 'PASS611' in line)
    tools=Path(__file__).resolve().parent
    touched=sorted(tools.glob('*636.py'))+[tools/n for n in ('test_nes_raw506_joint.py','check_nes_lifecycle611.py','check_nes_overlap634_arm.py','check_nes_rom613.py')]
    out['sources']={p.name:sha(p) for p in touched}
    a.out.write_text(json.dumps(out,indent=2)+'\n',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','build','out'):p.add_argument('--'+n,required=True,type=Path)
    main(p.parse_args())
