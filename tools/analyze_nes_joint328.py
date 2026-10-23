# SPDX-License-Identifier: MIT
"""Bind independent expected scan, actual ARM schedule and whole Lite evidence."""
import argparse,csv,json,re
from collections import defaultdict
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--schedules-only',action='store_true');args=ap.parse_args()
    pins={};d=BASE/'probes/nes-joint328';prior=BASE/'probes/nes-expand325'
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    ref=js(ROOT/'analysis/expand325-verification.json');assert ref['passed']
    previous327=js(ROOT/'analysis/joint327-verification.json');assert previous327['passed']
    board=js(d/'board01/result.json');assert board['passed']
    for n,h in board['actual_inputs'].items():assert sha(d/'board01'/n)==h
    whole={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',board['summary'])[1].replace(',','')) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
    log=read(d/'board01/map.log');assert 'Warning (10034)' not in log
    assert all('cache_index141' in x for x in re.findall(r'Warning \(10240\):[^\r\n]+',log))
    runs={}
    def grouped(transfers):
        g=defaultdict(list)
        for x in transfers:
            b=bytes.fromhex(x['tx'])
            if not b:continue
            if b[0]==0xe1:g[b[1]].append((b[:3]+b[5:-2]).hex()) # Only sequence and CRC change with ordering.
            if b[0]==0xe9:g[0xe9].append(b.hex())
        return dict(g)
    for tag,oldtag in [(mode+'-'+tag,oldtag) for mode in ('arm','joint') for tag,oldtag in [('fixed01','fixed03'),('window01','window02'),('normal01','normal02')]]:
        q=d/tag;r=js(q/'result.json');assert r['passed']
        if tag.startswith('arm-'):
            assert r['rtl_hashes']==js(prior/oldtag/'result.json')['rtl_hashes'], 'ARM-only RTL must exactly match325'
        for n,h in r['rtl_hashes'].items():assert sha(q/n)==h;pins[str(q/n)]=h
        for n in ('nes_mux260.sv','nes_validator278.sv','nes_joint257.sv','nes_bulk_aperture188.sv'):
            a=read((d/'board01' if tag.startswith('joint-') else prior/oldtag)/n);b=read(q/n)
            if n=='nes_mux260.sv':a=a.replace(' output wire tile_closed267,\n','').replace('assign tile_closed267=tiles_closed;','')
            assert a==b,n
        assert sha(q/'joint266_tb.sv')==r['tb_sha256'];read(q/'joint266_tb.sv')
        assert sha(q/'output.elf')==r['ELF_sha256'];pins[str(q/'output.elf')]=r['ELF_sha256']
        for n in ('nes_native289.c','nes_output264.c','nes_refill267.c','nes_planner211.c'):
            read(q/n)
        for n in ('ordinary.sfc','bus.csv','timing.csv','capture.lua','packets.hex'):
            assert sha(q/('CPU-'+n))==sha(prior/'cpu01'/n);pins[str(q/('CPU-'+n))]=sha(q/('CPU-'+n))
        events=list(csv.reader(read(q/'joint-events.csv').splitlines()))
        source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(q/'cycles.csv').splitlines())}
        metadata=js(q/'metadata317.json');rows=[]
        for old in ref['runs'][oldtag]['rows']:
            f=old['frame'];e=[x for x in events if len(x)>1 and x[1]==str(f)]
            first=lambda n:next(x for x in e if x[0]==n)
            at=lambda n,k=None: int(next(x for x in e if x[0]==n and (k is None or int(x[2])==k))[-1])/1e9
            end=first('frame_done');start=first('start319');arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            finish=int(end[2])/1e9;total=source[f]+int(end[3])/1e9
            assert sum(int(x[3]) for x in e if x[0]=='arm267')==arm['SPI_bytes']
            if tag.endswith('fixed01'):assert int(start[2])/1e9==old['start_ms'] and int(start[3])==old['start_ROM_cycle']
            newwire=grouped(js(q/f'arm{f}.json')['transfers']);oldwire=grouped(js(prior/oldtag/f'arm{f}.json')['transfers'])
            assert newwire==oldwire,(tag,f,'payload/opcode differs')
            if tag.startswith('joint-'):
                assert first('scan_done327')[2]=='446'
                scans=[x for x in e if x[0]=='scan_done327'];assert len(scans)==1
            credit=max(int(x[2]) for x in e if x[0]=='credits');assert credit<=2
            prep=[x for x in metadata if x['name']=='issue_map327' and x['start']['generation']==f-904]
            rows.append(dict(frame=f,start_ms=int(start[2])/1e9,start_ROM_cycle=int(start[3]),finish_ms=finish,total_ms=total,gap_ms=total-1000/60,
                first_BG_ms=at('romtile305',0),first_ROM_accept_ms=at('rom_accept327',0),first_ROM_response_ms=at('rom_response327',0),
                requirements_release_ms=at('release312',15),map_manifest_release_ms=at('release312',11) if any(x[:3]==['release312',str(f),'11'] for x in e) else None,
                last_consume_ms=int([x for x in e if x[0]=='consume293'][-1][-1])/1e9,
                scan_ms=at('scan_done327')-at('scan_start327') if tag.startswith('joint-') else None,expected_bytes=446,
                finish_delta_ms=finish-old['finish_ms'],duration_delta_ms=total-old['total_ms'],start_delta_ms=int(start[2])/1e9-old['start_ms'],
                ARM_instructions=arm['instructions'],ARM_delta=arm['instructions']-old['ARM_instructions'],SPI_bytes=arm['SPI_bytes'],SPI_delta=arm['SPI_bytes']-old['SPI_bytes'],max_credit=credit,
                map_preparation_calls=len(prep),map_preparation_inclusive_instructions=sum(x['end']['instruction']-x['start']['instruction'] for x in prep),
                opcode_payloads_and_E9_identical=True))
        with (q/'output.elf').open('rb') as f:
            elf=ELFFile(f);sections={n:elf.get_section_by_name(n)['sh_size'] if elf.get_section_by_name(n) else 0 for n in ('.text','.bss','.data')}
        runs[tag]=dict(rows=rows,SysTick=len(r['ARM']['IRQ_cases']),EXTI=len(r['ARM']['EXTI284']),stack=r['ARM']['stack_observed'],sections=sections)
    # Prove the ARM image is identical in both branches; build-directory DWARF is irrelevant.
    def load_segments(p):
        with p.open('rb') as f:
            elf=ELFFile(f)
            return [(v['p_vaddr'],v['p_memsz'],v.data()) for v in elf.iter_segments() if v['p_type']=='PT_LOAD']
    split={}
    for kind in ('fixed01','window01','normal01'):
        assert load_segments(d/('arm-'+kind)/'output.elf')==load_segments(d/('joint-'+kind)/'output.elf')
        a=runs['arm-'+kind]['rows'];b=runs['joint-'+kind]['rows']
        split[kind]=[dict(frame=x['frame'],ARM_only_delta_ms=x['duration_delta_ms'],joint_extra_delta_ms=y['total_ms']-x['total_ms'],joint_extra_finish_delta_ms=y['finish_ms']-x['finish_ms']) for x,y in zip(a,b)]
    for run in runs.values():
        for row in run['rows']:
            row['tail_ms']=row['finish_ms']-row['last_consume_ms']
            row['fixed_schedule_free_tail_gap_ms']=row['gap_ms']-row['tail_ms']
    versus327={}
    for kind,oldkind in [('fixed01','fixed03'),('window01','window01'),('normal01','normal01')]:
        versus327[kind]=[dict(frame=x['frame'],finish_delta_ms=x['finish_ms']-y['finish_ms'],duration_delta_ms=x['total_ms']-y['total_ms']) for x,y in zip(runs['joint-'+kind]['rows'],previous327['runs'][oldkind]['rows'])]
    if args.schedules_only:
        print(json.dumps(dict(status='schedule_only_not_full_verification',runs=runs,split=split),indent=2));return
    guards=js(d/'guards01/result.json');assert guards['passed']
    assert guards['rtl_hashes']==js(d/'joint-window01/result.json')['rtl_hashes']
    assert guards['ELF_sha256']==sha(d/'joint-window01/output.elf')
    assert guards['tb_sha256']==sha(d/'guards01/joint266_tb.sv');read(d/'guards01/joint266_tb.sv')
    for case in guards['cases']:
        p=d/'guards01'/f"case{case['case']}"/'vsim.log';assert sha(p)==case['log_sha256'];raw=read(p)
        fault=7 if case['case']==10 else 3 if case['case']==6 else 4
        assert f"PASS OWNER319 GUARD={case['case']} fault={fault}" in raw
    if len(guards['cases'])==11:
        extra=js(d/'guards02/result.json');assert extra['passed']
        assert extra['rtl_hashes']==guards['rtl_hashes'] and extra['ELF_sha256']==guards['ELF_sha256']
        assert extra['tb_sha256']==sha(d/'guards02/joint266_tb.sv');read(d/'guards02/joint266_tb.sv')
        for case in extra['cases']:
            p=d/'guards02'/f"case{case['case']}"/'vsim.log';assert sha(p)==case['log_sha256']
            assert f"PASS OWNER319 GUARD={case['case']} fault=4" in read(p)
        guards['cases']+=extra['cases']
    assert sorted(x['case'] for x in guards['cases'])==list(range(1,14))
    armguards=js(d/'armguards01/result.json');assert armguards['passed']
    assert armguards['rtl_hashes']==js(d/'arm-window01/result.json')['rtl_hashes']
    assert armguards['ELF_sha256']==sha(d/'arm-window01/output.elf')
    assert armguards['tb_sha256']==sha(d/'armguards01/joint266_tb.sv');read(d/'armguards01/joint266_tb.sv')
    assert sorted(x['case'] for x in armguards['cases'])==[3,5,6,10,11]
    for case in armguards['cases']:
        p=d/'armguards01'/f"case{case['case']}"/'vsim.log';assert sha(p)==case['log_sha256']
        fault=7 if case['case']==10 else 3 if case['case']==6 else 4
        assert f"PASS OWNER319 GUARD={case['case']} fault={fault}" in read(p)
    aperture=js(d/'guards01/aperture/result.json');assert aperture['passed']
    assert aperture['RTL_sha256']==sha(d/'board01/nes_bulk_aperture188.sv')
    for n,key in [('aperture325_tb.sv','tb_sha256'),('vsim.log','log_sha256')]:
        assert aperture[key]==sha(d/'guards01/aperture'/n);read(d/'guards01/aperture'/n)
    def nodes(p):
        out={}
        for line in read(p).split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
            c=[v.strip() for v in line.split(';')]
            if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):out[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
        return out
    new=nodes(d/'board01/output_files/board.map.rpt');old=nodes(prior/'board02/output_files/board.map.rpt');assert sum(new.values())==whole['comb']
    rpt=read(d/'board01/output_files/board.map.rpt')
    for module in ('nes_output260:flow','nes_validator278:validator'):
        assert re.search(r'State Machine - [^\n]*'+re.escape(module)+r'\|state',rpt)
    delta={k:new.get(k,0)-old.get(k,0) for k in set(new)|set(old)};delta={k:v for k,v in sorted(delta.items()) if v}
    for n in ('nes_joint328.py','probe_nes_joint328.py','map_nes_joint328.py','guard_nes_joint328.py','guard_nes_arm328.py','analyze_nes_joint328.py','nes_joint327.py','probe_nes_joint327.py'):read(ROOT/'tools'/n)
    out=dict(stage=328,passed=True,baseline=325,runs=runs,split=split,whole=whole,whole_delta={k:whole[k]-ref['whole'][k] for k in whole},comb_deficit=whole['comb']-15408,entity_comb_delta=delta,guards=guards['cases'],aperture=aperture,
        ARM_only_guards=armguards['cases'],ARM_only_whole=ref['whole'],joint_delta_vs327=versus327,
        scope='Actual M4 instructions/SPI/IRQ/two-slot/ROM and unchanged325 CPU replay; no physical timing/FIT/STA',pins=pins)
    (ROOT/'analysis/joint328-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(passed=True,whole=whole,delta=out['whole_delta'],warm={k:v['rows'][-1] for k,v in runs.items()}),indent=2))

if __name__=='__main__':main()
