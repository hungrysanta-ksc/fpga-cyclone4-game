"""Same-work two-start timing, validated response count and full linked cost."""
import argparse,json
from pathlib import Path
from analyze_nes_credit709 import memory,trace,read,sha,ms,csv_groups,one,contents,tile_image,receive_batch,cost,queries

def observations(events):
    snapshots=[e for e in events if e['event']=='E1_snapshot710']
    checks=[e for e in events if e['event']=='full_response710']
    checked_E1=checked_E0=0;last=None
    for e in events:
        if e['event']=='SPI':last=e['opcode']
        if e['event']=='full_response710':
            assert last in ('0xe0','0xe1'),last
            if last=='0xe0':checked_E0+=1
            else:checked_E1+=1
    reasons={'short':0,'not_needed':0,'unchanged':0,'full_check':0}
    for e in snapshots:
        rx=bytes.fromhex(e['reply']);pending=(e['sent_before']-e['retired_before'])&65535
        key='short' if e['length']<20 else 'not_needed' if pending<2 else 'unchanged' if int.from_bytes(rx[5:7],'big')==e['retired_before'] else 'full_check'
        reasons[key]+=1
    assert checked_E1==reasons['full_check'],(checked_E1,reasons)
    # Runtime construction executes the initial empty E0 before our observer
    # is installed. Do not invent a hook observation for that initialization.
    total_E0=sum(e['event']=='SPI' and e['opcode']=='0xe0' for e in events)
    assert checked_E0==total_E0-1,(checked_E0,total_E0)
    first=next(e for e in events if e['event']=='SPI' and e['opcode']=='0xe0')
    assert first['generation']==905 and first['reply']=='00f70000000000000000000000000000000000fe'
    return dict(snapshots=len(snapshots),reasons=reasons,actual_full_E1=checked_E1,actual_full_E0=checked_E0,total_full=len(checks),initial_E0_before_observer=1)

