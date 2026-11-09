"""Matched credit709 end-to-end schedule, both full ARM links and board costs."""
import argparse,json
from pathlib import Path
from analyze_nes_output664 import trace
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_frontier536 import contents
from analyze_nes_bg674 import tile_image
from analyze_nes_seal686 import receive_batch
from analyze_nes_status689 import cost
from summarize_nes_tail708 import queries
from check_nes_game478 import ELFFile

def memory(src):
    with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
        elf=ELFFile(f);secs={s.name:s['sh_size'] for s in elf.iter_sections() if s.name in ('.text','.data','.bss','.ahbram')}
        funcs={s.name:s['st_size'] for s in elf.get_section_by_name('.symtab').iter_symbols()
            if s.name in ('response709','status','nes_window184_through','nes_window532_room','send')}
    return dict(Flash_B=(src/'obj-nes-100/firmware.stm').stat().st_size,
        firmware=sha(src/'obj-nes-100/firmware.stm'),ELF=sha(src/'obj-nes-100/sd2snes.elf'),sections=secs,functions=funcs)

def run(a):
    arm_dir='arm-needed01' if a.needed else 'arm01'
    normal_dir='arm-needed-normal01' if a.needed else 'arm-normal01'
    prefix='nes-credit709-needed' if a.needed else 'nes-credit709-step'
    phases={};timing=True
    for p in (1,2):
        dirs={'base':a.temp/f'nes-bg707-step{p}','candidate':a.temp/f'{prefix}{p}'}
        ts={k:trace(d,a.temp/f'nes-front638-both{p}h') for k,d in dirs.items()}
        js={k:read(d/'joint.json') for k,d in dirs.items()};rows={}
        for k,d in dirs.items():
            j=js[k];t=ts[k]
            assert j['passed'] and j['commits']==53 and j['max_bulk_banks']<=2
            assert j['parameters']==js['base']['parameters'] and j['client_SHA256']==js['base']['client_SHA256']
            assert contents(d)==contents(dirs['base']) and tile_image(d)==tile_image(dirs['base'])
            assert {g:v['work'] for g,v in t['frames'].items()}=={g:v['work'] for g,v in ts['base']['frames'].items()}
            if k=='candidate':assert j['firmware_SHA256']==sha(a.probe/arm_dir/'src/obj-nes-100/firmware.stm')
            s911=[v for v in csv_groups(d/'window.csv')[911] if v['op']==3]
            events=read(d/'events.json')
            protections=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
                reveal951=t['details'][951]['marks']['reveal']['line']<=246,
                interval952=t['intervals'][952]['VBlank']==3,final_wait957=t['intervals'][957]['final_waits']==0)
            rows[k]=dict(dense_mean_ms=t['checked']['dense_mean_ms'],last_ACK=t['checked']['last_ACK'],
                protected=protections,intervals=t['intervals'],dense=t['dense'],
                deadline911_marks={n:one(s911,n) for n in ('load','upload165_entry')},
                details={g:t['details'][g] for g in (951,952,954,955,956,957)},
                early_DMA_B={g:t['early_DMA_B'][g] for g in (951,952,954,955,956,957)},
                receive956=receive_batch(d),queries=queries(d),wire=j['wire_B'],instructions=j['ARM_instructions'],
                E0_service_ms=sum(ms(e['clock']-e['start']) for e in events if e['event']=='SPI' and e['opcode']=='0xe0'),
                stack_low=j['observed_stack_low'],pins={n:sha(d/n) for n in ('joint.json','events.json','window.csv','packets.jsonl','obj-phases.json','seal528.csv','tile532.csv')})
        c=rows['candidate'];b=rows['base']
        c['delta']=dict(dense_ms=c['dense_mean_ms']-b['dense_mean_ms'],last_ACK_ms=ms(c['last_ACK']-b['last_ACK']),
            E0_B=c['wire']['0xe0']-b['wire']['0xe0'],ARM_instructions=c['instructions']-b['instructions'],
            E0_service_ms=c['E0_service_ms']-b['E0_service_ms'],
            ARM_CPI_sensitivity_ms=(c['instructions']-b['instructions'])*js['candidate']['parameters']['CPI']/84000)
        c['timing_gate']=all(c['protected'].values()) and c['delta']['dense_ms']<0 and c['delta']['last_ACK_ms']<0 and c['receive956']['checked_blocks_before_ACK']==7
        timing &= c['timing_gate'];phases[p]=rows
    boards={n:cost(a.temp/d) for n,d in (('707D','nes-bg707-board04'),('709A','nes-credit709-board01'),('709B','nes-credit709-board02'),('709C','nes-credit709-board03'))}
    arm={k:memory(d) for k,d in [('base_long',a.probe.parent/'nes-longrun694/arm01/src'),('base_normal',a.probe.parent/'nes-trial704/arm704-02/src'),('long',a.probe/arm_dir/'src'),('normal',a.probe/normal_dir/'src')]}
    assert arm['normal']['Flash_B']-arm['base_normal']['Flash_B']==arm['long']['Flash_B']-arm['base_long']['Flash_B']
    assert all(arm[x]['sections'][s]==arm['base_'+x]['sections'][s] for x in ('long','normal') for s in ('.data','.bss','.ahbram'))
    for label,base in [('long',a.probe.parent/'nes-longrun694/arm01/src'),('normal',a.probe.parent/'nes-trial704/arm704-02/src')]:
        target=a.probe/(arm_dir if label=='long' else normal_dir)/'src'
        assert [f.name for f in base.glob('nes_*.[ch]') if sha(f)!=sha(target/f.name)]==['nes_sink_window184.c']
    guards={}
    for n in (('arm-needed-guards01','long-needed-guards01') if a.needed else ('arm-guards01','long-guards01')):
        g=read(a.probe/(n+'.json'));assert g['passed'] and g['firmware']==arm['long']['firmware'];guards[n]=g
    rtls={}
    for n,board in [('rtl02','board01'),('rtl03','board02'),('rtl04','board03')]:
        d=a.temp/('nes-credit709-'+n);g=read(d/'result.json');assert g['passed']
        for fn,h in g['pins'].items():assert sha(a.temp/('nes-credit709-'+board)/fn)==h
        rtls[n]=g
    meta=read(a.temp/'nes-credit709-board03/inputs709.json')
    assert set(meta['changed'])=={'nes_sink_spi165.sv'}
    for n,h in meta['base'].items():assert sha(a.temp/'nes-credit709-board03'/n)==meta['changed'].get(n,h)
    b=boards['709C'];area=bool(b['SOF'] and not b['LAB_error'] and b['LAB']<=963)
    sta=bool(b['STA'] and min(b['slack_ns'].values())>=0)
    if b['STA']:
        for k in ('Illegal Clocks','Unconstrained Clocks','Unconstrained Input Ports','Unconstrained Output Ports'):
            assert b['unconstrained'][k]==boards['707D']['unconstrained'][k]
    flash=all(arm[k]['Flash_B']<=212992 for k in ('long','normal'))
    r=dict(stage=709,needed=a.needed,phases=phases,boards=boards,ARM=arm,guards=guards,RTL=rtls,board_inputs=meta,
        timing_gate=timing,Flash_gate=flash,FIT_gate=area,STA_gate=sta,request_gate=bool(timing and flash and area and sta),
        selected_before='707D + unchanged694/704 ARM + unchanged65816',
        replay_binding='709A RTL interface pinned in replay.709B/C have same tested E0/E1 response and clock-identical controls/credits; same ARM/65816 replay reused after separate boundary proofs.',
        scope='Actual linked ARM/65816 with SPI/IRQ/ROM calendar; separate actual RTL serial/ACK/STOP proof. Not simultaneous full NES/PSRAM/CPU simulation or physical FPS.',
        new_hardware=False,installer=False,CPU_changed=False,full_IO_signoff=False,
        failed_generator='rtl01 failed Python quote before any RTL execution; preserved; rtl02/03/04 passed. Analysis01 requested nonexistent911 detail; corrected to actual window marks.',
        parser_profile=read(a.probe/'parser-profile.json'),
        next_budget=dict(implemented=False,
            hypothesis='Use raw retired bytes only as an untrusted hint to skip an E1 response that cannot release new credit; never update state without full CRC/counter/identity validation. Keep authoritative E0/final ACK.',
            needed_before_next_replay=['Measure unchanged-vs-advanced E1 snapshots and actual full-check counts','Bound extra ARM cost against deletable E0 driver/wire time','Resolve snapshot control packing/timing within86LE/1LAB/0M9K; no seed or timeout changes'],
            actual_savings=None,scope='Budget hypothesis only; no new correctness or performance claim.'),
        cost_scope='E0 service and extra ARM CPI allocation are whole53-frame diagnostics, not additive physical wall-time savings.')
    if a.needed:
        old=read(a.probe/'all-verification.json')
        r['unconditional_response_candidate']=dict(SHA256=sha(a.probe/'all-verification.json'),ARM=old['ARM'],
            phases={p:{k:pair['candidate'][k] for k in ('delta','protected','timing_gate')} for p,pair in old['phases'].items()},
            rejected=True,reason='Extra CRC/identity checks on every E1 increased ARM instructions; both dense means regressed.')
    a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(dict(gates={k:r[k] for k in ('timing_gate','Flash_gate','FIT_gate','STA_gate','request_gate')},
        phases={p:dict(delta=v['candidate']['delta'],protected=v['candidate']['protected'],blocks=v['candidate']['receive956']['checked_blocks_before_ACK']) for p,v in phases.items()})))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('temp','probe','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--needed',action='store_true')
    run(p.parse_args())
