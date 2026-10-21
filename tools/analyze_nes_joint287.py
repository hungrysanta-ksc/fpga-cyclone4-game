# SPDX-License-Identifier: MIT
"""Reconcile actual planner/refill bytes, retimed schedules and whole Lite MAP."""
import argparse,collections,csv,json,re,struct,difflib
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    b=a.base.resolve();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    previous=js(ROOT/'analysis/joint286-verification.json')
    tags=['arm02','armguard01','rowguard03','irqguard02','h2guard03','guards02','range03','test06','window01','board01']
    r={t:js(b/t/'result.json') for t in tags};assert all(x['passed'] for x in r.values())
    assert len(r['arm02']['frames'])==71 and r['arm02']['metadata_bytes_per_frame']==8570
    assert r['arm02']['script_sha256']==sha(pin(ROOT/'tools/probe_nes_planner287.py'))
    for n,h in r['arm02']['input_hashes'].items():assert sha(pin(Path(n)))==h,n
    for n,h in r['arm02']['generated_hashes'].items():assert sha(pin(b/'arm02'/n))==h,n
    assert len(r['armguard01']['checks'])==15 and len(r['rowguard03']['checks'])==5
    assert r['guards02']['guards']==[62,63]
    inherited=[3,23,24]+list(range(39,53))+list(range(56,62))
    for n in inherited:
        log=pin(b/'guards01'/f'guard{n}.log').read_text(errors='replace')
        assert f'PASS HOST278 GNEG={n}' in log and not re.search(r'\*\* (Fatal|Error):',log),n
    assert r['irqguard02']['row_plan_exact'] and len(r['irqguard02']['row_preemption287'])==1
    for tag,script in [('armguard01','guard_nes_planner286.py'),('rowguard03','guard_nes_rows287.py'),('h2guard03','guard_nes_h2287.py')]:
        assert r[tag]['script_sha256']==sha(pin(ROOT/'tools'/script))
    assert r['irqguard02']['guard287_sha256']==sha(pin(ROOT/'tools/guard_nes_irq287.py'))
    assert r['irqguard02']['adapter_sha256']==sha(pin(ROOT/'tools/probe_nes_live287.py'))
    assert r['range03']['test_sha256']==sha(pin(b/'range03/range283_tb.sv'))
    assert r['guards02']['TB_sha256']==sha(pin(b/'guards02/joint266_tb.sv'))
    for n in ('nes_joint287.py','guard_nes_joint287.py'):assert r['guards02']['entry_hashes'][n]==sha(pin(ROOT/'tools'/n))
    def allocated(p):
        data=pin(p).read_bytes();assert data[:6]==b'\x7fELF\x01\x01'
        offset=struct.unpack_from('<I',data,32)[0];size,count=struct.unpack_from('<HH',data,46);sections=[]
        for i in range(count):
            h=struct.unpack_from('<10I',data,offset+i*size)
            if h[2]&2:sections.append((h[1:4],h[5],b'' if h[1]==8 else data[h[4]:h[4]+h[5]]))
        return sections
    assert allocated(b/'irqguard02/output.elf')==allocated(b/'test06/output.elf')
    assert r['h2guard03']['ELF_sha256']==r['test06']['ELF_sha256'] and len(r['h2guard03']['checks'])==8
    for tag in ('armguard01','rowguard03'):assert r[tag]['ELF_sha256']==r['arm02']['generated_hashes']['planner.elf']
    planner=[];pa={x['frame']:x for x in previous['planner']}
    source_cost=[int(x,16) for x in pin(b/'test06/source-cost280.hex').read_text().split()];source_at=0;decoder_delta={}
    for row in r['arm02']['frames']:
        f=row['frame'];old=pa[f]['new286_ms'];new=row['postdecode_CPI1_ms']
        n=row['blocks'];old_decoder=sum(source_cost[source_at:source_at+n]);source_at+=n
        decoder_delta[f]=row['decoder_instructions']-old_decoder
        assert decoder_delta[f]==5*n,(f,'probe-only block286 wrapper')
        planner.append(dict(frame=f,rows_reused=row['rows_reused287'],rows_full=row['rows_full287'],old286_ms=old,new287_ms=new,delta_ms=new-old,components=row['components'],steps=row['steps']))
        assert row['rows_reused287']+row['rows_full287']==29
        assert row['plan_bytes']<=8192-6
    assert source_at==len(source_cost)
    schedules={}
    for tag,count,oldrows in [('test06',71,previous['normal']),('window01',3,previous['restricted_ROM'])]:
        q=b/tag;result=r[tag];assert result['frames']==count
        assert result['input_hashes']['nes_joint287.py']==sha(pin(ROOT/'tools/nes_joint287.py'))
        assert result['input_hashes']['probe_nes_live287.py']==sha(pin(ROOT/'tools/probe_nes_live287.py'))
        assert result['ELF_sha256']==sha(pin(q/'output.elf'))
        assert result['tb_sha256']==sha(pin(q/'joint266_tb.sv'))
        for n,h in result['rtl_hashes'].items():assert sha(pin(q/n))==h==r['test06']['rtl_hashes'][n]
        for p in q.iterdir():
            if p.suffix in ('.c','.h','.inc','.s','.ld'):pin(p)
        for guard in ('guards02','range03'):
            if guard=='range03':assert r[guard]['rtl_sha256']==result['rtl_hashes']['nes_validator278.sv']
            else:
                for n,h in r[guard]['rtl_hashes'].items():
                    assert sha(pin(b/guard/n))==h
                    assert sha(pin(b/'guards01'/n))==h
                    if n in result['rtl_hashes']:assert h==result['rtl_hashes'][n],(guard,n)
        source={int(x['frame']):x for x in csv.DictReader(pin(q/'cycles.csv').open())}
        events=list(csv.reader(pin(q/'joint-events.csv').open()));old={x['frame']:x for x in oldrows};rows=[];prev=[0,0,0]
        for event in (e for e in events if e[0]=='frame_done'):
            f=int(event[1]);es=[e for e in events if int(e[1])==f];spi=[e for e in es if e[0]=='arm267'];wait=[e for e in es if e[0]=='wait284'];checkpoint=[e for e in es if e[0]=='checkpoint287']
            end=next(e for e in es if e[0]=='armdone284');counters=list(map(int,next(e for e in es if e[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counters,prev)];prev=counters
            src=int(source[f]['total'])*45.454/1e6;out=int(event[3])/1e9;total=src+out
            frame=next(x for x in result['ARM']['frames'] if x['frame']==f)
            now=js(q/f'arm{f}.json');then=js(BASE/'probes/nes-joint286'/('test01' if tag=='test06' else 'window01')/f'arm{f}.json')
            for op in (225,233):
                select=lambda v:[t['tx'] for t in v['transfers'] if t['tx'] and bytes.fromhex(t['tx'])[0]==op]
                assert select(now)==select(then),(tag,f,op)
            # Final finish/commit requests follow the snapshot; use event counts
            # for totals, and the snapshot for byte equality of E1/E9 payloads.
            rows.append(dict(frame=f,source_ms=src,output_with_live_planner_ms=out,diagnostic_serial_ms=total,prior286_ms=old[f]['diagnostic_serial_ms'],
                delta_ms=total-old[f]['diagnostic_serial_ms'],margin_ms=1000/60-total,absolute_end_ms=int(event[2])/1e9,
                E2=sum(int(e[2])==226 for e in spi),E9=sum(int(e[2])==233 for e in spi),SPI_bytes=sum(int(e[3]) for e in spi),
                charged_ARM_instructions=sum(int(e[5]) for e in spi)+sum(int(e[4]) for e in wait)+sum(int(e[3]) for e in checkpoint)+int(end[3]),
                IRQ_waits=len(wait),timer_fallbacks=sum(int(e[2])==0 for e in wait),checkpoints=len(checkpoint),
                rows_reused=frame['rows_reused'],rows_full=frame['rows_full'],prefills=frame['prefills'],
                uncharged_material_probe_wrapper_instructions=decoder_delta[f],wrapper_CPI1_sensitivity_us=decoder_delta[f]/84,
                tile_wait_cycles=inc[0],slot_wait_cycles=inc[1],core_priority_blocks=inc[2]))
            assert len(checkpoint)==31 and frame['commit']==1187
        assert len(rows)==count
        if tag=='window01':assert sum(x['core_priority_blocks'] for x in rows)>0
        schedules[tag]=rows
    def mapping(folder):
        s=pin(folder/'output_files/board.map.summary').read_text();whole={}
        for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:whole[k]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',s).group(1).replace(',',''))
        own={}
        for line in pin(folder/'output_files/board.map.rpt').read_text().splitlines():
            f=[x.strip() for x in line.split(';')]
            if len(f)==14 and re.fullmatch(r'\d+ \(\d+\)',f[2]):own[f[10]]={k:int(re.search(r'\((\d+)\)',f[i]).group(1)) for k,i in [('comb',2),('FF',3)]}
        assert sum(x['comb'] for x in own.values())==whole['comb'];return whole,own
    board=b/'board01';whole,own=mapping(board);oldwhole,oldown=mapping(BASE/'probes/nes-joint286/board01')
    for n,h in r['board01']['actual_inputs'].items():assert sha(pin(board/n))==h
    for n in ('nes_mux260.sv','nes_validator278.sv','nes_joint257.sv','nes_joint266.sv','nes_plan_batch206.sv','nes_plan_spi200.sv','nes_spi270.sv'):
        actual=pin(board/n).read_bytes();sim=pin(b/'test06'/n).read_bytes()
        if n=='nes_mux260.sv':actual=actual.replace(b' output wire tile_closed267,\n',b'').replace(b' reg tiles_closed;assign tile_closed267=tiles_closed;',b' reg tiles_closed;')
        if n=='nes_joint266.sv':
            # Preserve exactly the previous board/external-lease glue delta.
            delta=lambda x,y:[line for line in difflib.ndiff(x.decode().splitlines(),y.decode().splitlines()) if line.startswith(('- ','+ '))]
            oldboard=pin(BASE/'probes/nes-joint286/board01'/n).read_bytes()
            oldsim=pin(BASE/'probes/nes-joint286/test01'/n).read_bytes()
            assert delta(actual,sim)==delta(oldboard,oldsim),n
            for anchor in (b'.crc_reset287(crc_reset287)',b'.v_descriptor287(v_range_valid)'):assert actual.count(anchor)==sim.count(anchor)
        else:assert actual==sim,n
    region=lambda key:sum(v['comb'] for k,v in own.items() if key in k)
    regions=dict(host=sum(v['comb'] for k,v in own.items() if k.endswith('nes_output260:flow')),validator=region('nes_validator278:validator'),queue=region('nes_queue260:queue'),plan=region('nes_plan_batch206:transport')+region('nes_plan_spi200:endpoint'),SPI=region('nes_spi270:spi_front270'))
    selected=sum(regions.values());outside=whole['comb']-selected;budget=15408-outside
    glue_suffixes=('nes_joint267_board:native_joint267','nes_joint257:core')
    glue=sum(v['comb'] for k,v in own.items() if k.endswith(glue_suffixes))
    oldglue=sum(v['comb'] for k,v in oldown.items() if k.endswith(glue_suffixes))
    expanded=selected+glue;oldexpanded=previous['area']['selected']+oldglue
    expanded_outside=whole['comb']-expanded;expanded_budget=15408-expanded_outside
    changes=[dict(path=k,before=oldown.get(k,dict(comb=0,FF=0)),after=own.get(k,dict(comb=0,FF=0))) for k in sorted(own.keys()|oldown.keys()) if own.get(k)!=oldown.get(k)]
    def warnings(p):return collections.Counter((c,re.sub(r'(\.s[vh]|\.v|\.tdf)\(\d+\)',r'\1(LINE)',t.split(' File: ')[0])) for c,t in re.findall(r'Warning \((\d+)\): ([^\r\n]+)',pin(p).read_text(errors='replace')))
    oldwarn=warnings(BASE/'probes/nes-joint286/board01/map.log');newwarn=warnings(board/'map.log')
    area=dict(whole_MAP=whole,prior_MAP=oldwhole,delta={k:whole[k]-oldwhole[k] for k in whole},regions=regions,selected=selected,outside=outside,budget=budget,target_with_128_reserve=budget-128,
              selected_delta=selected-previous['area']['selected'],outside_delta=outside-previous['area']['outside'],deficit=whole['comb']-15408,instance_changes=changes,
              glue_own=glue,prior_glue_own=oldglue,expanded_boundary=expanded,prior_expanded_boundary=oldexpanded,expanded_delta=expanded-oldexpanded,
              expanded_outside=expanded_outside,expanded_outside_delta=expanded_outside-(oldwhole['comb']-oldexpanded),expanded_budget=expanded_budget,expanded_target_with_128_reserve=expanded_budget-128,
              warnings=dict(before=sum(oldwarn.values()),after=sum(newwarn.values()),added=list((newwarn-oldwarn).elements()),removed=list((oldwarn-newwarn).elements())))
    warm=schedules['test06'][2:];worst=max(warm,key=lambda x:x['diagnostic_serial_ms'])
    result=dict(passed=True,stage=287,selected=tags,inherited_guards_from_partial_run=inherited,planner=planner,normal=schedules['test06'],restricted_ROM=schedules['window01'],warm_max=worst,warm_over=[x['frame'] for x in warm if x['margin_ms']<0],warm_regressions=[x for x in warm if x['delta_ms']>0],area=area,
       ARM=dict(planner_size=r['arm02']['size'],live_size=pin(b/'test06/size287.log').read_text(),observed_stack=r['test06']['ARM']['stack_observed'],rows_reused=sum(x['rows_reused'] for x in planner),rows_full=sum(x['rows_full'] for x in planner),maximum_plan_bytes_with_END=max(x['plan_bytes'] for x in r['arm02']['frames'])+6),
       full_path_ms=None,FIT=False,STA=False,P2_selected=False,physical=False,input_hashes=pins,script_sha256=sha(Path(__file__)),
       limits=['Same ELF executes canonical decoder, row planner, credited E9 serializer, output refill and EXTI. Actual plans/material checked, ordinary command templates retained.',
       'Source SPI and decoder/control instruction costs retain prior280 replay. Decoder material execution is excluded from live output charge to avoid double counting; its probe-only block286 wrapper is5 instructions/block beyond original block280 (10..130/frame), separately listed as an unretimed sensitivity. Full source firmware/RUN not executed.',
       'Cooperative group checkpoints advance RTL and deliver GPIO. Directed actual EXTI inside row touch preserves exception frame and plan, but arbitrary-phase full IRQ/WCET is not proven.',
       '2 credited plan RAM banks are bounded; 8192B planner output remains diagnostic storage, not a bounded target-memory claim. H2 reads immutable native fields; the 8570B flat copy was removed. No input-before-COMMITTED speculative lease.',
       'CPU279 ordinary bus traces reused; tile/map/final display bus models retained. CPI1/84MHz and 24 exception cycles are explicit allocations, not physical60fps.',
       'Whole MAP saving and selected-boundary delta are reported separately; no whole FIT/STA or free subtraction of inclusive parents.'])
    for name,rows in [('costs.csv',schedules['test06']),('restricted.csv',schedules['window01'])]:
        with (d/name).open('w',newline='') as fp:w=csv.DictWriter(fp,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,warm_max=worst,restricted907=schedules['window01'][-1],area={k:v for k,v in area.items() if k!='instance_changes'})))

if __name__=='__main__':main()
