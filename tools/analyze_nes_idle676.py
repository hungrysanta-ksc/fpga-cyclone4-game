"""Measure bounded input work, real SNES DMA opportunities and complete frame latency."""
import argparse,json
from pathlib import Path
from analyze_nes_bg674 import tile_image
from analyze_nes_bg675 import stalls,drain_tail
from analyze_nes_output664 import trace
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_frontier536 import contents
from check_nes_fault641 import evidence

def end_timing(folder,g):
    ev=[e for e in read(folder/'events.json') if e['generation']==g]
    begin=next(e for e in ev if e['event']=='call673' and e['name']=='nes_plan200_end')
    end=next(e for e in ev if e['event']=='return673' and e['call']==begin['call'])
    wire=[e for e in ev if e['event']=='SPI' and begin['clock']<=e['start']<end['clock']]
    return dict(call=begin['clock'],returned=end['clock'],elapsed_ms=ms(end['clock']-begin['clock']),
        SPI=[{k:e[k] for k in ('opcode','start','clock','reply') if k in e} for e in wire])

def idle(folder):
    ev=read(folder/'events.json');cpu=csv_groups(folder/'window.csv');result=[]
    for enter in (e for e in ev if e['event']=='idle676_enter'):
        end,=[e for e in ev if e['event']=='idle676_return' and e['begin']==enter['clock']]
        assert end['passed']==1 and enter['sent']==enter['retired']==end['sent']==end['retired']
        delta=(end['next_token']-enter['next_token'])&65535;assert delta<=1
        spi=[e for e in ev if e['event']=='SPI' and enter['clock']<=e['start']<end['clock']]
        assert all(e['opcode'] in ('0xd0','0xd1','0xd2') for e in spi)
        g=enter['generation'];dma=[r for r in cpu[g] if r['event']=='ppu_dma' and enter['clock']<=r['clock']<=end['clock']]
        result.append(dict(generation=g,enter=enter,returned=end,elapsed_ms=ms(end['clock']-enter['clock']),
            blocks=delta,SPI=[{k:e[k] for k in ('opcode','start','clock')} for e in spi],DMA_started=dma))
    return result

def tail(folder,t,g):
    r=drain_tail(folder,t,g);r.pop('interpretation')
    d=t['details'][g];first=next(p for p in d['packets'] if p['section']>=3 and p['op']!=7)
    r['empty_queue_DMA_started']=[p for p in csv_groups(folder/'window.csv')[g] if p['event']=='ppu_dma' and
        r['drain_return']<=p['clock']<first['push']]
    r['first_ordinary_push']=first['push'];return r

