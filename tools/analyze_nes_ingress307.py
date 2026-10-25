# SPDX-License-Identifier: MIT
"""Bind actual ARM schedules, immutable bytes, independent guards and whole Lite."""
import csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_ingress306 import decode
from probe_nes_arm264 import ELFFile

def canonical(t):
    out=[]
    for x in t['transfers']:
        b=bytes.fromhex(x['tx'])
        if not b or b[0]!=0xe1:continue
        p=bytearray(b[1:-2])
        if p[0]==15 and p[1]==1:
            assert p[40]==1
            p=p[:40]+decode(p[41:],166);p[1]=0;p[12:14]=(190).to_bytes(2,'little')
        out.append(bytes(p))
    return out

def main():
    d=BASE/'probes/nes-ingress307';pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    def loaded(p):
        with pin(p).open('rb') as fp:return [(s['p_vaddr'],s['p_memsz'],s.data()) for s in ELFFile(fp).iter_segments() if s['p_type']=='PT_LOAD']
    prev=js(ROOT/'analysis/record305-verification.json')
    for p,h in prev['input_hashes'].items():assert sha(Path(p))==h
    schedules={};diagnostics=[];live={}
    for tag,mode,reference in [('isolated01','isolated_restricted','window02'),('window03','restricted','window02'),('test01','normal','test03')]:
        q=d/tag;r=js(q/'result.json');assert r['passed'];live[tag]=r
        for name,h in r['rtl_hashes'].items():assert sha(pin(q/name))==h
        assert sha(pin(q/'joint266_tb.sv'))==r['tb_sha256']
        assert sha(pin(q/'output.elf'))==r['ELF_sha256']
        for p in q.iterdir():
            if p.suffix in ('.c','.h','.inc','.s','.ld','.dll'):pin(p)
        events=list(csv.reader(pin(q/'joint-events.csv').open()))
        sources={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(pin(q/'cycles.csv').open())}
        rows=[]
        for f in (905,906,907):
            es=[e for e in events if e[1]==str(f)];t=js(q/f'arm{f}.json');old=js(BASE/'probes/nes-record305'/reference/f'arm{f}.json')
            assert canonical(t)==canonical(old),('semantic original packets',tag,f)
            assert [x['tx'] for x in t['transfers'] if x['tx'].startswith('e9')]==[x['tx'] for x in old['transfers'] if x['tx'].startswith('e9')]
            end=next(e for e in es if e[0]=='frame_done');finish=int(end[2])/1e9;output=int(end[3])/1e9;total=sources[f]+output
            base=next(x for x in prev['normal' if mode=='normal' else 'restricted'] if x['frame']==f)
            row=dict(frame=f,source_ms=sources[f],output_ms=output,total_ms=total,baseline305_ms=base['total_ms'],delta305_ms=total-base['total_ms'],margin_ms=1000/60-total,
                absolute_finish_ms=finish,frame_start_ms=finish-total,ARM_instructions=next(x['instructions'] for x in r['ARM']['frames'] if x['frame']==f),
                SPI_bytes=next(x['SPI_bytes'] for x in r['ARM']['frames'] if x['frame']==f),E2=sum(e[0]=='arm267' and e[2]=='226' for e in es),
                max_credit=max(int(e[2]) for e in es if e[0]=='credits'),timer_fallbacks=sum(e[0]=='wait284' and e[2]=='0' for e in es))
            assert row['max_credit']<=4
            bg=next((e for e in es if e[0]=='romtile305' and e[2]=='0'),None)
            plan=next((e for e in es if e[0]=='romplan305' and e[2]=='0'),None)
            if bg and plan:row.update(first_BG_ms=int(bg[-1])/1e9,BG_plan_ms=int(plan[-1])/1e9,tail_after_first_BG_ms=finish-int(bg[-1])/1e9,first_BG_plan_cycle=int(plan[3]),first_BG_tile_cycle=int(bg[4]))
            rows.append(row)
        schedules[mode]=rows
        if tag!='isolated01':
            issue=js(q/'issue307.json');assert all(0<=x['pending']<4 for x in issue)
            manifest=[x for x in issue if x['op']==15];assert len(manifest)==3 and any(x['pending']>0 for x in manifest)
            diagnostics.append(dict(mode=mode,manifest=manifest,checked_E1_issues=len(issue)))
    # identical functional candidate sources, independent normal/restricted execution
    assert live['test01']['rtl_hashes']==live['window03']['rtl_hashes']
    assert loaded(d/'test01/output.elf')==loaded(d/'window03/output.elf')
    tb=(d/'window03/joint266_tb.sv').read_text()
    old_tb=pin(BASE/'probes/nes-record305/window02/joint266_tb.sv').read_text()
    for key in ('wire qualify267=','wire core_req267='):
        assert next(x.strip() for x in tb.splitlines() if key in x)==next(x.strip() for x in old_tb.splitlines() if key in x)
    guard=js(d/'guards05/result.json');assert guard['passed'] and len(guard['guards'])==49
    for name,h in guard['entry307_hashes'].items():assert sha(pin(d/'guards05'/name))==h==sha(ROOT/'tools'/name)
    for name,h in guard['rtl_hashes'].items():
        assert sha(pin(d/'guards05'/name))==h
        if name in live['window03']['rtl_hashes']:assert h==live['window03']['rtl_hashes'][name],name
    for case in guard['guards']:
        log=pin(d/'guards05'/f'guard{case}.log').read_text()
        assert f'PASS HOST278 GNEG={case}' in log and 'Connection width does not match' not in log
    spi=js(d/'spi02/result.json');assert spi['passed'] and spi['checks']==13
    for name,h in spi['rtl_hashes'].items():assert sha(pin(d/'spi02'/name))==h==live['window03']['rtl_hashes'][name]
    armchecks={}
    elf=pin(d/'window03/output.elf')
    for tag in ('native01','armguard01','credit01','supply01','wait01','h2guard01','irqguard01','codec01'):
        r=js(d/tag/'result.json');assert r['passed'] and r['ELF_sha256']==sha(elf);armchecks[tag]=r
    assert len(armchecks['native01']['frames'])==71 and armchecks['native01']['fixture_reads']==0
    assert len(armchecks['codec01']['cases'])==76
    board=js(d/'board03/result.json');assert board['passed'] and not board['undriven']
    regenerated=js(d/'regenerate01/result.json');assert regenerated['passed'] and regenerated['script_sha256']==sha(ROOT/'tools/nes_ingress307.py')
    for name,h in board['actual_inputs'].items():assert sha(pin(d/'board03'/name))==h
    for name in ('nes_validator278.sv','nes_spi270.sv','nes_queue260.sv','nes_plan_spi200.sv','nes_plan_batch206.sv'):
        assert sha(d/'board03'/name)==sha(d/'window03'/name),name
    host=(d/'board03/nes_mux260.sv').read_bytes().replace(b' output wire tile_closed267,\n',b'').replace(b' reg tiles_closed;assign tile_closed267=tiles_closed;',b' reg tiles_closed;')
    assert host==(d/'window03/nes_mux260.sv').read_bytes()
    summary=pin(d/'board03/output_files/board.map.summary').read_text();report=pin(d/'board03/output_files/board.map.rpt').read_text()
    assert 'Lite Edition' in summary;whole={};own={}
    for key,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:whole[key]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',summary).group(1).replace(',',''))
    for line in report.splitlines():
        fields=[x.strip() for x in line.split(';')]
        if len(fields)==14 and re.fullmatch(r'\d+ \(\d+\)',fields[2]):own[fields[10]]=int(re.search(r'\((\d+)\)',fields[2]).group(1))
    assert sum(own.values())==whole['comb']
    def region(s,tree=False):return sum(v for k,v in own.items() if (s in k if tree else k.endswith(s)))
    regions=dict(host=region('nes_output260:flow'),validator=region('nes_validator278:validator'),queue=region('nes_queue260:queue',True),plan=region('nes_plan_batch206:transport',True)+region('nes_plan_spi200:endpoint',True),SPI=region('nes_spi270:spi_front270',True),glue=region('nes_joint267_board:native_joint267')+region('nes_joint257:core'))
    warm=schedules['restricted'][-1];old_events=list(csv.reader(pin(BASE/'probes/nes-record305/window02/joint-events.csv').open()))
    old_bg=next(e for e in old_events if e[:3]==['romtile305','907','0']);old_end=next(e for e in old_events if e[:2]==['frame_done','907'])
    assert warm['first_BG_tile_cycle']==int(old_bg[4])
    old_tail=(int(old_end[2])-int(old_bg[-1]))/1e9
    rom=dict(window_unchanged=True,first_BG_tile_cycle_unchanged=True,baseline_tail_ms=old_tail,new_tail_ms=warm['tail_after_first_BG_ms'],tail_gain_ms=old_tail-warm['tail_after_first_BG_ms'],warm_frame_regression_ms=warm['delta305_ms'])
    # Archived scripts can differ by a later guard-only existence check; bind
    # executable HDL itself, never pretend their original hashes are current.
    for name in ('nes_ingress307.py','probe_nes_live307.py','guard_nes_ingress307.py','guard_nes_spi307.py','guard_nes_codec307.py','map_nes_ingress307.py'):pin(ROOT/'tools'/name)
    size=pin(d/'window03/size287.log').read_text().splitlines()[-1].split()
    result=dict(passed=True,stage=307,selected=False,status='area_and_tail_improved_restricted_frame_regressed',**schedules,
        whole_MAP=whole,delta305_MAP={k:whole[k]-prev['whole_MAP'][k] for k in whole},regions=regions,
        boundary=sum(regions.values()),outside=whole['comb']-sum(regions.values()),comb_deficit=whole['comb']-15408,
        manifest_credit=diagnostics,ROM=rom,ARM_memory=dict(text=int(size[0]),bss=int(size[2]),observed_stack=live['window03']['ARM']['stack_observed']),
        RTL_guards=49,SPI_guards=13,ARM_checks=armchecks,current_patch_reproduces_MAP=regenerated,new_live_frames=9,new_MAP=True,full_RUN=False,full_schedule71=False,actual_SNES_live=False,FIT=False,STA=False,physical=False,
        limitations=['M4 CPI1/84MHz and IRQ24cycle allocation, not measured hardware cycles','Source replay and ordinary65816 trace plus map/tile/display bus model','Cold schedule changes ROM phase of following warm frame; absolute tail gain is not full-frame gain','Shared ingress and manifest execution are partial replacement; host/validator control remains','No fresh whole FIT/STA or physical60fps'],input_hashes=pins,script_sha256=sha(Path(__file__)))
    (ROOT/'analysis/ingress307-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    for mode,rows in schedules.items():
        with (ROOT/f'analysis/ingress307-{mode}.csv').open('w',newline='') as fp:
            w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    print(json.dumps(dict(whole_MAP=whole,regions=regions,ROM=rom,normal=schedules['normal'][-1],restricted=warm),indent=2))
if __name__=='__main__':main()
