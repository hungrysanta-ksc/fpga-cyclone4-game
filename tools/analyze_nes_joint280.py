# SPDX-License-Identifier: MIT
"""Reconcile actual new source bytes/ARM costs, output schedule and whole Lite."""
import argparse,collections,csv,difflib,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_decode280 import records,chunks
from elftools.elf.elffile import ELFFile


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();b=a.base.resolve();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    def csvs(p):return list(csv.DictReader(pin(p).open()))
    def ev(p):return list(csv.reader(pin(p/'joint-events.csv').open()))
    selected=['test05','window02','arm04','armguards01','spiguards02','rawguards02','guards02','board01']
    results={n:js(b/n/'result.json') for n in selected}
    assert all(r['passed'] for r in results.values())
    q=b/'test05';prior=BASE/'probes/nes-joint278';old=js(prior/'analysis01/result.json')
    oldcost={int(x['frame']):x for x in csvs(prior/'analysis01/costs.csv')}
    armrows={int(x['frame']):x for x in csvs(b/'arm04/frames.csv')}
    for n,h in results['test05']['rtl_hashes'].items():
        assert sha(pin(q/n))==h==sha(pin(b/'window02'/n))
        for tag in ('guards02','spiguards02'):
            if n in results[tag]['rtl_hashes']:assert results[tag]['rtl_hashes'][n]==h==sha(pin(b/tag/n))
    assert results['rawguards02']['RTL_sha256']==sha(pin(q/'nes_core257.sv'))
    assert results['rawguards02']['ARM_sha256']==results['arm04']['ELF_sha256']==results['armguards01']['ELF_sha256']
    assert pin(q/'source-ARM-decoder.elf').read_bytes()==pin(b/'arm04/decoder.elf').read_bytes()
    # These are the actual delays consumed by the source SPI testbench.
    for n in ('source-cost280.hex','source-length280.hex','source-expected280.hex','control280.hex','transaction-cost280.hex'):
        assert pin(q/n).read_bytes()==pin(b/'window02'/n).read_bytes()==pin(b/'guards02'/n).read_bytes(),n
    blockrows=csvs(b/'arm04/blocks.csv')
    for n,col in [('source-cost280.hex','instructions'),('source-length280.hex','length')]:
        assert [int(v,16) for v in (q/n).read_text().split()]==[int(r[col]) for r in blockrows],n
    for n in ('nes_output264.c','commands.hex','stream.hex','expected.hex','certs.hex','hashes.hex'):
        assert pin(q/n).read_bytes()==pin(prior/'test07'/n).read_bytes(),n
    with pin(q/'output.elf').open('rb') as nf,pin(prior/'test07/output.elf').open('rb') as of:
        newelf,oldelf=ELFFile(nf),ELFFile(of)
        for sec in newelf.iter_sections():
            if sec['sh_flags']&2:
                prev=oldelf.get_section_by_name(sec.name)
                assert prev is not None and sec.header==prev.header and sec.data()==prev.data(),sec.name
    for n in ('CPU-ordinary.sfc','CPU-bus.csv','CPU-timing.csv'):
        assert pin(q/n).read_bytes()==pin(BASE/'probes/nes-joint279/test01'/n).read_bytes(),n
    # Original host execution and independent validator are retained. Link
    # width is the common transaction context; no host-FSM saving is claimed.
    for n in ('nes_mux260.sv','nes_validator278.sv'):
        s=pin(q/n).read_text().replace('[106:0] link270','[48:0] link270')
        assert s==pin(prior/'test07'/n).read_text(),n
    frames=collections.defaultdict(list);tokens=[]
    for line in pin(q/'blocks.txt').read_text().splitlines():
        f,t,n,h=line.split();payload=bytes.fromhex(h);assert len(payload)==int(n)<=248
        frames[int(f)].append(payload);tokens.append(int(t))
    assert tokens==list(range(len(tokens))) and len(frames)==71
    for f in frames:
        rr=records(pin(q/f'frame{f}.records'));oracle=records(pin(b/'arm04'/f'frame{f}.records'))
        assert rr==oracle and chunks(rr)==frames[f],f
    def costs(folder):
        events=ev(folder);sc={int(x['frame']):x for x in csvs(folder/'cycles.csv')}
        done={int(x[1]):int(x[3])/1e9 for x in events if x[0]=='frame_done'};out=[]
        for f in sorted(done):
            tr=js(folder/f'arm{f}.json')['transfers']
            actual=[x['tx'] for x in tr if x['tx'].startswith('e1')]
            expected=[x['tx'] for x in js(prior/'test07'/f'arm{f}.json')['transfers'] if x['tx'].startswith('e1')]
            assert actual==expected,f
            spi=[x for x in events if x[0]=='arm267' and int(x[1])==f]
            total=int(sc[f]['total'])*45.454/1e6+done[f]
            out.append(dict(frame=f,source_ms=int(sc[f]['total'])*45.454/1e6,
                output_ms=done[f],diagnostic_serial_ms=total,prior278_ms=float(oldcost[f]['diagnostic_serial_ms']),
                delta278_ms=total-float(oldcost[f]['diagnostic_serial_ms']),budget_gap_ms=total-1000/60,
                payload=int(armrows[f]['payload']),blocks=int(armrows[f]['blocks']),
                source_decode_instructions=int(armrows[f]['instructions']),
                source_decode_CPI1_ms=int(armrows[f]['instructions'])/84000,
                frozen_source_decode_CPI2_ms=total+int(armrows[f]['instructions'])/84000,
                frozen_source_decode_CPI_room=1+(1000/60-total)/(int(armrows[f]['instructions'])/84000),
                E2=sum(int(x[2])==226 for x in spi),output_SPI_bytes=sum(int(x[3]) for x in spi),
                ARM_IRQ_event_instructions=sum(int(x[5]) for x in spi),
                absolute_end_ms=next(int(x[2])/1e9 for x in events if x[0]=='frame_done' and int(x[1])==f)))
        return out,events
    rows,events=costs(q);window,wevents=costs(b/'window02')
    assert len(rows)==71 and len(window)==3
    assert sum(x[0]=='cpu267' for x in events)==544
    assert sum(x[0]=='receipt' for x in events)==2069
    assert max(int(x[2]) for x in events if x[0]=='credits')==4
    with (d/'costs.csv').open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    def mapping(folder):
        summary=pin(folder/'output_files/board.map.summary').read_text();m={}
        for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:
            m[k]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',summary).group(1).replace(',',''))
        rpt=pin(folder/'output_files/board.map.rpt').read_text();own={}
        for line in rpt.splitlines():
            f=[v.strip() for v in line.split(';')]
            if len(f)==14 and re.fullmatch(r'\d+ \(\d+\)',f[2]):
                own[f[10]]={k:int(re.search(r'\((\d+)\)',f[i]).group(1)) for k,i in [('comb',2),('FF',3)]}
        assert {k:sum(v[k] for v in own.values()) for k in ('comb','FF')}=={k:m[k] for k in ('comb','FF')}
        return m,own,rpt
    m,own,rpt=mapping(b/'board01');before,oldown,_=mapping(prior/'board01')
    # Inherited MAP result.input_hashes describe the seed before patch().
    # Pin every actual compiler source/configuration separately.
    board_inputs={}
    for p in sorted((b/'board01').rglob('*')):
        rel=p.relative_to(b/'board01')
        if p.is_file() and not any(x in ('db','incremental_db','output_files') for x in rel.parts) and p.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
            board_inputs[rel.as_posix()]=sha(pin(p))
    changes=[dict(path=k,before=oldown.get(k,dict(comb=0,FF=0)),after=own.get(k,dict(comb=0,FF=0)))
        for k in sorted(own.keys()|oldown.keys()) if own.get(k)!=oldown.get(k)]
    assert sum(v['after']['comb']-v['before']['comb'] for v in changes)==m['comb']-before['comb']
    def region(part):return sum(v['comb'] for k,v in own.items() if part in k)
    regions=dict(source=region('nes_core257:encoder'),source_transport=region('nes_transport257:transport'),
        SPI=region('nes_spi270:spi_front270'),
        plan=region('nes_plan_batch206:transport')+region('nes_plan_spi200:endpoint'),
        host=sum(v['comb'] for k,v in own.items() if k.endswith('nes_output260:flow')),
        queue=region('nes_queue260:queue'),validator=region('nes_validator278:validator'))
    regions['expanded']=sum(regions.values())
    regions['endpoint']=regions['expanded']-regions['source']-regions['validator']
    regions['endpoint_budget']=regions['endpoint']-(m['comb']-15408)
    regions['expanded_budget']=regions['expanded']-(m['comb']-15408)
    regions['outside']=m['comb']-regions['expanded']
    # Board wrappers differ from simulation by the same established tile and
    # physical bus connections. All newly edited leaf RTL is byte-identical.
    board_binding={}
    for n in ['nes_core257.sv','nes_transport257.sv','nes_spi270.sv','nes_plan_spi200.sv','nes_queue260.sv','nes_validator278.sv']:
        assert pin(q/n).read_bytes()==pin(b/'board01'/n).read_bytes(),n
        board_binding[n]=sha(q/n)
    for n in ['nes_joint257.sv','nes_joint266.sv','nes_mux260.sv']:
        def delta(x,y):
            return [v for v in difflib.unified_diff(x.splitlines(),y.splitlines(),n=0) if v.startswith(('+','-')) and not v.startswith(('+++','---'))]
        expected=delta(pin(prior/'test07'/n).read_text(),pin(prior/'board01'/n).read_text())
        expected=[v.replace('[48:0] link270','[106:0] link270') for v in expected]
        actual=delta(pin(q/n).read_text(),pin(b/'board01'/n).read_text())
        assert actual==expected,(n,actual,expected);board_binding[n]=actual
    warm=[r for r in rows if r['frame']>=907]
    priorwindow={r['frame']:r for r in old['restricted_ROM']}
    for r in window:
        r['prior278_ms']=priorwindow[r['frame']]['diagnostic_serial_ms']
        r['delta278_ms']=r['diagnostic_serial_ms']-r['prior278_ms']
    counts=re.search(r'COUNTS278 tap=(\d+) mask=(\d+) provisional=(\d+) orderedACK=(\d+)',pin(q/'vsim.log').read_text())
    assert counts
    counters=dict(zip(['original_body_reads','deferred_mask_writes','provisional_CRC','ordered_ACK'],map(int,counts.groups())))
    assert counters==dict(original_body_reads=17277,deferred_mask_writes=638*71,provisional_CRC=32,ordered_ACK=793)
    result=dict(passed=True,stage=280,selected=selected,frames=71,source_blocks=len(tokens),source_bytes=sum(r['payload'] for r in rows),
        prior_source_bytes=83240,CPU_commands=544,map_ranges=2069,max_credit=4,
        source_canonical_bytes=348610,ARM=results['arm04'],ARM_guards=results['armguards01']['rejects'],
        raw_guards=results['rawguards02'],SPI_guards=results['spiguards02']['log'],STOP_guards=results['guards02']['guards'],
        warm_max=max(warm,key=lambda r:r['diagnostic_serial_ms']),
        warm_over=[r['frame'] for r in warm if r['diagnostic_serial_ms']>1000/60],
        frame954=next(r for r in rows if r['frame']==954),restricted_ROM=window,
        restricted_end_ms=window[-1]['absolute_end_ms'],
        prior_restricted_end_ms=max(int(x[2])/1e9 for x in ev(prior/'window01') if x[0]=='frame_done'),
        whole_MAP=m,prior_whole_MAP=before,whole_delta={k:m[k]-before[k] for k in m},
        area_deficit=m['comb']-15408,regions=regions,whole_own_changes=changes,board_binding=board_binding,actual_MAP_inputs=board_inputs,
        base_hi_RAM=[l for l in rpt.splitlines() if 'base_hi' in l and 'Single Port' in l],
        counters=counters,host_execution_replaced=False,independent_validator_retained=True,
        full_path_ms=None,P2_selected=False,FIT=False,STA=False,physical=False,
        limits=['CPI1/84MHz is instruction sensitivity, not hardware cycle bound.',
          'Source ARM codec/control measured offline, block-byte-bound cost replay. Output serializer/refill/IRQ bodies execute live.',
          'Geometry planner, full RUN/NVIC, active VBlank and live CPU/FPGA co-simulation remain open.',
          'Raw cache supports 0..2 patches; larger counts reject before writes.',
          'Request-state sharing replaces source/plan fields and output CRC, not host output execution FSM.',
          'Whole comb gate still fails; no placement or area gain is claimed.'],
        input_hashes=pins,script_sha256=sha(Path(__file__)))
    (d/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['passed','source_bytes','warm_max','warm_over','whole_MAP','whole_delta','area_deficit']},ensure_ascii=False))


if __name__=='__main__':main()
