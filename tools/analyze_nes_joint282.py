# SPDX-License-Identifier: MIT
"""Same-frame ARM/SPI/ROM schedule and whole Lite cost of direct host282."""
import argparse,csv,json,re,difflib,sys,hashlib
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    b=a.base.resolve();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    def cs(p):return list(csv.DictReader(pin(p).open()))
    def ev(p):return list(csv.reader(pin(p/'joint-events.csv').open()))
    prior=BASE/'probes/nes-joint280';old=js(ROOT/'analysis/joint280-verification.json')
    before={int(r['frame']):r for r in cs(ROOT/'analysis/joint280-costs.csv')}
    tags=['test04','window01','guards01','armguards01','spiguards01','board01']
    checks={t:js(b/t/'result.json') for t in tags};assert all(r['passed'] for r in checks.values())
    q=b/'test04';r=checks['test04'];assert r['frames']==71 and checks['window01']['frames']==3
    source={r['frame']:r for r in old['ARM']['frames']}
    for n in r['rtl_hashes']:
        assert sha(pin(q/n))==r['rtl_hashes'][n]==sha(pin(b/'window01'/n)),n
    for n,h in checks['guards01']['rtl_hashes'].items():
        assert h==sha(pin(b/'guards01'/n))
        if n in r['rtl_hashes']:assert h==r['rtl_hashes'][n],n
    for n,h in checks['spiguards01']['rtl_hashes'].items():assert h==sha(pin(q/n)),n
    # GCC gives the assembly temporary object a random STT_FILE name. Normalize
    # exactly that non-allocated string; every other byte of the ELF must match.
    sys.path.insert(0,str(BASE/'.tools/arm259-python'))
    from elftools.elf.elffile import ELFFile
    elf_binding={}
    for tag,expected in [('test04',r['ELF_sha256']),('window01',checks['window01']['ELF_sha256']),('armguards01',checks['armguards01']['ELF_sha256'])]:
        path=pin(b/tag/'output.elf');assert sha(path)==expected
        raw=bytearray(path.read_bytes());names=[]
        with path.open('rb') as fp:
            elf=ELFFile(fp);strings=elf.get_section_by_name('.strtab')
            assert not strings['sh_flags']&2
            for symbol in elf.get_section_by_name('.symtab').iter_symbols():
                if symbol['st_info']['type']=='STT_FILE' and re.fullmatch(r'cc[A-Za-z0-9]{6}\.o',symbol.name):
                    at=strings['sh_offset']+symbol['st_name'];name=symbol.name.encode()
                    assert raw[at:at+len(name)]==name
                    raw[at:at+len(name)]=b'ccXXXXXX.o';names.append(dict(name=symbol.name,offset=at))
        assert len(names)==1
        elf_binding[tag]=dict(raw_sha256=expected,nonallocated_STT_FILE=names,normalized_sha256=hashlib.sha256(raw).hexdigest())
    assert len({x['normalized_sha256'] for x in elf_binding.values()})==1,elf_binding
    for n in ('source-cost280.hex','source-length280.hex','source-expected280.hex','transaction-cost280.hex','control280.hex',
              'source-ARM-decoder.elf','certs.hex','hashes.hex','CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc'):
        assert pin(q/n).read_bytes()==pin(prior/'test05'/n).read_bytes()==pin(b/'window01'/n).read_bytes(),n
    assert pin(q/'nes_core257.sv').read_bytes()==pin(prior/'test05/nes_core257.sv').read_bytes()
    assert pin(q/'blocks.txt').read_bytes()==pin(prior/'test05/blocks.txt').read_bytes()
    # prepare261 rebuilds sparse receipts only through LAST. The unexecuted
    # tail in a 3-frame fixture still contains legacy gap16 coverage.
    normal_expected=pin(q/'expected.hex').read_text()
    window_expected=pin(b/'window01/expected.hex').read_text()
    assert normal_expected==pin(prior/'test05/expected.hex').read_text()
    assert window_expected==pin(prior/'window02/expected.hex').read_text()
    assert bytes.fromhex(normal_expected)[:3*754]==bytes.fromhex(window_expected)[:3*754]
    for n in ('nes_output264.c','nes_refill267.c'):
        assert pin(q/n).read_bytes()==pin(b/'window01'/n).read_bytes()
    packets=0;normalization=[]
    for f in range(905,976):
        a=js(q/f'arm{f}.json');o=js(prior/'test05'/f'arm{f}.json');assert a['ok']==1
        def commands(x,op):return [bytes.fromhex(t['tx']) for t in x['transfers'] if bytes.fromhex(t['tx'])[0]==op]
        e1=commands(a,225);assert e1==commands(o,225),f
        assert commands(a,233)==commands(o,233),f
        for t in a['transfers']:
            tx=bytes.fromhex(t['tx']);rx=bytes.fromhex(t['rx'])
            if tx[0] in (225,233) and len(tx)>=12:
                c=0
                for byte in rx[1:11]:
                    c^=byte
                    for _ in range(8):c=((c<<1)^7 if c&128 else c<<1)&255
                assert rx[1]==250 and rx[11]==c,(f,tx[0])
                normalization.append((f,tx[0]))
        packets+=len(e1)
    assert packets==1231
    oldevents=ev(prior/'test05')
    oldspi={f:[e for e in oldevents if e[0]=='arm267' and int(e[1])==f] for f in range(905,976)}
    def costs(folder,oldrows):
        events=ev(folder);sc={int(x['frame']):x for x in cs(folder/'cycles.csv')};rows=[];prev=[0,0,0]
        for done in (e for e in events if e[0]=='frame_done'):
            f=int(done[1]);es=[e for e in events if int(e[1])==f];spi=[e for e in es if e[0]=='arm267']
            counts=list(map(int,next(e for e in es if e[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counts,prev)];prev=counts
            src=int(sc[f]['total'])*45.454/1e6;out=int(done[3])/1e9;total=src+out
            oldrow=oldrows[f];oldtotal=float(oldrow['diagnostic_serial_ms'])
            row=dict(frame=f,source_ms=src,output_ms=out,diagnostic_serial_ms=total,prior280_ms=oldtotal,delta280_ms=total-oldtotal,
                margin_ms=1000/60-total,absolute_end_ms=int(done[2])/1e9,
                source_codec_instructions=source[f]['instructions'],frozen_source_CPI2_ms=total+source[f]['instructions']/84000,
                E0=sum(int(e[2])==224 for e in spi),E1=sum(int(e[2])==225 for e in spi),E2=sum(int(e[2])==226 for e in spi),
                E8=sum(int(e[2])==232 for e in spi),E9=sum(int(e[2])==233 for e in spi),
                output_SPI_bytes=sum(int(e[3]) for e in spi),ARM_IRQ_event_instructions=sum(int(e[5]) for e in spi),
                parser_ms=sum(int(e[3]) for e in es if e[0]=='parser')/1e9,
                receipt_ms=sum(int(e[3]) for e in es if e[0]=='receipt')/1e9,
                tile_wait_cycles=inc[0],slot_wait_cycles=inc[1],core_priority_blocks=inc[2])
            rows.append(row)
        return rows,events
    rows,events=costs(q,before);window,_=costs(b/'window01',{r['frame']:r for r in old['restricted_ROM']})
    assert len(rows)==71 and len(window)==3
    assert sum(e[0]=='cpu267' for e in events)==544
    assert sum(e[0]=='receipt' for e in events)==2069
    assert max(int(e[2]) for e in events if e[0]=='credits')<=4
    for row in rows:
        previous=oldspi[row['frame']]
        for key,opcode in [('E0',224),('E2',226),('E8',232)]:
            row['prior280_'+key]=sum(int(e[2])==opcode for e in previous)
        row['prior280_SPI_bytes']=sum(int(e[3]) for e in previous)
        row['prior280_ARM_IRQ_instructions']=sum(int(e[5]) for e in previous)
    def mapping(folder):
        summary=pin(folder/'output_files/board.map.summary').read_text();m={}
        for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:
            m[k]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',summary).group(1).replace(',',''))
        rpt=pin(folder/'output_files/board.map.rpt').read_text();own={}
        for line in rpt.splitlines():
            f=[v.strip() for v in line.split(';')]
            if len(f)==14 and re.fullmatch(r'\d+ \(\d+\)',f[2]):own[f[10]]={k:int(re.search(r'\((\d+)\)',f[i]).group(1)) for k,i in [('comb',2),('FF',3)]}
        assert sum(v['comb'] for v in own.values())==m['comb']
        return m,own
    m,own=mapping(b/'board01');om,oo=mapping(prior/'board01')
    warnings=js(b/'warning-audit.json')
    for n,h in warnings['input_hashes'].items():assert sha(pin(Path(n)))==h
    report=(b/'board01/output_files/board.map.rpt').read_text()
    fsm=['nes_validator278:validator|state','nes_core257:encoder|state',
         'nes_output260:flow|state','nes_output260:flow|tap_state278','nes_plan_batch206:transport|state']
    for path in fsm:assert any(path in line for line in report.splitlines() if 'State Machine - ' in line),path
    changes=[dict(path=k,before=oo.get(k,dict(comb=0,FF=0)),after=own.get(k,dict(comb=0,FF=0))) for k in sorted(own.keys()|oo.keys()) if own.get(k)!=oo.get(k)]
    assert sum(x['after']['comb']-x['before']['comb'] for x in changes)==m['comb']-om['comb']
    def region(part):return sum(v['comb'] for k,v in own.items() if part in k)
    regions=dict(host=sum(v['comb'] for k,v in own.items() if k.endswith('nes_output260:flow')),
        validator=region('nes_validator278:validator'),queue=region('nes_queue260:queue'),
        plan=region('nes_plan_batch206:transport')+region('nes_plan_spi200:endpoint'))
    regions['selected']=sum(regions.values());regions['outside']=m['comb']-regions['selected'];regions['budget']=15408-regions['outside']
    # Bind actual compiler inputs, then preserve the established board-vs-test bus wiring delta.
    for rel,h in checks['board01']['actual_inputs'].items():assert sha(pin(b/'board01'/rel))==h
    for line in (b/'board01/board.qsf').read_text().splitlines():
        match=re.fullmatch(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL|SDC|QIP)_FILE (.+)',line)
        if match:
            rel=match[1].strip('"').replace('\\','/')
            assert rel in checks['board01']['actual_inputs'],('unpinned QSF input',rel)
    for n in ('nes_core257.sv','nes_spi270.sv','nes_plan_spi200.sv','nes_queue260.sv','nes_validator278.sv'):
        assert pin(q/n).read_bytes()==pin(b/'board01'/n).read_bytes(),n
    transport_a=pin(q/'nes_transport257.sv').read_text();transport_b=pin(b/'board01/nes_transport257.sv').read_text()
    assert [line for line in transport_a.splitlines() if line.strip()]==[line for line in transport_b.splitlines() if line.strip()]
    transport_whitespace=list(difflib.unified_diff(transport_a.splitlines(),transport_b.splitlines(),n=0))
    binding={}
    for n in ('nes_mux260.sv','nes_joint257.sv','nes_joint266.sv'):
        def delta(x,y):return [v for v in difflib.unified_diff(x.splitlines(),y.splitlines(),n=0) if v.startswith(('+','-')) and not v.startswith(('+++','---'))]
        expected=delta(pin(prior/'test05'/n).read_text(),pin(prior/'board01'/n).read_text())
        expected=[v.replace('[106:0] link270','[107:0] link270') for v in expected]
        actual=delta(pin(q/n).read_text(),pin(b/'board01'/n).read_text());assert actual==expected,(n,actual,expected);binding[n]=actual
    s=(q/'nes_mux260.sv').read_text()
    assert all(x not in s for x in ('consumer_word','event_return','task event264','manifest_at<=','manifest_phase<='))
    warm=[r for r in rows if r['frame']>=907]
    warm_max=max(warm,key=lambda r:r['diagnostic_serial_ms'])
    frozen_max=max(warm,key=lambda r:r['frozen_source_CPI2_ms'])
    restricted_warm=[r for r in window if r['frame']>=907]
    result=dict(passed=True,stage=282,selected=tags,frames=71,packets=packets,CPU_commands=544,map_ranges=2069,
        progress_snapshots=len(normalization),compressed_E1_E9_bytes_unchanged=True,source_bytes=47900,max_credit=4,
        warm_delta_range_ms=[min(r['delta280_ms'] for r in rows if r['frame']>=907),max(r['delta280_ms'] for r in rows if r['frame']>=907)],
        warm_max=warm_max,warm_over=[r['frame'] for r in warm if r['margin_ms']<0],
        time_budget=dict(frame_limit_ms=1000/60,planning_reserve_ms=0.5,
          normal_gap_ms=max(0,-warm_max['margin_ms']),normal_to_reserve_ms=max(0,0.5-warm_max['margin_ms']),
          frozen_source_CPI2_worst_frame=frozen_max['frame'],frozen_source_CPI2_max_ms=frozen_max['frozen_source_CPI2_ms'],
          frozen_source_CPI2_gap_ms=max(0,frozen_max['frozen_source_CPI2_ms']-1000/60),
          restricted_warm_gap_ms=max(0,max(r['diagnostic_serial_ms'] for r in restricted_warm)-1000/60)),
        heavy=[r for r in rows if r['frame'] in (952,954,955,962,963,968,970)],restricted_ROM=window,
        restricted_end_delta_ms=window[-1]['absolute_end_ms']-old['restricted_end_ms'],
        whole_MAP=m,prior_whole_MAP=om,whole_delta={k:m[k]-om[k] for k in m},area_deficit=m['comb']-15408,
        own_changes=changes,regions=regions,board_binding=binding,transport_blank_line_difference=transport_whitespace,
        MAP_warning_changes=warnings,FSM_extracted=fsm,
        ARM_size=pin(q/'size-rom.log').read_text(),ARM_stack=r['ARM']['stack_observed'],
        ARM_ELF_binding=elf_binding,
        ARM_guards=checks['armguards01'],SPI_guards=checks['spiguards01']['log'],STOP_guards=checks['guards01']['guards'],
        new_RTL=True,new_ARM=True,new_MAP=True,new_CPU=False,full_path_ms=None,P2_selected=False,FIT=False,STA=False,physical=False,
        limits=['Source ARM offline block-specific instruction replay; output ARM live, CPI1/84MHz is not hardware WCET.',
          'Independent validator predicate/RAM micro-FSM, SNES tap, plan banks/reader/CRC/CDC remain. No claim of a monolithic whole engine.',
          'Whole count includes outside-region synthesis changes, no inclusive parent/child subtraction.',
          'CPU279 bus traces reused; no new live65816/fullRUN/NVIC/activeVBlank/full program linking/physical60fps.',
          'Command-start snapshot excludes current packet acceptance; errors and full/tile waits retain checked status fallback.'],
        input_hashes=pins,script_sha256=sha(Path(__file__)))
    with (d/'costs.csv').open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
    (d/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:result[k] for k in ('passed','warm_max','warm_over','whole_MAP','whole_delta','area_deficit','restricted_ROM','regions')},ensure_ascii=False))


if __name__=='__main__':main()
