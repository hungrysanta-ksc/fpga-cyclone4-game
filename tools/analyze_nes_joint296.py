# SPDX-License-Identifier: MIT
"""Bind BG publication, unchanged tile order, live schedules and whole Lite cost."""
import argparse,csv,json,re
from pathlib import Path
from probe_nes_arm264 import ELFFile
from nes_bg293 import unbatch
from nes_bg295 import unbatch as unbatch295
from nes_delta231 import BASE,ROOT,sha

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    b=a.base.resolve();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    def loaded(p):
        with pin(p).open('rb') as fp:
            return [(s['p_vaddr'],s['p_memsz'],s['p_flags'],s.data()) for s in ELFFile(fp).iter_segments() if s['p_type']=='PT_LOAD']
    old=js(ROOT/'analysis/joint289-verification.json');bg=js(ROOT/'analysis/joint293-verification.json');previous=js(ROOT/'analysis/joint295-verification.json');reference=js(BASE/'probes/nes-joint289/test02/result.json')
    r={n:js(b/n/'result.json') for n in ('native01','armguard01','h2guard01','irqguard01','test02','window02','guards01','board01')}
    assert all(x['passed'] for x in r.values())
    for name in ('guard_nes_joint296.py','map_nes_joint296.py','nes_joint296.py','nes_wait296.py','probe_nes_live296.py'):pin(ROOT/'tools'/name)
    native=r['native01'];assert len(native['frames'])==71 and not native['fixture_reads'] and len(native['guards'])==6
    for tag,script in [('native01','probe_nes_native296.py'),('h2guard01','guard_nes_h2290.py'),('armguard01','guard_nes_wait296.py')]:
        assert r[tag]['script_sha256']==sha(pin(ROOT/'tools'/script))
        assert r[tag]['ELF_sha256']==sha(pin(b/'window01'/'output.elf'))
    assert len(r['h2guard01']['checks'])==9 and len(r['armguard01']['checks'])==8
    assert len(r['irqguard01']['cases'])==8 and len(r['irqguard01']['EXTI'])==33
    assert r['irqguard01']['ELF_sha256']==sha(pin(b/'window01/output.elf'))
    assert r['irqguard01']['script_sha256']==sha(pin(ROOT/'tools/guard_nes_irq284.py'))
    pin(ROOT/'tools/guard_nes_irq293.py');pin(ROOT/'tools/probe_nes_live287.py')
    assert loaded(b/'window01/output.elf')==loaded(b/'test02/output.elf')
    native_rows=[]
    def batches(data):
        at=0;n=0
        while at<len(data):size=int.from_bytes(data[at:at+2],'little');at+=3+size;n+=1
        assert at==len(data);return n
    for f in range(905,976):
        before=pin(BASE/f'probes/nes-joint284/test04/plans{f-904}.bin').read_bytes();after=pin(b/f'native01/plans{f-904}.bin').read_bytes()
        assert unbatch(before)==unbatch295(after)
        assert pin(b/f'native01/frame{f}.packets').read_bytes()==pin(BASE/f'probes/nes-joint289/native01/frame{f}.packets').read_bytes()
        now=next(x for x in native['frames'] if x['frame']==f);prev=next(x for x in old['native_frames'] if x['frame']==f)
        wire=(b/f'native01/frame{f}.packets').read_bytes();at=0;packets=[]
        while at<len(wire):n=int.from_bytes(wire[at:at+2],'little');packets.append(wire[at+2:at+2+n]);at+=2+n
        assert at==len(wire) and packets[0][0]==1
        early=packets[1:now['early_packets']];assert all(p[0]==7 for p in early)
        blank=lambda p:p[1]==0 and int.from_bytes(p[10:12],'little')==0 and int.from_bytes(p[14:16],'little')==16
        native_rows.append(dict(frame=f,plans=len(unbatch295(after)),before_batches=batches(before),after_batches=batches(after),extra_framing_bytes=len(after)-len(before),before_foreground_done_descriptors=len(early),before_foreground_done_nonblank=sum(not blank(p) for p in early),before_foreground_done_bytes=sum(int.from_bytes(p[14:16],'little') for p in early),final_producer_instructions=now['final_producer_instructions']))
    schedules={}
    for tag,key in [('test02','normal'),('window02','restricted')]:
        q=b/tag;v=r[tag];assert v['frames']==3 and not v['physical'] and not v['full_RUN']
        assert v['rtl_hashes']==r['test02']['rtl_hashes']
        for n,h in v['rtl_hashes'].items():assert sha(pin(q/n))==h
        assert loaded(q/'output.elf')==loaded(b/'test02/output.elf')
        for n in ('nes_bg293.py','nes_bg294.py','nes_bg295.py','nes_stage290.py','nes_close295.py','probe_nes_live295.py','nes_wait296.py','nes_joint296.py','probe_nes_live296.py'):assert v['input_hashes'][n]==sha(pin(ROOT/'tools'/n))==sha(pin(q/n))
        assert v['tb_sha256']==sha(pin(q/'joint266_tb.sv'))
        for p in q.iterdir():
            if p.suffix in ('.c','.h','.inc','.s','.ld'):pin(p)
        source={int(x['frame']):x for x in csv.DictReader(pin(q/'cycles.csv').open())}
        events=list(csv.reader(pin(q/'joint-events.csv').open()));rows=[];last=[0,0,0]
        for event in (e for e in events if e[0]=='frame_done'):
            f=int(event[1]);es=[e for e in events if int(e[1])==f];spi=[e for e in es if e[0]=='arm267'];wait=[e for e in es if e[0]=='wait284']
            counters=list(map(int,next(e for e in es if e[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counters,last)];last=counters
            now=js(q/f'arm{f}.json');then=js(BASE/'probes/nes-joint289'/('test02' if tag=='test02' else 'window01')/f'arm{f}.json')
            select=lambda z:[t['tx'] for t in z['transfers'] if t['tx'].startswith('e1')]
            assert select(now)==select(then)
            nr=next(x for x in v['ARM']['frames'] if x['frame']==f);pr=next(x for x in old[key] if x['frame']==f)
            checkpoints=[int(e[2]) for e in es if e[0]=='checkpoint287'];assert len(checkpoints)==31
            final_start=checkpoints[-2];final_end=checkpoints[-1]
            plans=[e for e in es if e[0]=='plan293'];tiles=[e for e in es if e[0]=='tile293'];cons=[e for e in es if e[0]=='consume293']
            e9=[e for e in spi if int(e[2])==233];assert e9 and nr['early_refills']>0
            credits=[int(e[2]) for e in es if e[0]=='credits'];assert credits and max(credits)<=4
            src=int(source[f]['total'])*45.454/1e6;out=int(event[3])/1e9;total=src+out
            bgrow=next(x for x in bg[key] if x['frame']==f);prevrow=next(x for x in previous[key] if x['frame']==f)
            rows.append(dict(frame=f,source_ms=src,output_ms=out,total_ms=total,before_ms=pr['total_ms'],delta_ms=total-pr['total_ms'],previous295_ms=prevrow['total_ms'],delta_vs295_ms=total-prevrow['total_ms'],BG293_ms=bgrow['total_ms'],delta_vs293_ms=total-bgrow['total_ms'],margin_ms=1000/60-total,
                E2=sum(int(e[2])==226 for e in spi),E9=len(e9),E9_delta=len(e9)-pr['E9'],SPI_bytes=nr['SPI_bytes'],early_refills=nr['early_refills'],
                ARM_instructions=nr['instructions'],ARM_instruction_delta295=nr['instructions']-prevrow['ARM_instructions'],final_step_instructions=nr['steps'][-1],
                plans_before_final_step=sum(int(e[-1])<=final_start for e in plans),tiles_started_before_final_step=sum(int(e[-1])<=final_start for e in tiles),
                consumed_before_final_step_start=sum(int(e[-1])<=final_start for e in cons),first_consume_relative_to_final_start_us=(int(cons[0][-1])-final_start)/1e6 if cons else None,
                parser_windows_ms=sum(int(e[3]) for e in es if e[0]=='parser')/1e9,
                map_receipt_windows_ms=sum(int(e[3]) for e in es if e[0]=='receipt')/1e9,
                IRQ_waits=len(wait),timer_fallbacks=sum(int(e[2])==0 for e in wait),max_credit=max(credits),tile_wait_cycles=inc[0],slot_wait_cycles=inc[1],core_priority_blocks=inc[2]))
        assert len(rows)==3;schedules[key]=rows
    critical=[]
    for stage in (295,296):
        q=BASE/f'probes/nes-joint{stage}'/('window01' if stage==295 else 'window02')
        es=[e for e in csv.reader(pin(q/'joint-events.csv').open()) if e[1]=='907']
        critical.append(dict(stage=stage,E9_ms=[int(e[4])/1e9 for e in es if e[0]=='arm267' and e[2]=='233'],
            OBJ_plan_ms=[int(e[-1])/1e9 for e in es if e[0]=='plan293' and e[2]=='1'],
            OBJ_start_ms=[int(e[-1])/1e9 for e in es if e[0]=='tile293' and e[2]=='1'],
            tile_receipt_ms=[int(e[-1])/1e9 for e in es if e[0]=='consume293' and e[2]=='1']))
    size=lambda p:list(map(int,re.search(r'\n\s*(\d+)\s+(\d+)\s+(\d+)',pin(p).read_text()).groups()))
    newsize=size(b/'test02/size287.log');oldsize=size(BASE/'probes/nes-joint295/test03/size287.log')
    # Ownership decisions concern actual simultaneous datapaths, not the count
    # of symbolic states or assumed standalone LUT costs.
    review=[
      dict(candidate='host + validator completion continuation',old_comb=3440,budget=1145,decision='unproven',retain='pre-DMA descriptor validation; concurrent CRC tap; RAM read/write latency; independent receipt coverage',new_comb=None),
      dict(candidate='fixed queue/plan/SPI/host/validator boundary',old_comb=4847,budget=2552,decision='unproven',retain='4 packet credits; 2 sealed plan banks; E9 admission; token and final ACK ownership',new_comb=None),
      ]
    anchors={'nes_mux260.sv':['ACKWAIT:if(qdone&&tap_idle278&&range_ready)','OTILE,OSELECT:if(range_ready)state<=ORET;','ORET:if(range_ready||sealed)'],
             'nes_validator278.sv':['V_RWRITE:if(!crc_covered287)','V_PCHECKTEST:if(checked_byte!=v_value||ram_q!=255)','if(cursor!=422||!v_all_consumed||!certificate_ok)'],
             'nes_tile_producer260.sv':['else if(opened&&!append_ok)state<=SEAL;','end_sealed<=1;sealed_generation<=wgen;in_frame<=0;'],
             'nes_plan_spi200.sv':['if(end_sealed)begin','ended<=1;ended_generation<=end_generation;','!can_write||!live||ended||retiring'],
             'nes_native289.c':['if(!final)return 1;','if(used&&!bulk289(kind,first,used))return 0;']}
    for file,terms in anchors.items():
        text=pin(b/'test02'/file).read_text();assert all(x in text for x in terms)
    board=b/'board01';prior=BASE/'probes/nes-joint295/board01'
    for name,h in r['board01']['actual_inputs'].items():assert sha(pin(board/name))==h
    for name in ('nes_plan_batch206.sv','nes_tile_producer260.sv','nes_validator278.sv'):
        assert sha(pin(board/name))==sha(pin(b/'test02'/name)),name
    actual=pin(board/'nes_mux260.sv').read_bytes().replace(b' output wire tile_closed267,\n',b'').replace(b' reg tiles_closed;assign tile_closed267=tiles_closed;',b' reg tiles_closed;')
    assert actual==pin(b/'test02/nes_mux260.sv').read_bytes()
    changed={'nes_mux260.sv','nes_validator278.sv'}
    for name in r['board01']['actual_inputs']:
        if name not in changed:assert sha(pin(board/name))==sha(pin(prior/name)),name
    raw=pin(board/'output_files/board.map.summary').read_text();whole={}
    for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:whole[k]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',raw).group(1).replace(',',''))
    own={}
    for line in pin(board/'output_files/board.map.rpt').read_text().splitlines():
        fields=[x.strip() for x in line.split(';')]
        if len(fields)==14 and re.fullmatch(r'\d+ \(\d+\)',fields[2]):own[fields[10]]=int(re.search(r'\((\d+)\)',fields[2]).group(1))
    assert sum(own.values())==whole['comb']
    def region(suffix,subtree=False):
        return sum(v for k,v in own.items() if (suffix in k if subtree else k.endswith(suffix)))
    regions=dict(host=region('nes_output260:flow'),validator=region('nes_validator278:validator'),
        queue=region('nes_queue260:queue',True),plan=region('nes_plan_batch206:transport',True)+region('nes_plan_spi200:endpoint',True),
        SPI=region('nes_spi270:spi_front270',True),glue=region('nes_joint267_board:native_joint267')+region('nes_joint257:core'))
    fixed=sum(regions.values());outside=whole['comb']-fixed
    area=dict(whole_MAP=whole,prior_MAP=previous['whole_MAP'],delta={k:whole[k]-previous['whole_MAP'][k] for k in whole},deficit=whole['comb']-15408,own=own,
        regions=regions,fixed_boundary=fixed,outside=outside,budget=15408-outside)
    for row in review[:2]:
        row['measured_boundary_comb']=regions['host']+regions['validator'] if row['old_comb']==3440 else fixed
        row['current_budget']=row['measured_boundary_comb']-area['deficit']
        row['decision']='shared host packet position and validator phase cursor measured; broad shared executor unimplemented'

    for tag in ('guards01',):
        for name,h in r[tag]['rtl_hashes'].items():assert sha(pin(b/tag/name))==h
    for name in ('nes_mux260.sv','nes_tile_producer260.sv','nes_validator278.sv'):assert sha(pin(b/'guards01'/name))==sha(pin(b/'test02'/name))
    close=js(BASE/'probes/nes-joint295/close02/result.json');assert close['passed']
    assert close['rtl_hashes']['nes_plan_batch206.sv']==sha(pin(b/'test02/nes_plan_batch206.sv'))
    for case in r['guards01']['guards']:
        assert f'PASS HOST278 GNEG={case}' in pin(b/'guards01'/f'guard{case}.log').read_text()
    assert 'tile_ended' not in (b/'test02/nes_mux260.sv').read_text()
    services=[dict(frame=x['frame'],mode=tag,**e) for tag in ('test02','window02') for x in r[tag]['ARM']['frames'] for e in x['service296'] if e['after_done']!=e['before_done']]
    assert any((e['sent']-e['retired'])&65535 for e in services)
    result=dict(wait_service296=services,wait_service_scope='Function-entry/return instruction trace; sent/retired are conservative ARM cached counters. Actual OBJ plan and receipt overlap is in restricted907_trace.',passed=True,stage=296,selected=list(r),normal=schedules['normal'],restricted=schedules['restricted'],native=native_rows,
        native_count_scope='Intercepted dispatch before foreground observes planner completion; service may already have completed OBJ. Not an early-BG or actual DMA-completion count.',native_commands=sum(x['packets'] for x in native['frames']),native_bytes=sum(x['bytes'] for x in native['frames']),
        native_guards=native['guards'],RTL_guards=r['guards01']['guards'],reused_close295_guards=close['cases'],H2_guards=r['h2guard01']['checks'],BG_guards=r['armguard01']['checks'],IRQ_cases=r['irqguard01']['cases'],
        ARM_size=dict(before=oldsize,after=newsize,delta=[x-y for x,y in zip(newsize,oldsize)],observed_stack=r['test02']['ARM']['stack_observed']),
        joint_review=review,restricted907_trace=critical,unchanged_RTL=False,new_MAP=True,area=area,whole_MAP=area['whole_MAP'],comb_deficit=area['deficit'],measured_comb_saving=-area['delta']['comb'],
        full_schedule71=False,full_RUN=False,physical=False,FIT=False,STA=False,
        scope='Actual M4 BG flush/refill/incremental native DMA dispatch and compiled IRQ with live SPI/ROM RTL; original tile and E1 order preserved. Source timing replay, reused ordinary 65816 trace, modeled map/tile/display bus and CPI1 remain. Native71 sink intercepted; live finish267 precedes commit285. Retained BG marker; actual OBJ planner service before DMA wait, host packet-position and validator phase-cursor sharing; new whole Lite MAP.',
        input_hashes=pins,script_sha256=sha(Path(__file__)))
    for name,rows in [('native',native_rows),*schedules.items(),('control',review)]:
        with (d/f'{name}.csv').open('w',newline='') as fp:w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('passed','normal','restricted','ARM_size','comb_deficit')}))

if __name__=='__main__':main()
