"""Reconcile real event publication, same-work timing and complete resource costs."""
import argparse,csv,json,re
from pathlib import Path
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_output664 import trace
from analyze_nes_handoff678 import input_credit
from analyze_nes_idle676 import idle,end_timing
from analyze_nes_bg674 import tile_image
from analyze_nes_frontier536 import contents
from analyze_nes_progress679 import unpack
from nes_rom636 import pack


def mapping(folder):
    text=(folder/'output_files/board.map.summary').read_text()
    def number(label):return int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',text)[1].replace(',',''))
    return dict(LE_before_fit=number('Total logic elements'),comb=number('Total combinational functions'),
        registers=number('Total registers'),RAM_bits=number('Total memory bits'),summary=sha(folder/'output_files/board.map.summary'))


def grants(folder,g,packets):
    rows=csv_groups(folder/'window.csv')[g]
    starts=[r for r in rows if r['event']=='ppu_dma' and r['op']==-1]
    choices=[r for r in rows if r['event']=='idle524'];assert len(starts)==len(choices)
    copied=set();out=[]
    for d,s in zip(starts,choices,strict=True):
        # The new pre-DMA source-class push is charged here. A full scanline
        # is a conservative assertion, not an assigned performance cost.
        assert 0<d['clock']-s['clock']<1364
        accepted=set()
        for p in packets:
            if p['section']==2 and p['ack']<s['clock']:
                accepted.update(range(p['offset'],p['offset']+p['expanded_B'],64))
        off=s['value']-65536 if s['value']>=65536 else None
        if off is not None:
            selected=set(range(off,off+d['value'],64));assert selected<=accepted-copied
            copied.update(selected)
        out.append(dict(clock=d['clock'],line=d['line'],bytes=d['value'],offset=off,
            selection_to_DMA_clocks=d['clock']-s['clock'],accepted_map_B=64*len(accepted),
            remaining_map_B=64*len(accepted-copied)))
    return out


