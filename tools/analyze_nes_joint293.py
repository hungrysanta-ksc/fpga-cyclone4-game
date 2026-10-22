# SPDX-License-Identifier: MIT
"""Bind BG publication, unchanged tile order, live schedules and whole Lite cost."""
import argparse,csv,json,re
from pathlib import Path
from probe_nes_arm264 import ELFFile
from nes_bg293 import unbatch
from nes_delta231 import BASE,ROOT,sha

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    b=a.base.resolve();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    def loaded(p):
        with pin(p).open('rb') as fp:
            return [(s['p_vaddr'],s['p_memsz'],s['p_flags'],s.data()) for s in ELFFile(fp).iter_segments() if s['p_type']=='PT_LOAD']
    old=js(ROOT/'analysis/joint289-verification.json');reference=js(BASE/'probes/nes-joint289/test02/result.json')
    r={n:js(b/n/'result.json') for n in ('native02','guards01','bg-guards01','irq-guards01','test02','window01')}
    assert all(x['passed'] for x in r.values())
    native=r['native02'];assert len(native['frames'])==71 and not native['fixture_reads'] and len(native['guards'])==6
    for tag,script in [('native02','probe_nes_native293.py'),('guards01','guard_nes_native289.py'),('bg-guards01','guard_nes_bg293.py')]:
        assert r[tag]['script_sha256']==sha(pin(ROOT/'tools'/script))
        assert r[tag]['ELF_sha256']==sha(pin(b/'test02/output.elf'))
    assert len(r['guards01']['checks'])==8 and len(r['bg-guards01']['checks'])==4
    assert len(r['irq-guards01']['cases'])==8 and len(r['irq-guards01']['EXTI'])==33
    assert r['irq-guards01']['ELF_sha256']==sha(pin(b/'test02/output.elf'))
    assert r['irq-guards01']['script_sha256']==sha(pin(ROOT/'tools/guard_nes_irq284.py'))
    pin(ROOT/'tools/guard_nes_irq293.py');pin(ROOT/'tools/probe_nes_live287.py')
    native_rows=[]
    def batches(data):
        at=0;n=0
        while at<len(data):size=int.from_bytes(data[at:at+2],'little');at+=3+size;n+=1
        assert at==len(data);return n
    for f in range(905,976):
        before=pin(BASE/f'probes/nes-joint284/test04/plans{f-904}.bin').read_bytes();after=pin(b/f'native02/plans{f-904}.bin').read_bytes()
        assert unbatch(before)==unbatch(after)
        assert pin(b/f'native02/frame{f}.packets').read_bytes()==pin(BASE/f'probes/nes-joint289/native01/frame{f}.packets').read_bytes()
        now=next(x for x in native['frames'] if x['frame']==f);prev=next(x for x in old['native_frames'] if x['frame']==f)
        native_rows.append(dict(frame=f,plans=len(unbatch(after)),before_batches=batches(before),after_batches=batches(after),extra_framing_bytes=len(after)-len(before),producer_instruction_delta=now['producer_instructions']-prev['producer_instructions']))
    schedules={}
    for tag,key in [('test02','normal'),('window01','restricted')]:
        q=b/tag;v=r[tag];assert v['frames']==3 and not v['physical'] and not v['full_RUN']
        assert v['rtl_hashes']==reference['rtl_hashes']
        for n,h in v['rtl_hashes'].items():assert sha(pin(q/n))==h
        assert loaded(q/'output.elf')==loaded(b/'test02/output.elf')
        for n in ('nes_bg293.py','probe_nes_live293.py'):assert v['input_hashes'][n]==sha(pin(ROOT/'tools'/n))==sha(pin(q/n))
        assert v['tb_sha256']==sha(pin(q/'joint266_tb.sv'))
        for p in q.iterdir():
            if p.suffix in ('.c','.h','.inc','.s','.ld'):pin(p)
        source={int(x['frame']):x for x in csv.DictReader(pin(q/'cycles.csv').open())}
        events=list(csv.reader(pin(q/'joint-events.csv').open()));rows=[];last=[0,0,0]
        for event in (e for e in events if e[0]=='frame_done'):
            f=int(event[1]);es=[e for e in events if int(e[1])==f];spi=[e for e in es if e[0]=='arm267'];wait=[e for e in es if e[0]=='wait284']
            counters=list(map(int,next(e for e in es if e[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counters,last)];last=counters
            now=js(q/f'arm{f}.json');then=js(BASE/'probes/nes-joint289'/tag/f'arm{f}.json')
            select=lambda z:[t['tx'] for t in z['transfers'] if t['tx'].startswith('e1')]
            assert select(now)==select(then)
            nr=next(x for x in v['ARM']['frames'] if x['frame']==f);pr=next(x for x in old[key] if x['frame']==f)
            checkpoints=[int(e[2]) for e in es if e[0]=='checkpoint287'];assert len(checkpoints)==31
            final_start=checkpoints[-2];final_end=checkpoints[-1]
            plans=[e for e in es if e[0]=='plan293'];tiles=[e for e in es if e[0]=='tile293'];cons=[e for e in es if e[0]=='consume293']
            e9=[e for e in spi if int(e[2])==233];assert e9 and nr['early_refills']>0
            credits=[int(e[2]) for e in es if e[0]=='credits'];assert credits and max(credits)<=4
            src=int(source[f]['total'])*45.454/1e6;out=int(event[3])/1e9;total=src+out
            rows.append(dict(frame=f,source_ms=src,output_ms=out,total_ms=total,before_ms=pr['total_ms'],delta_ms=total-pr['total_ms'],margin_ms=1000/60-total,
                E2=sum(int(e[2])==226 for e in spi),E9=len(e9),E9_delta=len(e9)-pr['E9'],SPI_bytes=nr['SPI_bytes'],early_refills=nr['early_refills'],
                ARM_instructions=nr['instructions'],final_step_instructions=nr['steps'][-1],
                plans_before_final_step=sum(int(e[-1])<=final_start for e in plans),tiles_started_before_final_step=sum(int(e[-1])<=final_start for e in tiles),
                consumed_before_final_step_end=sum(int(e[-1])<=final_end for e in cons),first_consume_after_final_step_us=(int(cons[0][-1])-final_end)/1e6 if cons else None,
                IRQ_waits=len(wait),timer_fallbacks=sum(int(e[2])==0 for e in wait),max_credit=max(credits),tile_wait_cycles=inc[0],slot_wait_cycles=inc[1],core_priority_blocks=inc[2]))
        assert len(rows)==3;schedules[key]=rows
    size=lambda p:list(map(int,re.search(r'\n\s*(\d+)\s+(\d+)\s+(\d+)',pin(p).read_text()).groups()))
    newsize=size(b/'test02/size287.log');oldsize=size(BASE/'probes/nes-joint289/test02/size287.log')
    # Ownership decisions concern actual simultaneous datapaths, not the count
    # of symbolic states or assumed standalone LUT costs.
    review=[
      dict(candidate='host + validator completion continuation',old_comb=3451,budget=1188,decision='unproven',retain='pre-DMA descriptor validation; concurrent CRC tap; RAM read/write latency; independent receipt coverage',new_comb=None),
      dict(candidate='fixed queue/plan/SPI/host/validator boundary',old_comb=4853,budget=2590,decision='unproven',retain='4 packet credits; 2 sealed plan banks; E9 admission; token and final ACK ownership',new_comb=None),
      dict(candidate='include source encoder and transport',old_comb=6624,budget=4361,decision='requires new clock/port arbitration proof',retain='NES source clock vs host clock; input/display lease; CRC and query ownership',new_comb=None)]
    anchors={'nes_mux260.sv':['ACKWAIT:if(qdone&&tap_idle278&&range_ready)','OTILE,OSELECT:if(range_ready)state<=ORET;','ORET:if(range_ready||sealed)'],
             'nes_validator278.sv':['V_RWRITE:if(!crc_covered287)','V_PCHECKTEST:if(checked_byte!=v_value||ram_q!=255)','if(cursor!=422||!v_all_consumed||!certificate_ok)']}
    for file,terms in anchors.items():
        text=pin(b/'test02'/file).read_text();assert all(x in text for x in terms)
    pin(BASE/'probes/nes-joint287/board01/output_files/board.map.summary')
    result=dict(passed=True,stage=293,selected=list(r),normal=schedules['normal'],restricted=schedules['restricted'],native=native_rows,
        native_commands=sum(x['packets'] for x in native['frames']),native_bytes=sum(x['bytes'] for x in native['frames']),
        native_guards=native['guards'],failure_guards=r['guards01']['checks'],BG_guards=r['bg-guards01']['checks'],IRQ_cases=r['irq-guards01']['cases'],
        ARM_size=dict(before=oldsize,after=newsize,delta=[x-y for x,y in zip(newsize,oldsize)],observed_stack=r['test02']['ARM']['stack_observed']),
        joint_review=review,unchanged_RTL=True,new_MAP=False,whole_MAP=old['whole_MAP'],comb_deficit=2263,measured_comb_saving=0,
        full_schedule71=False,full_RUN=False,physical=False,FIT=False,STA=False,
        scope='Actual M4 BG flush/refill and compiled IRQ with live SPI/ROM RTL; original tile and E1 order preserved. Source timing replay, reused ordinary 65816 trace, modeled map/tile/display bus and CPI1 remain. Native71 sink intercepted; live finish267 precedes commit285. No new FPGA replacement or whole MAP.',
        input_hashes=pins,script_sha256=sha(Path(__file__)))
    for name,rows in [('native',native_rows),*schedules.items(),('control',review)]:
        with (d/f'{name}.csv').open('w',newline='') as fp:w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('passed','normal','restricted','ARM_size','comb_deficit')}))

if __name__=='__main__':main()
