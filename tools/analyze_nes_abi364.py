# SPDX-License-Identifier: MIT
"""ABI deletion caps and coupled added-cost diagnostics, never a new-RTL claim."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_receipt335 import load_image,completed_unit
from analyze_nes_execute334 import wire
from probe_nes_arm264 import crc

def physical_bytes(encoded):
    # Keep the existing 13-byte progress reply after the command byte. A 13B
    # empty SEAL therefore needs one zero dummy clock byte outside record CRC.
    b=bytes.fromhex(encoded);at=0;total=0
    while at<len(b):
        n=int.from_bytes(b[at+5:at+7],'little')+13;assert at+n<=len(b)
        total+=max(14,n);at+=n
    return total

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--partial',action='store_true');a=ap.parse_args();d=a.root.resolve();pins={}
    def pin(p):p=p.resolve();pins[str(p)]=sha(p);return p
    def read(p):return pin(p).read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    old=js(ROOT/'analysis/execute362-verification.json');assert old['analysis_passed']
    refroot=BASE/'probes/nes-execute362';arm=js(d/'arm01/result.json');guards=js(d/'guards01/result.json');assert arm['passed'] and guards['passed']
    packets=js(d/'arm01/packets.json')
    for r in arm['rows']:
        selected=[p for p in packets if (p['schedule'],p['mode'],p['frame'])==(r['schedule'],r['mode'],r['frame'])]
        r['minimum_14B_exchange_bytes']=sum(physical_bytes(p['new']) for p in selected)
        r['minimum_14B_exchange_delta']=r['minimum_14B_exchange_bytes']-r['old_bytes']
        assert sum(max(0,physical_bytes(p['new'])-len(p['old'])//2) for p in selected)==r['positive_bytes']
    for path,h in arm['pins'].items():assert sha(pin(Path(path)))==h
    assert sha(pin(d/'arm01/abi364.elf'))==guards['ELF_sha256']
    for n in ('nes_abi364.c','build.log','size.log','disassembly.log','abi364.elf-nes_abi364.su'):pin(d/'arm01'/n)
    assert read(d/'arm01/nes_abi364.c')==read(ROOT/'tools/nes_abi364.c')
    runs={}
    for mode in (0,1):
        for schedule,refname in [('window','keepwindow01'),('fixed','keepfixed01')]:
            name=f'{schedule}-m{mode}-01';q=d/name;ref=refroot/refname
            if not (q/'result.json').exists():assert a.partial,(name,'missing');continue
            result=js(q/'result.json');rr=js(ref/'result.json');assert result['passed'] and result['CPI']==1 and result['ROM_window']==1
            assert set(result['rtl_hashes'])==set(rr['rtl_hashes'])
            for n,h in result['rtl_hashes'].items():assert sha(pin(q/n))==h==sha(pin(ref/n))==rr['rtl_hashes'][n],(name,n)
            assert load_image(pin(q/'output.elf'))==load_image(pin(ref/'output.elf'))
            assert sha(pin(q/'abi364.elf'))==guards['ELF_sha256']
            assert 'PASS REFILL267 frames=3' in read(q/'vsim.log')
            tb=read(q/'joint266_tb.sv');assert 'romcycle267%357368>=330088&&romcycle267%357368<354640&&romcycle267%12==3' in tb
            costs=js(q/'abi-cost364.json');assert costs['mode']==mode
            hint=js(q/'hint-arm361.json');assert hint['passed']
            assert read(q/'hint361.hex')==read(ref/'hint361.hex')
            events=list(csv.reader(read(q/'joint-events.csv').splitlines()));bevents=list(csv.reader(read(ref/'joint-events.csv').splitlines()));rows=[]
            for f in (905,906,907):
                e=[x for x in events if x[1]==str(f)];be=[x for x in bevents if x[1]==str(f)];get=lambda ev,n:next(x for x in ev if x[0]==n)
                start=get(e,'start319');end=get(e,'frame_done');bs=get(be,'start319');bend=get(be,'frame_done')
                if schedule=='fixed':assert start[2:]==bs[2:]
                transfers=js(q/f'arm{f}.json')['transfers'];bt=js(ref/f'arm{f}.json')['transfers']
                for t in transfers:
                    tx=bytes.fromhex(t['tx'])
                    if tx and tx[0]==0xe9:
                        assert crc(tx[4:-4])==int.from_bytes(tx[-4:-2],'big') and crc(tx[:-2],8)==tx[-2] and tx[-1]==165
                assert read(q/f'frame{f}.records')==read(ref/f'frame{f}.records')
                expected=[];actual=[];offset=0;token=None;writes=[];published=0
                for x in e:
                    if x[0]=='read336':
                        tok,op,section,pos,off,data,t=map(int,x[2:]);assert off==offset
                        if not offset:token=tok
                        assert tok==token;offset+=1;unit=completed_unit(op,section,pos,2)
                        if unit:expected.append((tok,int(unit[0]),unit[1]))
                    elif x[0]=='unit336':actual.append(tuple(map(int,x[2:5])))
                    elif x[0]=='private336':
                        tok,addr,value,t=map(int,x[2:]);assert tok==token;writes.append(t)
                    elif x[0]=='publish336':
                        tok,n,t=map(int,x[2:]);assert tok==token and n==offset and n>0 and all(z<t for z in writes)
                        offset=0;token=None;writes=[];published+=1
                assert expected==actual and offset==0 and int(get(e,'display266')[2])==12*(f-904)
                credit=max(int(x[2]) for x in e if x[0]=='credits');assert credit<=2
                c=[x for x in costs['rows'] if x['serial']==f-904];assert len(c)==sum(bool(t['tx']) and t['tx'][:2] in ('e1','e9') for t in transfers)
                assert all(max(0,physical_bytes(x['new_hex'])-x['old_bytes'])==x['positive_wire_bytes'] for x in c)
                assert sum(x['helper_instructions'] for x in c)==sum(t.get('ABI364',{}).get('helper_instructions',0) for t in transfers)
                total=(int(end[2])-int(start[2]))/1e9;base=(int(bend[2])-int(bs[2]))/1e9
                rows.append(dict(frame=f,total_ms=total,baseline_ms=base,delta_ms=total-base,margin_60Hz_ms=1000/60-total,
                    start_ROM_cycle=int(start[3]),baseline_ROM_cycle=int(bs[3]),max_credit=credit,qualified_units=len(actual),published=published,
                    output_wire_equal=wire(transfers)==wire(bt),actual_old_output_SPI_bytes=sum(len(t['tx'])//2 for t in transfers),
                    actual_E2_polls=sum(t['tx'].startswith('e2') for t in transfers),source_SPI_bytes=sum(int(x[5]) for x in e if x[0]=='input_wire337'),
                    source_empty_polls=sum(x[0]=='input_wire337' and x[2]=='28' and x[4]=='0' for x in e),
                    helper_instructions=sum(x['helper_instructions'] for x in c),extra_wire_CS_cycles=sum(x['extra_wire_CS_cycles'] for x in c),
                    new_records=sum(x['new_packets'] for x in c),old_records=len(c),proposed_bytes=sum(x['new_bytes'] for x in c),old_command_bytes=sum(x['old_bytes'] for x in c)))
                rows[-1]['proposed_minimum_14B_exchange_bytes']=sum(physical_bytes(x['new_hex']) for x in c)
                if f==907:
                    row=rows[-1];row['hint_ms']={n:(int(get(e,n)[2])-int(start[2]))/1e9 for n in ('hint_start361','hint_end361','hint_fill361')}
                    row['initial_ROM_window_end_upper_ms']=(354640-int(start[3])%357368)/22000
                    row['fill_margin_to_initial_window_upper_ms']=row['initial_ROM_window_end_upper_ms']-row['hint_ms']['hint_fill361']
                    for kind,label in [('0','BG'),('1','OBJ')]:
                        for event,key in [('romplan305','plan'),('romtile305','tile')]:
                            x=next(x for x in e if x[0]==event and x[2]==kind);row[label+'_'+key+'_ms']=(int(x[-1])-int(start[2]))/1e9
            runs[name]=dict(rows=rows,IRQ_cases=len(result['ARM']['IRQ_cases']))
    # Unchanged whole MAP, all actual synthesis inputs remain pinned. No new run.
    mapped=refroot/'objmap01';mr=js(mapped/'result.json');assert mr['passed']
    for n,h in mr['actual_inputs'].items():assert sha(pin(mapped/n))==h
    summary=read(mapped/'output_files/board.map.summary');report=read(mapped/'output_files/board.map.rpt')
    whole={k:int(re.search(pattern+r'\s*:\s*([0-9,]+)',summary)[1].replace(',','')) for k,pattern in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Total registers'),('RAM_bits','Total memory bits')]}
    assert whole==old['maps']['objmap01'];ledger=old['ledgers']['objmap01']
    host=ledger['nes_output260:flow']['self'];queue=ledger['nes_queue260:queue']['inclusive'];spi=ledger['nes_spi270:spi_front270']['inclusive'];plan=sum(ledger[n]['inclusive'] for n in ('nes_plan_batch206:transport','nes_plan_spi200:endpoint'))
    source=ledger['nes_joint257:core']['inclusive']-ledger['nes_validator278:validator']['inclusive'];checker=sum(ledger[n]['inclusive'] for n in ('nes_validator278:validator','nes_bulk_aperture188:shared_ram.aperture'))
    rest=whole['comb']-host-queue-spi-plan-source-checker;replace=host+queue+spi+plan;fixed=source+checker+rest
    budget=dict(host=host,queue=queue,SPI=spi,plan=plan,replace_total=replace,source_retained=source,independent_checker_aperture_retained=checker,rest_retained=rest,fixed_total=fixed,
        device_limit=15408,target=15253,reserve=155,new_inclusive_cap=15253-fixed,device_only_cap=15408-fixed,required_net_deletion=whole['comb']-15253,
        old_interfaces_only=queue+spi+plan,new_cost_measured=None,actual_deleted_comb=0,whole_replacement_comb=None)
    assert replace==3314 and fixed==14410 and budget['new_inclusive_cap']==843 and budget['required_net_deletion']==2471
    assert 'expected_address313<472' in read(refroot/'keepwindow01/nes_queue260.sv')
    # Prior fault tests remain valid only for their unchanged modules.
    prior_guards=js(BASE/'probes/nes-prefetch359/guards01/result.json');assert prior_guards['passed']
    for n in ('nes_mux260.sv','nes_validator278.sv','nes_queue260.sv'):
        assert read(BASE/'probes/nes-prefetch359/guards01'/n)==read(refroot/'keepwindow01'/n)
    ea=js(refroot/'objguards02/result.json');assert ea['passed'] and 'PASS GUARD361 cases=68' in read(refroot/'objguards02/vsim.log')
    for n in ('nes_spi270.sv','nes_plan_spi200.sv','nes_source_tile192.sv','nes_chr_cache192.sv','nes_rom_physical.sv','nes_native_arbiter165.sv'):
        assert read(refroot/'objguards02'/n)==read(refroot/'keepwindow01'/n)
    for p in ROOT.glob('tools/*364.*'):pin(p)
    out=dict(stage=364,analysis_passed=len(runs)==4,selected_RTL=338,selected_ARM=355,host359=True,BG5_OBJ2=True,ABI_RTL_implemented=False,candidate_selected=False,
        actual_converter=arm,additional_guards=guards,whole_reference=whole,budget=budget,runs=runs,new_MAP=False,FIT=False,STA=False,physical=False,
        scope='Measured M4 converter, old actual output ARM+IRQ+2slots/ROM retimed by positive ABI additions. Original wire still reaches original FPGA. Extra fragment credit/status CPU waits and new RTL/port latency are NOT proven. No full firmware/65816/physical60fps claim.',pins=pins)
    (ROOT/'analysis/abi364-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=out['analysis_passed'],budget=budget,warm={n:r['rows'][-1] for n,r in runs.items()},pins=len(pins)),indent=2))
if __name__=='__main__':main()
