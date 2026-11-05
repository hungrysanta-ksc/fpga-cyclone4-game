# SPDX-License-Identifier: MIT
"""R1: reanalyse pinned577 inputs and existing two-phase timelines; never simulate."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from analyze_nes_dma542 import partition
from analyze_nes_phase537 import csv_groups, one, ms
from analyze_nes_hardware552 import inputs
from nes_schedule492 import funcs

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text(encoding='utf8'))


def summary(values):
    values=sorted(values)
    return dict(n=len(values),mean=sum(values)/len(values),
                p95_nearest_rank=values[math.ceil(.95*len(values))-1],maximum=values[-1])


def union(intervals):
    end=None;total=0
    for a,b in sorted(intervals):
        assert b>=a
        if end is None or a>=end:total+=b-a
        elif b>end:total+=b-end
        end=b if end is None else max(end,b)
    return total


def inventory(folder, predicate=lambda p:True):
    return {p.relative_to(folder).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p))
            for p in sorted(folder.rglob('*')) if p.is_file() and predicate(p)}


def phase(t,i,pins):
    d=t/f'nes-close561-run{i}';replay=t/f'nes-cdc576-replay{i}'
    for name,h in pins.items():assert sha(d/name)==h,name
    assert sha(d/'window.csv')==sha(replay/'window.csv')
    replay_result=read(replay/'result.json')
    assert replay_result['passed'] and replay_result['commits']==53
    cpu=csv_groups(d/'window.csv');events=read(d/'events.json')
    rom=read(d/'obj-phases.json');j=read(d/'joint.json')
    assert j['passed'] and j['commits']==53
    assert [f['ACK_masterclock'] for f in j['frames']]==[f['ACK_masterclock'] for f in replay_result['frames']]
    # Historical506 logger reused `start` for next capture on the final D2.
    # Keep its original evidence; no guessed repair of the lost SPI start.
    all_spi=[r for r in events if r['event']=='SPI']
    assert all(b['clock']>=a['clock'] for a,b in zip(all_spi,all_spi[1:]))
    invalid=[r for r in all_spi if r['start']>r['clock']]
    assert len(invalid)==53 and {r['generation'] for r in invalid}==set(range(905,958))
    for r in invalid:
        assert r['opcode']=='0xd2'
        assert r is [s for s in all_spi if s['generation']==r['generation'] and s['opcode']=='0xd2'][-1]
        expected=(math.floor((r['clock']-j['parameters']['ROM_phase'])/(341*262*4))+1)*(341*262*4)+j['parameters']['ROM_phase']
        assert r['start']==expected
    part=partition(d);byframe={}
    for g in range(906,958):
        ev=[r for r in events if r['generation']==g]
        m={k:one(ev,k)['clock'] for k in ['source_begin','planner_enter','output_enter531']}
        tail=[r for r in cpu[g] if r['op']==3]
        head,ack,reveal=[one(tail,k)['clock'] for k in ['load','ack','reveal']]
        old=[r for r in cpu[g-1] if r['op']==3]
        prev_ack=one(old,'ack')['clock'];prev_reveal=one(old,'reveal')['clock']
        p=part[g]
        terms=dict(previous_ACK_to_source_ms=ms(m['source_begin']-prev_ack),
            source_to_planner_ms=ms(m['planner_enter']-m['source_begin']),
            planner_to_output_ms=ms(m['output_enter531']-m['planner_enter']),
            output_to_SEAL_head_ms=p['output_to_head_ms'],
            SEAL_checks_ms=p['checks_ms'],SEAL_VBlank_service_ms=p['serviced_VBlank_wait_ms'],
            SEAL_DMA_ms=sum(p['DMA_ms'].values()),SEAL_other_ms=p['other_setup_control_ms'])
        assert all(v>=0 for v in terms.values())
        interval=ms(ack-prev_ack)
        assert abs(sum(terms.values())-interval)<1e-9
        spi=[r for r in ev if r['event']=='SPI']
        ops=Counter()
        for r in spi:ops[r['opcode']]+=r['bytes']
        observers=Counter(r['opcode'] for r in ev if r['event']=='observer')
        for op,n in observers.items():ops[op]+=n*8
        reads=rom[str(g)].get('rom_service',[])
        assert all(a<=b<=c for _,a,b,c in reads)
        # Resource intervals overlap CPU/SPI/consumer work; never add to terms.
        byframe[g]=dict(terms=terms,ACK_interval_ms=interval,
            reveal_interval_ms=ms(reveal-prev_reveal),final_wait_count=p['final_wait_count'],
            final_wait_ms=p['final_wait_ms'],post_SEAL_DMA_B=sum(p['DMA_B'].values()),
            operation_wire_B=dict(ops),nonquery_wire_B=sum(v for k,v in ops.items() if k not in ('0xd0','0xe0','0xe8')),
            nested_resource=dict(SPI_call_span_union_ms=None,
                SPI_valid_span_subset_union_ms=ms(union([(r['start'],r['clock']) for r in spi if r['clock']>=r['start']])),
                SPI_missing_start_count=sum(r['clock']<r['start'] for r in spi),
                ROM_request_to_grant_union_ms=ms(union([(a,b) for _,a,b,_ in reads])),
                ROM_grant_to_response_union_ms=ms(union([(b,c) for _,_,b,c in reads])),
                ROM_reads=len(reads),OBJ_plans=len(rom[str(g)].get('obj_plans',[]))))
    wire=Counter()
    for r in events:
        if r['event']=='SPI':wire[r['opcode']]+=r['bytes']
        elif r['event']=='observer':wire[r['opcode']]+=8
    assert dict(wire)==j['wire_B']
    groups={}
    for name,frames in [('both_banks_initialized',range(907,958)),('dense_regression',range(951,956))]:
        items=[byframe[g] for g in frames]
        groups[name]=dict(ACK=summary([x['ACK_interval_ms'] for x in items]),
            reveal=summary([x['reveal_interval_ms'] for x in items]),
            mean_terms={k:sum(x['terms'][k] for x in items)/len(items) for k in items[0]['terms']},
            nonquery_wire_B=summary([x['nonquery_wire_B'] for x in items]),
            final_wait_generations=[g for g in frames if byframe[g]['final_wait_count']],
            nested_ROM_wait_mean_ms=sum(x['nested_resource']['ROM_request_to_grant_union_ms'] for x in items)/len(items))
    assert byframe[952]['final_wait_count']==byframe[957]['final_wait_count']==0
    return dict(phase=i,groups=groups,frames=byframe,wire_B=dict(wire),
        unchanged_replay=dict(commits=53,last_ACK_masterclock=replay_result['frames'][-1]['ACK_masterclock'],
            VRAM_DMA_B=replay_result['vram_DMA_B']),
        historical_logger=dict(invalid_D2_start_records=invalid,SPI_end_monotonic=True,
            explanation='Final D2 start was overwritten with next capture start. Clock/capture readiness unchanged; complete SPI span unknown, byte counts and outer partition retained.'),
        parameters=j['parameters'],scope=j['scope'],physical_timing=j['physical_timing'],
        full_ROM_RTL=j['full_ROM_RTL'],ARM_instructions=j['ARM_instructions'],
        SysTick_instructions=j['SysTick_instructions'],IRQ_lateness_masterclocks=j['IRQ_boundary_lateness_masterclocks'],
        evidence=pins,replay={n:sha(replay/n) for n in ['client.sfc','arrivals.tsv','window.csv','result.json','audit.json','bank561.csv']})


def main(a):
    t=a.traces;w=a.workspace;out=a.out;out.mkdir(parents=True,exist_ok=False)
    board=t/'nes-cdc576-board01';arm=w/'probes/nes-gate577/ARM577'
    base=w/'probes/nes-end557/ARM558/src';client=w/'probes/nes-admit556/client01'
    pkg=read(ROOT/'analysis/trial577-package.json');cdc=read(ROOT/'analysis/cdc576-verification.json')
    old=read(ROOT/'analysis/close561-verification.json')
    fw=arm/'src/obj-nes-100/firmware.stm'
    assert sha(fw)==pkg['firmware_SHA256']
    assert sha(base/'obj-nes-100/firmware.stm')==old['firmware']
    f=funcs(arm/'src/obj-nes-100/sd2snes.elf')
    assert f==funcs(base/'obj-nes-100/sd2snes.elf') and len(f)==792
    assert sha(board/'output_files/board.sof')==pkg['SOF_SHA256']
    assert all(sha(board/n)==h for n,h in cdc['RTL'].items())
    assert sha(board/'cdc576.sdc')==cdc['final_routed_extension']
    rom=(client/'sink165.sfc').read_bytes()
    assert sha(client/'sink165.sfc')==old['client']
    assert bytes.fromhex((board/'sink-program.hex').read_text())==rom[:5056]+rom[-64:]
    for i in [1,2]:
        assert sha(t/f'nes-cdc576-replay{i}/client.sfc')==old['client']
    names=set(read(ROOT/'analysis/trial558-verification.json')['inputs'])|set(cdc['RTL'])
    names.update(['initial576.sdc','cdc576.sdc'])
    fpga={n:dict(bytes=(board/n).stat().st_size,sha256=sha(board/n)) for n in sorted(names)}
    # Snapshot project-local inputs; toolchain/system headers are not claimed closed.
    arm_files=inventory(arm,lambda p: not any(x.startswith(('obj-','.dep','.git')) for x in p.relative_to(arm).parts)
                        and p.suffix not in ('.log','.o','.elf','.su'))
    tools=['analyze_nes_whole580.py','analyze_nes_dma542.py','analyze_nes_phase537.py',
           'nes_schedule492.py','build_nes_trial577.ps1','prepare_nes_trial577.py',
           'prepare_nes_cdc576.py','nes_cdc576.py','test_nes_close561.py','replay_nes_close561.py',
           'test_nes_raw506_joint.py','check_nes_clock580.py']
    manifest=dict(candidate='MMC577',locations=dict(FPGA='TEMP/nes-cdc576-board01',
        ARM='WORKSPACE/probes/nes-gate577/ARM577',comparison_ARM='WORKSPACE/probes/nes-end557/ARM558/src',
        SNES='WORKSPACE/probes/nes-admit556/client01',coupled='TEMP/nes-close561-run{1,2}',
        CPU_replay='TEMP/nes-cdc576-replay{1,2}',physical_logs='WORKSPACE/probes/nes-hardware578/run01'),
        FPGA_inputs=fpga,ARM_project_files=arm_files,ARM_function_equality=792,
        artifacts=dict(firmware=sha(fw),ELF=sha(arm/'src/obj-nes-100/sd2snes.elf'),
                       SOF=sha(board/'output_files/board.sof'),SNES_ROM=sha(client/'sink165.sfc'),
                       package=sha(ROOT/'analysis/trial577-package.json')),
        tools={n:sha(ROOT/'tools'/n) for n in tools},
        rebuild_scope='Selected local snapshots, dependency recipes and historical traces; not a clean-clone or fresh full co-simulation closure.',
        unresolved_reproduction=['External ARM compiler/system headers and emulator/tool versions must be restored.',
            'Original source/geometry/capture/plan fixtures and repeated boot ROM calendar are required for fresh co-simulation; current reanalysis consumes pinned recorded events.',
            '576 post-route CDC rebinding is STA-only; do not silently rebuild a different bitstream.'])
    phases=[phase(t,i,old['phases'][i-1]['early']['pins']) for i in [1,2]]
    # Same input/output work; polling count can differ with time.
    for g in range(906,958):
        for op in ['0xd1','0xe1','0xe9']:
            assert phases[0]['frames'][g]['operation_wire_B'].get(op,0)==phases[1]['frames'][g]['operation_wire_B'].get(op,0)
    raw=w/'probes/nes-hardware578/run01';g,b,_,rawpins=inputs(raw,577)
    physical=read(ROOT/'analysis/hardware578-mmc577.json')
    assert rawpins==physical['source_SHA256']
    n=int(g['native_frames']);hz=int(b['cost_clock_hz']);dwt={}
    for i,name in enumerate(['receive','plan_supply','output_final_ack']):
        values=list(map(int,b[f'cost_phase_{i:02}'].split(',')))
        dwt[name]=((values[2]<<32)+values[3])/hz*1000/n
    dwt['unattributed_or_different_boundary_ms']=physical['display']['mean_ms']-sum(dwt.values())
    assert dwt['unattributed_or_different_boundary_ms']>=0
    projection=read(ROOT/'analysis/retrospective579.json')['wire_projection']
    result=dict(stage=580,baseline='MMC577',new_firmware=False,new_FIT=False,new_simulation=False,
        logger_regression=read(w/'probes/nes-whole580/clock01.json'),
        retained_budget=dict(LE=15260,LE_free=148,comb=14191,FF=8407,M9K=51,M9K_free=5,
            ARM_Flash_free_B=84,ARM_BSS_B=18592,source='analysis/retrospective579.json; selected576/577, no new synthesis/build',
            full_IO_signoff=False,whole_60Hz_passed=False),
        phases=phases,physical=dict(evidence='analysis/hardware578-mmc577.json',DWT_ms_per_display=dwt,
                                  wire_projection=projection,source_SHA256=rawpins),
        accounting='8 disjoint wall-time terms sum exactly to ACK interval for each of104 warm/second-bank cases; SPI/ROM/DWT resource times are nested and not added.',
        uncertainty=[
          dict(id='U1',topic='Physical receive, capture and input payload distribution',known='Aggregate bytes/cost and four retained capture transitions',missing='Per-frame canonical/encoded section bytes, capture counts and physical game/input latency',method='One bounded diagnostic pass reusing existing counters/buffers or separate diagnostic build; bind same trace to reference NES progress; record overhead.'),
          dict(id='U2',topic='ROM grant timing and ARM cycle model',known='Same53 inputs, CPI2, measured503 per-op overhead, repeated boot frames12..19 calendar',missing='Actual first-level dense-ROM calendar and physical instruction/IRQ latency',method='Targeted timestamp/owner trace for selected sparse and dense windows; compare uninstrumented timestamps before using model as feasibility gate.'),
          dict(id='U3',topic='Physical output partitions',known='Aggregate36.37ms and exact CPU replay partitions',missing='Physical per-frame SEAL acceptance/DMA/VBlank/ACK decomposition',method='Reuse CPU interval logger for current trace; add only missing bounded phase marks to diagnostic build, not an always-on large trace.'),
          dict(id='U4',topic='Fresh execution source closure',known='Current source/artifact and recorded trace hashes',missing='Single-command fresh co-simulation fixture/toolchain restoration',method='Restore only selected fixture/calendar/source inputs from existing private snapshots; do not recreate all historical candidates.')],
        next='R1 existing-data pass complete. One targeted missing-data pass remains before R2 feasibility approval; no structural candidate selected.',
        interpretation='Post-SEAL DMA averages about1ms in this replay. Early output/pre-SEAL and source transfer dominate; these are model results, not physical577 DMA measurements.')
    for name,value in [('manifest.json',manifest),('result.json',result)]:
        (out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(dict(inputs=len(fpga),ARM_files=len(arm_files),
        phases=[dict(phase=p['phase'],groups=p['groups']) for p in phases],physical=dwt),ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['traces','workspace','out']:p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