def run(a):
    phases={};firmware=sha(a.arm/'obj-nes-100/firmware.stm')
    for n in (1,2):
        folders={'MMC666':a.traces/f'nes-ready673-b{n}','675':a.traces/f'nes-bg675-grant{n}','676':a.traces/f'nes-idle676-{a.tag}{n}'}
        if a.tag=='joint':folders['676-input']=a.traces/f'nes-idle676-input{n}'
        traces={k:trace(f,a.traces/f'nes-front638-both{n}h') for k,f in folders.items()}
        b,c=traces['MMC666'],traces['676'];j={k:read(f/'joint.json') for k,f in folders.items()}
        assert j['676']['firmware_SHA256']==firmware
        for k,f in folders.items():
            assert j[k]['parameters']==j['MMC666']['parameters'] and j[k]['client_SHA256']==j['MMC666']['client_SHA256']
            assert tile_image(f)==tile_image(folders['MMC666']) and contents(f)[1]==contents(folders['MMC666'])[1]
            assert {g:r['work'] for g,r in traces[k]['frames'].items()}=={g:r['work'] for g,r in b['frames'].items()}
        cpu=csv_groups(folders['676']/'window.csv');s911=[r for r in cpu[911] if r['op']==3]
        protected=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
            reveal951=c['details'][951]['marks']['reveal']['line']<=246,interval952=c['intervals'][952]['VBlank']==3,
            final_wait957=c['intervals'][957]['final_waits']==0)
        dense=c['checked']['dense_mean_ms']-b['checked']['dense_mean_ms'];ack=ms(c['checked']['last_ACK']-b['checked']['last_ACK'])
        regressions=[g for g in b['intervals'] if c['intervals'][g]['VBlank']>b['intervals'][g]['VBlank']]
        extra=[g for g in b['intervals'] if c['intervals'][g]['final_waits']>b['intervals'][g]['final_waits']]
        work={}
        for g in (952,954,957):
            work[g]={}
            for k,t in traces.items():
                d=t['details'][g]
                work[g][k]=dict(previous_reveal=d['previous_reveal'],interval=t['intervals'][g],marks=d['marks'],
                    last_tile_ACK=d['last_tile_ACK'],last_ROM_response=d['last_ROM_response'],terms=d['terms'],
                    early_DMA_B=t['early_DMA_B'][g],plan=stalls(folders[k],g),packets=d['packets'],
                    END=end_timing(folders[k],g),DMA=[r for r in csv_groups(folders[k]/'window.csv')[g] if r['event']=='ppu_dma'])
        phases[n]=dict(dense_delta_ms=dense,last_ACK_delta_ms=ack,protected=protected,
            selected_gate=all(protected.values()) and dense<0 and ack<0 and not regressions and not extra,
            interval_regressions=regressions,new_final_waits=extra,
            dense={k:dict(VBlank=t['checked']['dense_VB'],mean_ms=t['checked']['dense_mean_ms'],last_ACK=t['checked']['last_ACK']) for k,t in traces.items()},
            intervals={k:t['intervals'] for k,t in traces.items()},same_work_bytes_pixels=True,
            deadline911={k:one(s911,k) for k in ('load','upload165_entry')},
            wire_B={k:v['wire_B'] for k,v in j.items()},details=work,
            drain952={k:tail(folders[k],t,952) for k,t in traces.items()},idle=idle(folders['676']),
            pins={k:sha(folders['676']/k) for k in ('joint.json','events.json','window.csv','seal528.csv','obj-phases.json','packets.jsonl')})
    changed={p.name:sha(p) for p in a.arm.glob('nes_*.[ch]') if sha(p)!=sha(a.base_arm/p.name)}
    expected={'nes_native_sink165.c','nes_native_runtime165.c'}
    if a.tag=='joint':expected.add('nes_plan_service200.c')
    assert set(changed)==expected
    flash=(a.arm/'obj-nes-100/firmware.stm').stat().st_size
    guards={p.name:dict(SHA256=sha(p),result=read(p)) for p in a.guards}
    for item in guards.values():
        g=item['result']
        if 'firmware' in g:assert g['firmware']==firmware
        if 'source_SHA' in g:
            pins=evidence('entry665-verification.json')['board_inputs']['inputs']
            assert all(pins[k]==v for k,v in g['source_SHA'].items())
    r=dict(baseline='MMC666',candidate='idle676-'+a.tag,phases=phases,firmware=firmware,Flash_B=flash,Flash_free_B=212992-flash,
        ARM_data_B=10040,ARM_BSS_B=19544,extra_static_RAM_B=0,changed_vs675=changed,
        guards=guards,
        selected='idle676-'+a.tag if all(p['selected_gate'] for p in phases.values()) else 'MMC666',
        board_and_65816_unchanged=True,new_FIT_STA=False,new_delivery=False,prior_RTL_ownership='analysis/bg675-verification.json',
        DMA_completion_feedback=False,scope='Actual linked M4 and65816; CPI2/SPI/IRQ model and periodic ROM calendar. Checked map receipt is not VRAM completion. Input callback creates an empty-queue opportunity; actual DMA is observed independently in CPU trace. No physical FPS or new menu hardware claim.',
        sources={p.name:sha(p) for p in Path('tools').glob('*676.py')})
    a.out.write_text(json.dumps(r,indent=2)+'\n',newline='\n')
    print(json.dumps({k:{n:v[n] for n in ('dense_delta_ms','last_ACK_delta_ms','protected','interval_regressions','selected_gate')} for k,v in phases.items()},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('traces','arm','base-arm','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--tag',choices=('input','joint'),default='input')
    p.add_argument('--guards',type=Path,nargs='*',default=[]);run(p.parse_args())