def run(a):
    phases={};timing=True
    for p in (1,2):
        dirs={'base':a.temp/f'nes-bg707-step{p}','candidate':a.temp/f'nes-credit710-step{p}'}
        ts={k:trace(d,a.temp/f'nes-front638-both{p}h') for k,d in dirs.items()}
        js={k:read(d/'joint.json') for k,d in dirs.items()};rows={}
        for k,d in dirs.items():
            j=js[k];t=ts[k];events=read(d/'events.json')
            assert j['passed'] and j['commits']==53 and j['max_bulk_banks']<=2
            assert j['parameters']==js['base']['parameters'] and j['client_SHA256']==js['base']['client_SHA256']
            assert contents(d)==contents(dirs['base']) and tile_image(d)==tile_image(dirs['base'])
            assert {g:v['work'] for g,v in t['frames'].items()}=={g:v['work'] for g,v in ts['base']['frames'].items()}
            if k=='candidate':assert j['firmware_SHA256']==sha(a.probe/'arm01/src/obj-nes-100/firmware.stm')
            s911=[v for v in csv_groups(d/'window.csv')[911] if v['op']==3]
            protection=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
                reveal951=t['details'][951]['marks']['reveal']['line']<=246,
                interval952=t['intervals'][952]['VBlank']==3,final_wait957=t['intervals'][957]['final_waits']==0)
            rows[k]=dict(dense_mean_ms=t['checked']['dense_mean_ms'],last_ACK=t['checked']['last_ACK'],
                protected=protection,intervals=t['intervals'],dense=t['dense'],
                deadline911_marks={n:one(s911,n) for n in ('load','upload165_entry')},
                details={g:t['details'][g] for g in (951,952,954,955,956,957)},
                early_DMA_B={g:t['early_DMA_B'][g] for g in (951,952,954,955,956,957)},
                receive956=receive_batch(d),queries=queries(d),wire=j['wire_B'],instructions=j['ARM_instructions'],
                E0_service_ms=sum(ms(e['clock']-e['start']) for e in events if e['event']=='SPI' and e['opcode']=='0xe0'),
                stack_low=j['observed_stack_low'],pins={n:sha(d/n) for n in ('joint.json','events.json','window.csv','packets.jsonl','obj-phases.json','seal528.csv','tile532.csv')})
            if k=='candidate':rows[k]['response_counts']=observations(events)
        c=rows['candidate'];b=rows['base']
        c['delta']=dict(dense_ms=c['dense_mean_ms']-b['dense_mean_ms'],last_ACK_ms=ms(c['last_ACK']-b['last_ACK']),
            E0_B=c['wire']['0xe0']-b['wire']['0xe0'],ARM_instructions=c['instructions']-b['instructions'],
            E0_service_ms=c['E0_service_ms']-b['E0_service_ms'],
            ARM_CPI_sensitivity_ms=(c['instructions']-b['instructions'])*js['candidate']['parameters']['CPI']/84000)
        c['timing_gate']=all(c['protected'].values()) and c['delta']['dense_ms']<0 and c['delta']['last_ACK_ms']<0 and c['receive956']['checked_blocks_before_ACK']==7
        timing &= c['timing_gate'];phases[p]=rows
    boards={n:cost(a.temp/d) for n,d in [('707D','nes-bg707-board04'),('709A','nes-credit709-board01'),('710','nes-credit710-board01')]}
    arm={k:memory(d) for k,d in [('base_long',a.probe.parent/'nes-longrun694/arm01/src'),('base_normal',a.probe.parent/'nes-trial704/arm704-02/src'),('long',a.probe/'arm01/src'),('normal',a.probe/'arm-normal01/src')]}
    assert arm['normal']['Flash_B']-arm['base_normal']['Flash_B']==arm['long']['Flash_B']-arm['base_long']['Flash_B']
    for label,base in [('long',a.probe.parent/'nes-longrun694/arm01/src'),('normal',a.probe.parent/'nes-trial704/arm704-02/src')]:
        target=a.probe/('arm01' if label=='long' else 'arm-normal01')/'src'
        assert [f.name for f in base.glob('nes_*.[ch]') if sha(f)!=sha(target/f.name)]==['nes_sink_window184.c']
        assert all(arm[label]['sections'][s]==arm['base_'+label]['sections'][s] for s in ('.data','.bss','.ahbram'))
    guards={n:read(a.probe/(n+'.json')) for n in ('arm-guards03','long-guards01')}
    assert all(g['passed'] and g['firmware']==arm['long']['firmware'] for g in guards.values())
    rtl=read(a.temp/'nes-credit710-rtl02/result.json');assert rtl['passed']
    for fn,h in rtl['pins'].items():assert sha(a.temp/'nes-credit710-board01'/fn)==h
    meta=read(a.temp/'nes-credit710-board01/inputs710.json');assert set(meta['changed'])=={'nes_sink_spi165.sv'}
    for n,h in meta['base'].items():assert sha(a.temp/'nes-credit710-board01'/n)==meta['changed'].get(n,h)
    b=boards['710'];area=bool(b['SOF'] and not b['LAB_error'] and b['LAB']<=963)
    sta=bool(b['STA'] and min(b['slack_ns'].values())>=0)
    if b['STA']:
        for k in ('Illegal Clocks','Unconstrained Clocks','Unconstrained Input Ports','Unconstrained Output Ports'):
            assert b['unconstrained'][k]==boards['707D']['unconstrained'][k]
    flash=all(arm[k]['Flash_B']<=212992 for k in ('long','normal'))
    r=dict(stage=710,phases=phases,boards=boards,ARM=arm,guards=guards,RTL=rtl,board_inputs=meta,
        timing_gate=timing,Flash_gate=flash,FIT_gate=area,STA_gate=sta,request_gate=bool(timing and flash and area and sta),
        area_delta_LE=b['LE'][0]-boards['707D']['LE'][0],area_delta_LAB=b.get('LAB',0)-boards['707D']['LAB'],
        area_improved=bool(area and b['LE'][0]<boards['707D']['LE'][0] and b['LAB']<=boards['707D']['LAB']),
        selected_before='707D + unchanged694/704 ARM + unchanged65816',
        replay_binding='709A separately verified E1 wire interface;710 snapshot reset removal separately checked against707D control/response timing. Not simultaneous full board simulation.',
        scope='Actual linked ARM/65816 with SPI/IRQ/ROM calendar and read-only response observations; separate real serial RTL proof. No physical FPS claim.',
        new_hardware=False,installer=False,CPU_changed=False,full_IO_signoff=False,
        parser_profile=read(a.probe/'parser-profile.json'),
        failure_scope='Initial observer import order failed before replay; guard01 used wrong through argument order; analysis01 expected constructor E0 hook before observer existed. Corrected harness/accounting only; intermediate evidence retained.',
        cost_scope='Whole53-frame E0 service and extra ARM CPI allocation are diagnostics, not additive physical wall-time savings.')
    a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(dict(gates={k:r[k] for k in ('timing_gate','Flash_gate','FIT_gate','STA_gate','request_gate')},
        phases={p:dict(delta=v['candidate']['delta'],protected=v['candidate']['protected'],counts=v['candidate']['response_counts']) for p,v in phases.items()})))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('temp','probe','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
