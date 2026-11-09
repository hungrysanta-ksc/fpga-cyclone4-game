"""Freeze rejected ARM tail candidates and budget the next credit-response boundary.

Read-only trace attribution is an upper bound, not a replay of removed queries.
Private archive contains target firmware/evidence, never original game ROM.
"""
import argparse, collections, hashlib, json, zipfile
from pathlib import Path
from analyze_nes_output615 import read, sha, ms

ROOT = Path(__file__).resolve().parents[1]

def save(p, x):
    p.write_text(json.dumps(x, indent=2, ensure_ascii=False)+'\n', encoding='utf8')

def queries(folder):
    events=read(folder/'events.json')
    calls={e['call']:e for e in events if e['event']=='call673'}
    ends={e['call']:e['clock'] for e in events if e['event']=='return673'}
    result={}
    for g in (951,952,954,955,956,957):
        rows=[e for e in events if e.get('generation')==g and e['event']=='SPI']
        stats=collections.defaultdict(lambda:dict(count=0,wire_B=0,service_ms=0.0))
        for e in rows:
            if e['opcode']!='0xe0':continue
            enclosing=[(ends[n]-c['clock'],c['name']) for n,c in calls.items()
                if n in ends and c['clock']<=e['start'] and ends[n]>=e['clock']]
            name=min(enclosing)[1] if enclosing else 'outside_recorded_calls'
            v=stats[name];v['count']+=1;v['wire_B']+=e['bytes'];v['service_ms']+=ms(e['clock']-e['start'])
        e1=[e for e in rows if e['opcode']=='0xe1']
        # E1 command+16B header+CRC16 can be only19B. Do not assume a
        # complete20B status reply fits every legal packet.
        result[g]=dict(E0_by_innermost_call=dict(stats),E1_count=len(e1),
            E1_shorter_than_status=sum(e['bytes']<20 for e in e1),
            scope='Enqueue E0 is credit wait. Packet-wire E0 includes room/progress: not all removable. Through/barrier/outside remain mandatory until a new proof.')
    return result

