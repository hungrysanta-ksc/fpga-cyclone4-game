# SPDX-License-Identifier: MIT
"""Native producer costs, paired live schedules, and unchanged whole RTL ledger."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    b=a.base.resolve();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    old=js(ROOT/'analysis/joint287-verification.json');reference=js(BASE/'probes/nes-joint287/test06/result.json')
    r={t:js(b/t/'result.json') for t in ('native01','guards01','test02','window01')};assert all(v['passed'] for v in r.values())
    native=r['native01'];assert len(native['frames'])==71 and native['fixture_reads']==0 and len(native['guards'])==6
    from probe_nes_arm264 import plans
    from elftools.elf.elffile import ELFFile
    def loaded(p):
        with pin(p).open('rb') as fp:
            e=ELFFile(fp)
            return [(s['p_vaddr'],s['p_paddr'],s['p_memsz'],s['p_flags'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
    oracle,_=plans()
    for p in oracle.glob('req-*.bin'):pin(p)
    pin(BASE/'probes/nes-delta231/test07/palette.bin')
    for f in range(905,976):
        pin(BASE/f'probes/nes-joint284/test04/frame{f}.records')
        pin(BASE/f'probes/nes-joint284/test04/plans{f-904}.bin')
        pin(b/f'native01/frame{f}.packets')
    assert len(r['guards01']['checks'])==8
    for tag,script in [('native01','probe_nes_native289.py'),('guards01','guard_nes_native289.py')]:
        assert r[tag]['script_sha256']==sha(pin(ROOT/'tools'/script))
        assert r[tag]['ELF_sha256']==sha(pin(b/'build03/output.elf'))
    schedules={}
    for tag,key,oldtag in [('test02','normal','test06'),('window01','restricted_ROM','window01')]:
        q=b/tag;v=r[tag];assert v['frames']==3 and not v['full_RUN'] and not v['physical']
        assert v['rtl_hashes']==reference['rtl_hashes']
        for n,h in v['rtl_hashes'].items():assert sha(pin(q/n))==h
        for n in ('nes_native289.py','nes_native289.inc','probe_nes_live289.py'):assert v['input_hashes'][n]==sha(pin(ROOT/'tools'/n))==sha(pin(q/n))
        assert v['ELF_sha256']==sha(pin(q/'output.elf'))
        # ELF build metadata may carry different working directories. Compare
        # every loaded code/data byte and address/BSS extent, not only text size.
        assert loaded(q/'output.elf')==loaded(b/'build03/output.elf')
        assert v['tb_sha256']==sha(pin(q/'joint266_tb.sv'))
        for p in q.iterdir():
            if p.suffix in ('.c','.h','.inc','.s','.ld'):pin(p)
        source={int(x['frame']):x for x in csv.DictReader(pin(q/'cycles.csv').open())}
        events=list(csv.reader(pin(q/'joint-events.csv').open()));previous={x['frame']:x for x in old[key]};rows=[];last=[0,0,0]
        for event in (e for e in events if e[0]=='frame_done'):
            f=int(event[1]);es=[e for e in events if int(e[1])==f];spi=[e for e in es if e[0]=='arm267'];wait=[e for e in es if e[0]=='wait284']
            counters=list(map(int,next(e for e in es if e[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counters,last)];last=counters
            now=js(q/f'arm{f}.json');then=js(BASE/'probes/nes-joint287'/oldtag/f'arm{f}.json')
            for op in (225,233):
                select=lambda z:[t['tx'] for t in z['transfers'] if t['tx'] and bytes.fromhex(t['tx'])[0]==op]
                assert select(now)==select(then),(tag,f,op)
            src=int(source[f]['total'])*45.454/1e6;out=int(event[3])/1e9;total=src+out
            rows.append(dict(frame=f,source_ms=src,output_ms=out,total_ms=total,before_ms=previous[f]['diagnostic_serial_ms'],delta_ms=total-previous[f]['diagnostic_serial_ms'],margin_ms=1000/60-total,
                E2=sum(int(e[2])==226 for e in spi),E9=sum(int(e[2])==233 for e in spi),IRQ_waits=len(wait),timer_fallbacks=sum(int(e[2])==0 for e in wait),tile_wait_cycles=inc[0],slot_wait_cycles=inc[1],core_priority_blocks=inc[2]))
        assert len(rows)==3;schedules[tag]=rows
    size=lambda p:list(map(int,re.search(r'\n\s*(\d+)\s+(\d+)\s+(\d+)',pin(p).read_text()).groups()))
    newsize=size(b/'test02/size287.log');oldsize=size(BASE/'probes/nes-joint287/test06/size287.log')
    for n in ('nes_native_sink165.c','nes_native_sink165.h','nes_sink_bulk195.h'):pin(BASE/'probes/nes-wholepath247/jointdecode-host01'/n)
    area=old['area'];pin(BASE/'probes/nes-joint287/board01/output_files/board.map.summary')
    result=dict(passed=True,stage=289,status='native_producer_slice_not_joint_optimization',selected=list(r),native_frames=native['frames'],native_guards=native['guards'],failure_guards=r['guards01']['checks'],fixture_reads=0,
        normal=schedules['test02'],restricted=schedules['window01'],
        ARM_size=dict(before=oldsize,after=newsize,delta=[x-y for x,y in zip(newsize,oldsize)],observed_stack=r['test02']['ARM']['stack_observed'],prior_stack=reference['ARM']['stack_observed']),
        identical_ARM_load_segments=True,unchanged_RTL=True,new_MAP=False,area_reference='NES287 board01',whole_MAP=area['whole_MAP'],comb_deficit=area['deficit'],expanded_boundary_comb=area['expanded_boundary'],expanded_budget=area['expanded_budget'],
        FPGA_controls_replaced=False,early_DMA=False,full_schedule71=False,full_RUN=False,physical=False,FIT=False,STA=False,
        scope='Actual M4 native production and dispatch, E1/E9 exact, live IRQ/tile ROM. Source timing replay and 65816 bus trace reuse remain. Offline71 dispatch is intercepted and does not prove ACK. Live3 finish267 gates commit285 after checked display retirement.',
        input_hashes=pins,script_sha256=sha(Path(__file__)))
    for name,rows in [('native',native['frames']),('normal',result['normal']),('restricted',result['restricted'])]:
        with (d/f'{name}.csv').open('w',newline='') as fp:w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('passed','normal','restricted','ARM_size','comb_deficit')}))


if __name__=='__main__':main()