def analyze(a):
    phases={};firmware=sha(a.arm/'obj-nes-100/firmware.stm');client=sha(a.client/'sink165.sfc')
    for n in a.phases:
        folders={'MMC666':a.traces/f'nes-ready673-b{n}','678':a.traces/f'nes-handoff678-credit{n}','680':a.traces/f'nes-progress680-{a.tag}{n}'}
        t={k:trace(f,a.traces/f'nes-front638-both{n}h') for k,f in folders.items()}
        j={k:read(f/'joint.json') for k,f in folders.items()};b,c=t['MMC666'],t['680'];f=folders['680']
        assert j['680']['firmware_SHA256']==firmware and j['680']['client_SHA256']==client
        for k,folder in folders.items():
            assert j[k]['parameters']==j['MMC666']['parameters']
            assert tile_image(folder)==tile_image(folders['MMC666']) and contents(folder)[1]==contents(folders['MMC666'])[1]
            assert {g:d['work'] for g,d in t[k]['frames'].items()}=={g:d['work'] for g,d in b['frames'].items()}
        plans={k:read(folder/'obj-phases.json') for k,folder in folders.items()}
        for g,p in plans['678'].items():
            assert [(x['count'],x['first'],x['decoded']) for x in p['banks557']]==[(x['count'],x['first'],x['decoded']) for x in plans['680'][g]['banks557']]
        cpu=csv_groups(f/'window.csv');s911=[r for r in cpu[911] if r['op']==3]
        protected=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
            reveal951=c['details'][951]['marks']['reveal']['line']<=246,interval952=c['intervals'][952]['VBlank']==3,
            final_wait957=c['intervals'][957]['final_waits']==0)
        dense=c['checked']['dense_mean_ms']-b['checked']['dense_mean_ms'];ack=ms(c['checked']['last_ACK']-b['checked']['last_ACK'])
        regress=[g for g in b['intervals'] if c['intervals'][g]['VBlank']>b['intervals'][g]['VBlank']]
        extra=[g for g in b['intervals'] if c['intervals'][g]['final_waits']>b['intervals'][g]['final_waits']]
        details={}
        for g in (952,954,955,956,957):
            details[g]={}
            for k,folder in folders.items():
                d=t[k]['details'][g]
                details[g][k]=dict(previous_reveal=d['previous_reveal'],marks=d['marks'],packets=d['packets'],terms=d['terms'],
                    early_DMA_B=t[k]['early_DMA_B'][g],idle_grants=grants(folder,g,d['packets']),END=end_timing(folder,g))
        notices=read(f/'progress680-events.json')
        with (f/'progress680.csv').open() as stream:writes=[{k:int(v) for k,v in r.items()} for r in csv.DictReader(stream)]
        assert notices and writes and len(notices)<=len(writes)
        # Every modeled host event must originate from an actual CPU store.
        for e in notices:assert any(w['clock']+3==e['clock'] and w['retired']==e['retired'] for w in writes)
        ev=read(f/'events.json');queries=[e for e in ev if e.get('opcode')=='0xe0' and e.get('reply')]
        seen=[e for e in queries if bytes.fromhex(e['reply'])[2]&8]
        for e in seen:
            r=bytes.fromhex(e['reply']);assert r[2]&7==2 and r[3:5]==r[5:7]
            assert any(q['accepted'] and q['clock']<=e['clock'] for q in notices)
        g=956;prev=c['details'][g]['previous_reveal'];end=c['details'][g]['marks']['ack']['clock']
        phases[n]=dict(protected=protected,dense_delta_ms=dense,last_ACK_delta_ms=ack,
            timing_gate=all(protected.values()) and dense<0 and ack<0 and not regress and not extra,
            interval_regressions=regress,new_final_waits=extra,
            dense={k:dict(VBlank=v['checked']['dense_VB'],mean_ms=v['checked']['dense_mean_ms'],last_ACK=v['checked']['last_ACK']) for k,v in t.items()},
            intervals={k:v['intervals'] for k,v in t.items()},details=details,
            deadline911={k:one(s911,k) for k in ('load','upload165_entry')},
            input_credit=input_credit(f),idle=idle(f),max_bulk_banks=j['680']['max_bulk_banks'],
            CPU_event_writes=len(writes),host_events_accepted=sum(e['accepted'] for e in notices),
            E0_event_observations=len(seen),event956=[e for e in notices if prev<=e['clock']<=end],
            wire_B={k:v['wire_B'] for k,v in j.items()},
            first_poll_clock={k:v['first_packet_poll_masterclock'] for k,v in j.items()},
            first_poll_delta_ms=ms(j['680']['first_packet_poll_masterclock']-j['678']['first_packet_poll_masterclock']),
            pins={k:sha(f/k) for k in ('joint.json','events.json','window.csv','seal528.csv','obj-phases.json','packets.jsonl','progress680.csv','progress680-events.json')})
    flash=(a.arm/'obj-nes-100/firmware.stm').stat().st_size;assert flash<=212992
    info=read(a.client/'build.json');body=(a.client/'body.bin').read_bytes()
    decoded,_=unpack(body[:info['prefix_B']],pack(body,info['prefix_B']));assert decoded==body
    assert info['physical_ROM_B']==5120 and info['physical_free_B']>=0 and len(body)<=5984
    boards={k:mapping(p) for k,p in (('MMC666',a.base_board),('680',a.board))}
    bp=read(a.board/'inputs680.json')
    for name,old in bp['base'].items():assert sha(a.board/name)==bp['changed'].get(name,old)
    guards={p.parent.name+'/'+p.name:dict(SHA256=sha(p),result=read(p)) for p in a.guards}
    assert len(guards)==len(a.guards),'guard report collision'
    for v in guards.values():
        r=v['result']
        if 'firmware' in r:assert r['firmware']==firmware
        if 'client_SHA256' in r:assert r['client_SHA256']==client
        if 'client' in r:assert r['client']==client
        if 'pins' in r:
            for name in ('nes_sink_bus165.sv','nes_sink_spi165.sv','nes_sink_bridge165.sv'):
                assert r['pins'][name]==sha(a.board/name)
    fit=a.board/'output_files/board.fit.summary'
    result=dict(stage=680,variant=a.tag,baseline='MMC666',experimental_base='678 credit',phases=phases,
        timing_gate=set(a.phases)=={1,2} and all(p['timing_gate'] for p in phases.values()),firmware=firmware,client=client,
        Flash_B=flash,Flash_free_B=212992-flash,ARM_data_B=10040,ARM_BSS_B=19544,
        client_build=info,map_only=boards,board_inputs=bp,guards=guards,
        new_FIT=fit.exists(),FIT_passed=None,STA_passed=None,selected='MMC666',
        extra_static_ARM_WRAM_B=0,extra_SNES_DMA_stack_B=info['extra_DMA_stack_B'],
        source_pins={p.name:sha(p) for p in Path('tools').glob('*680.py')},
        scope='Actual linked M4 and 65816. Progress events from CPU stores with8hostclock publication allocation and board-tested endpoint semantics; not live whole NES/PSRAM RTL coexecution. Actual separate RTL2phases. No physical FPS/menu or FIT inferred from MAP.')
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({n:{k:p[k] for k in ('protected','dense_delta_ms','last_ACK_delta_ms','timing_gate','E0_event_observations','first_poll_delta_ms')} for n,p in phases.items()},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag',choices=('coupled','interiorb','neighbor'),default='neighbor')
    p.add_argument('--phases',type=int,nargs='+',default=[1,2])
    for k in ('traces','arm','client','board','base-board','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--guards',type=Path,nargs='+',required=True);analyze(p.parse_args())