def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    archive={}
    def add(p,n):
        assert p.is_file(),p
        assert n not in archive,n
        assert p.suffix.lower() not in ('.nes','.prg','.chr','.dat'),p
        archive[n]=p
    results={};normal=a.probe/'arm-initialized-normal01/src/obj-nes-100/firmware.stm'
    for mode in ('prefix','scroll','initialized'):
        f=a.probe/(mode+'-verification.json');r=read(f);assert not r['timing_gate']
        phases={}
        for phase,pair in r['phases'].items():
            c=pair['candidate'];b=pair['base']
            phases[phase]=dict(delta=c['delta'],protected=c['protected'],
                dense_mean_ms=c['dense_mean_ms'],last_ACK=c['last_ACK'],
                receive956_blocks=c['receive956']['checked_blocks_before_ACK'],
                reveal951_line=c['details']['951']['marks']['reveal']['line'],
                interval952=c['intervals']['952'],final957=c['intervals']['957'],
                early_DMA_B=c['early_DMA_B'],relative_VBlank_regressions=c['relative_VBlank_regressions'],
                pins=c['pins'],base_pins=b['pins'],stack_low=c['stack_low'])
        results[mode]=dict(accepted=False,Flash_B=r['Flash_B'],firmware=r['firmware'],
            source_pins=r['source_pins'],same_work_and_bytes=True,phases=phases,
            scope=r['scope'],raw_result_SHA256=sha(f))
    credit=a.probe/'arm-credit01/src/obj-nes-100/firmware.stm'
    assert credit.stat().st_size==213008 and normal.stat().st_size==213008
    results['credit']=dict(accepted=False,Flash_B=credit.stat().st_size,over_limit_B=16,
        firmware=sha(credit),timing_run=False,reason='Long build exceeds Flash limit; not replayed')
    results['initialized']['normal_Flash_B']=normal.stat().st_size
    results['initialized']['normal_firmware']=sha(normal)
    guards={}
    for n in ('owner-prefix','owner-scroll','long-prefix','long-scroll','initialized-byte-guards'):
        p=a.probe/(n+'.json');v=read(p)
        if n.startswith('owner'):
            assert len(v['cases'])==41 and len(v['owner'])==6
            assert all(c['passed'] for c in v['cases']+v['owner'])
        elif n.startswith('long'):
            assert v['passed'] and len(v['cases'])==16 and all(c['passed'] for c in v['cases'])
        else:
            assert v['passed'] and v['cases']==29
        guards[n]=dict(SHA256=sha(p),result=v)
    budget={str(p):queries(a.temp/f'nes-bg707-step{p}') for p in (1,2)}
    base=read(a.probe/'prefix-verification.json')
    supply={p:{k:v for k,v in r['base']['first951'].items() if k not in ('gaps','SPI')}
        for p,r in base['phases'].items()}
    arm=a.probe.parent/'nes-longrun694/arm01/src/nes_sink_window184.c'
    rtl=a.temp/'nes-bg707-board04/nes_sink_spi165.sv'
    r=dict(stage=708,selected='707D board + unchanged694 long /704 normal ARM + unchanged65816',
        candidates=results,guards=guards,baseline951=supply,query_budget=budget,
        next_boundary=dict(selected_for_implementation=False,
            hypothesis='Reuse existing E0 snapshot/CRC rotation during E1 full-duplex; consume only prior retired credit before incrementing sent.',
            source_pins={'ARM_window':sha(arm),'RTL_sink':sha(rtl)},
            existing_logic='Snapshot/CRC already initialized for E1 but reply/rotation only exposed for E0. E1 accepted increments at SS release; snapshot predates it.',
            retain=['Independent packet/ACK checker','CRC8 and counter/identity validation','STOP guard','Full final-display ACK and menu/base','E0 fallback for short E1/stale response/full window'],
            replacement=['One shared ARM status parser, not duplicate response checker','Existing snapshot/reply rotation, no second snapshot or RAM','Only proven redundant credit queries; receipt/final ACK not assumed removable'],
            limits=dict(LE_free=86,LAB_free=1,M9K_free=0,normal_Flash_free_B=8,long_Flash_free_B=52),
            actual_deleted_E0=0,actual_deleted_LE=0,actual_time_gain_ms=None,
            risk='A stale pre-E1 snapshot is conservative but not sufficient to prove current E1 acceptance. Both status semantics and last identity must be checked before next issuance.'),
        failures=dict(initial_subst='Default sandbox build failed before build; escalated authorized builder completed.',
            instrumentation='New per-packet memory-store observer first import order failure, then SysTick handler did not return. Excluded from timing evidence; unchanged standard replay completed both phases, separate29 byte cases passed.'),
        new_RTL=False,new_FIT_STA=False,new_installer=False,new_hardware=False,
        scope='Three matched53-frame candidates x2 starts, actual linked ARM/65816 with modeled SPI/IRQ/ROM calendar. Not simultaneous NES/PSRAM RTL or physical FPS. Rejected candidates leave selected safety/menu paths unchanged.')
    save(ROOT/'analysis/tail708-verification.json',r)
    add(ROOT/'analysis/tail708-verification.json','analysis/tail708-verification.json')
    # Explicit inventories keep game ROM, licensed tools, raw graphics and caches out.
    for p in a.probe.iterdir():
        if p.is_file() and p.suffix in ('.json','.log','.ps1'):add(p,'probe/'+p.name)
    builds=('arm-prefix01','arm-prefix02','arm-scroll01','arm-credit01','arm-initialized01','arm-initialized-normal01')
    for name in builds:
        d=a.probe/name
        for p in d.glob('*.log'):add(p,name+'/'+p.name)
        for n in ('nes_native_sink165.c','nes_sink_window184.c','nes_sink_window184.h'):
            p=d/'src'/n
            if p.exists():add(p,name+'/src/'+n)
        for n in ('firmware.stm','sd2snes.elf','sd2snes.map','nes_native_sink165.su'):
            p=d/'src/obj-nes-100'/n
            if p.exists():add(p,name+'/obj/'+n)
    for mode in ('prefix','scroll','credit','initialized'):
        add(a.probe/mode/'nes_native_sink165.c','patch/'+mode+'/nes_native_sink165.c')
    for folder in ('nes-bg707-step1','nes-bg707-step2',
        'nes-tail708-prefix1','nes-tail708-prefix2','nes-tail708-scroll1','nes-tail708-scroll2',
        'nes-tail708-initialized1','nes-tail708-initialized-plain1','nes-tail708-initialized-plain2'):
        for n in ('joint.json','events.json','window.csv','packets.jsonl','obj-phases.json','seal528.csv','tile532.csv'):
            p=a.temp/folder/n
            if p.exists():add(p,folder+'/'+n)
    for p in ROOT.glob('tools/*tail708.py'):add(p,'tools/'+p.name)
    add(ROOT/'docs/nes-tail708-results.ko.md','docs/nes-tail708-results.ko.md')
    add(arm,'boundary/nes_sink_window184.c');add(rtl,'boundary/nes_sink_spi165.sv')
    for n in ('bg707-verification.json','bg707-archive.json'):
        add(ROOT/'analysis'/n,'inherited/'+n)
    inv={n:dict(bytes=p.stat().st_size,SHA256=sha(p)) for n,p in sorted(archive.items())}
    save(a.out/'inventory.json',inv);zpath=a.out/'evidence.zip'
    with zipfile.ZipFile(zpath,'x',zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(archive.items()):z.write(p,n)
    with zipfile.ZipFile(zpath) as z:
        for n,h in inv.items():assert hashlib.sha256(z.read(n)).hexdigest()==h['SHA256']
    save(ROOT/'analysis/tail708-archive.json',dict(stage=708,
        location='WORKSPACE/probes/nes-tail708/'+a.out.name,files=len(inv),
        SHA256=sha(zpath),inventory_SHA256=sha(a.out/'inventory.json'),all_verified=True,
        raw_ROM=False,license=False))
    print(json.dumps(dict(candidates=list(results),selected=r['selected'],files=len(inv),query_budget=budget)))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
