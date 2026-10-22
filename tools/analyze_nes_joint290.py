# SPDX-License-Identifier: MIT
"""Paired incremental-output schedules and matched whole Lite receipt boundary."""
import argparse,csv,difflib,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    b=a.base.resolve();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    old=js(ROOT/'analysis/joint289-verification.json');area_old=js(ROOT/'analysis/joint287-verification.json')['area']
    tags=['native01','armguards01','h2guard01','test02','window02','range01','guards01','board03']
    r={t:js(b/t/'result.json') for t in tags};assert all(v['passed'] for v in r.values())
    from probe_nes_arm264 import plans
    from elftools.elf.elffile import ELFFile
    def loaded(p):
        with pin(p).open('rb') as fp:
            e=ELFFile(fp);return [(s['p_vaddr'],s['p_paddr'],s['p_memsz'],s['p_flags'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
    native=r['native01'];assert len(native['frames'])==71 and native['fixture_reads']==0 and len(native['guards'])==6
    assert len(r['armguards01']['checks'])==9 and len(r['h2guard01']['checks'])==9 and r['range01']['checks']==318
    assert r['guards01']['guards']==[3,23,24,*range(39,53),*range(56,64)]
    oracle,_=plans()
    for p in oracle.glob('req-*.bin'):pin(p)
    pin(BASE/'probes/nes-delta231/test07/palette.bin')
    for f in range(905,976):
        pin(BASE/f'probes/nes-joint284/test04/frame{f}.records');pin(BASE/f'probes/nes-joint284/test04/plans{f-904}.bin');pin(b/f'native01/frame{f}.packets')
    for tag,script in [('native01','probe_nes_native290.py'),('armguards01','guard_nes_stage290.py'),('h2guard01','guard_nes_h2290.py')]:
        assert r[tag]['script_sha256']==sha(pin(ROOT/'tools'/script));assert r[tag]['ELF_sha256']==sha(pin(b/'build01/output.elf'))
    schedules={}
    for tag,key,oldtag in [('test02','normal','test02'),('window02','restricted','window01')]:
        q=b/tag;v=r[tag];assert v['frames']==3 and not v['full_RUN'] and not v['physical']
        for n,h in v['rtl_hashes'].items():assert sha(pin(q/n))==h
        for n in ('nes_stage290.py','nes_joint290.py','probe_nes_live290.py'):assert v['input_hashes'][n]==sha(pin(ROOT/'tools'/n))==sha(pin(q/n))
        assert v['ELF_sha256']==sha(pin(q/'output.elf'));assert loaded(q/'output.elf')==loaded(b/'build01/output.elf')
        assert v['tb_sha256']==sha(pin(q/'joint266_tb.sv'))
        for p in q.iterdir():
            if p.suffix in ('.c','.h','.inc','.s','.ld'):pin(p)
        source={int(x['frame']):x for x in csv.DictReader(pin(q/'cycles.csv').open())}
        events=list(csv.reader(pin(q/'joint-events.csv').open()));previous={x['frame']:x for x in old[key]};rows=[];last=[0,0,0]
        for event in (e for e in events if e[0]=='frame_done'):
            f=int(event[1]);es=[e for e in events if int(e[1])==f];spi=[e for e in es if e[0]=='arm267'];wait=[e for e in es if e[0]=='wait284']
            counters=list(map(int,next(e for e in es if e[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counters,last)];last=counters
            now=js(q/f'arm{f}.json');then=js(BASE/'probes/nes-joint289'/oldtag/f'arm{f}.json')
            for op in (225,233):
                select=lambda z:[t['tx'] for t in z['transfers'] if t['tx'] and bytes.fromhex(t['tx'])[0]==op]
                assert select(now)==select(then),(tag,f,op)
            src=int(source[f]['total'])*45.454/1e6;out=int(event[3])/1e9;total=src+out
            armrow=next(x for x in v['ARM']['frames'] if x['frame']==f)
            rows.append(dict(frame=f,source_ms=src,output_ms=out,total_ms=total,before_ms=previous[f]['total_ms'],delta_ms=total-previous[f]['total_ms'],margin_ms=1000/60-total,
                early_DMA_descriptors=armrow['early_DMA_descriptors'],E2=sum(int(e[2])==226 for e in spi),E9=sum(int(e[2])==233 for e in spi),IRQ_waits=len(wait),timer_fallbacks=sum(int(e[2])==0 for e in wait),tile_wait_cycles=inc[0],slot_wait_cycles=inc[1],core_priority_blocks=inc[2]))
        assert len(rows)==3;schedules[tag]=rows
    assert r['test02']['rtl_hashes']==r['window02']['rtl_hashes']
    assert r['guards01']['TB_sha256']==sha(pin(b/'guards01/joint266_tb.sv'))
    for n,h in r['guards01']['rtl_hashes'].items():assert sha(pin(b/'guards01'/n))==h
    for case in r['guards01']['guards']:
        log=pin(b/'guards01'/f'guard{case}.log').read_text(errors='replace')
        assert f'PASS HOST278 GNEG={case}' in log and not re.search(r'\*\* (Fatal|Error):',log)
    for n in ('nes_mux260.sv','nes_validator278.sv'):
        assert sha(pin(b/'guards01'/n))==sha(pin(b/'test02'/n))
    assert r['range01']['rtl_sha256']==sha(pin(b/'test02/nes_validator278.sv'))
    assert r['range01']['test_sha256']==sha(pin(b/'range01/range283_tb.sv'))
    for n in ('guard_nes_range290.py','guard_nes_joint290.py'):pin(ROOT/'tools'/n)
    board=b/'board03'
    for n,h in r['board03']['actual_inputs'].items():assert sha(pin(board/n))==h
    for n in ('nes_mux260.sv','nes_validator278.sv'):
        actual=pin(board/n).read_bytes();sim=pin(b/'test02'/n).read_bytes()
        if n=='nes_mux260.sv':actual=actual.replace(b' output wire tile_closed267,\n',b'').replace(b' reg tiles_closed;assign tile_closed267=tiles_closed;',b' reg tiles_closed;')
        assert actual==sim,n
    # All other board inputs remain the pinned NES287 whole-board boundary.
    prior=BASE/'probes/nes-joint287/board01'
    for n in r['board03']['actual_inputs']:
        if n not in ('nes_mux260.sv','nes_validator278.sv'):assert sha(pin(board/n))==sha(pin(prior/n)),n
    s=pin(board/'output_files/board.map.summary').read_text();whole={}
    for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:whole[k]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',s).group(1).replace(',',''))
    own={}
    for line in pin(board/'output_files/board.map.rpt').read_text().splitlines():
        fields=[x.strip() for x in line.split(';')]
        if len(fields)==14 and re.fullmatch(r'\d+ \(\d+\)',fields[2]):own[fields[10]]=int(re.search(r'\((\d+)\)',fields[2]).group(1))
    assert sum(own.values())==whole['comb']
    region=lambda key:sum(v for k,v in own.items() if key in k)
    regions=dict(host=sum(v for k,v in own.items() if k.endswith('nes_output260:flow')),validator=region('nes_validator278:validator'),queue=region('nes_queue260:queue'),plan=region('nes_plan_batch206:transport')+region('nes_plan_spi200:endpoint'),SPI=region('nes_spi270:spi_front270'))
    glue=sum(v for k,v in own.items() if k.endswith(('nes_joint267_board:native_joint267','nes_joint257:core')));expanded=sum(regions.values())+glue
    area=dict(whole_MAP=whole,prior_MAP=area_old['whole_MAP'],delta={k:whole[k]-area_old['whole_MAP'][k] for k in whole},regions=regions,glue=glue,expanded_boundary=expanded,expanded_delta=expanded-area_old['expanded_boundary'],outside=whole['comb']-expanded,expanded_budget=15408-(whole['comb']-expanded),deficit=whole['comb']-15408)
    size=lambda p:list(map(int,re.search(r'\n\s*(\d+)\s+(\d+)\s+(\d+)',pin(p).read_text()).groups()))
    newsize=size(b/'test02/size287.log');oldsize=size(BASE/'probes/nes-joint289/test02/size287.log')
    result=dict(passed=True,stage=290,status='not_adopted',selected=tags,native_frames=native['frames'],native_guards=native['guards'],ARM_guards=r['armguards01']['checks'],H2_guards=r['h2guard01']['checks'],RTL_guards=r['guards01']['guards'],range_guards=r['range01']['checks'],fixture_reads=0,
        early_frames=sum(x['early_packets']>1 for x in native['frames']),early_descriptors=sum(x['early_packets']-1 for x in native['frames']),normal=schedules['test02'],restricted=schedules['window02'],area=area,
        normal_three_delta_ms=sum(x['delta_ms'] for x in schedules['test02']),restricted_three_delta_ms=sum(x['delta_ms'] for x in schedules['window02']),
        ARM_size=dict(before=oldsize,after=newsize,delta=[x-y for x,y in zip(newsize,oldsize)],observed_stack=r['test02']['ARM']['stack_observed'],prior_stack=old['ARM_size']['observed_stack']),
        new_MAP=True,full_schedule71=False,full_RUN=False,physical=False,FIT=False,STA=False,adopted=False,
        scope='Actual M4 staged H2/BEGIN and closed DMA descriptors, original compressed E1/E9 exact. Source timing replay and 65816 bus trace reuse remain. Offline71 intercepts dispatch. Only3+3 live schedule frames; no full RUN/WCET/physical proof. Host and validator FSMs retained; endpoint arithmetic is not whole control replacement.',
        input_hashes=pins,script_sha256=sha(Path(__file__)))
    for name,rows in [('native',native['frames']),('normal',result['normal']),('restricted',result['restricted'])]:
        with (d/f'{name}.csv').open('w',newline='') as fp:w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('passed','early_frames','early_descriptors','normal','restricted','ARM_size','area')}))


if __name__=='__main__':main()
