# SPDX-License-Identifier: MIT
"""Reconcile unchanged336 schedules; exact wire lower bounds and queue layout model."""
import argparse,csv,json,math
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_receipt335 import load_image


def queue_layout(packet,bank):
    """Old compact header + physical24B prefix versus aligned original packet.

    Addresses only. No new RTL, token/credit/STOP implementation is implied.
    """
    op=packet[0];prefix=21 if op==14 else 20 if op==12 else 16
    assert prefix<=len(packet)<=256 and bank in (0,1)
    oldbase=480+272*bank;newbase=512+256*bank
    fields={0:0,1:1,2:2,3:3,10:4,11:5,14:6,15:7,12:8,13:9}
    old={};new={}
    for i,value in enumerate(packet):
        new[newbase+i]=value
        if i<16:
            if i in fields:old[oldbase+fields[i]]=value
        elif i<prefix:old[oldbase+i-6]=value
        else:old[oldbase+24+i-prefix]=value
    indices=[0,1,2,3,10,11,14,15,12,13]+list(range(16,prefix))
    assert [old[oldbase+i] for i in range(len(indices))]==[new[newbase+i] for i in indices]
    assert [old[oldbase+24+i] for i in range(len(packet)-prefix)]==[new[newbase+prefix+i] for i in range(len(packet)-prefix)]
    assert min(new)>=512 and max(new)<1024 and all(x>=480 for x in old)
    return len(indices),len(packet)-prefix


def fixed_plan_cost(tx):
    """Keep existing batch boundaries; cost a16B base plus alternate tags.

    This hypothetical wire version removes short7/8/3B decode. Partial BG
    markers still need an explicit flag. It is not the current E9 ABI.
    """
    assert tx[0]==0xe9
    n=int.from_bytes(tx[1:3],'little');count=tx[3]
    assert len(tx)==n+8
    p=tx[4:4+n];at=0;sizes=[];short=0
    for _ in range(count):
        kind=p[at]&3
        if p[at]&128:
            assert p[at] in (128,129,130,131,135)
            size=3 if kind>=2 else 8 if kind==1 else 7
            fixed=16;short+=1
        else:
            assert p[at]<=3
            size=16+2*p[at+1].bit_count();fixed=size
        assert at+size<=n;at+=size;sizes.append(fixed)
    assert at==n
    packets=1;used=0;plans=0
    for size in sizes:
        if used+size>240 or plans==15:packets+=1;used=plans=0
        used+=size;plans+=1
    return dict(plans=count,short=short,old_wire=len(tx),new_wire=sum(sizes)+8*packets,extra_packets=packets-1)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');args=ap.parse_args()
    root=BASE/'probes/nes-ingress337';pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    previous=js(ROOT/'analysis/read336-verification.json');runs={};packet_cases=0
    for tag in ('window01','fixed01','normal01'):
        d=root/tag;old=BASE/'probes/nes-read336'/tag
        if not (d/'result.json').exists():assert args.partial,tag;continue
        r=js(d/'result.json');reference=js(old/'result.json')
        assert r['passed'] and r['rtl_hashes']==reference['rtl_hashes'] and r['ARM']==reference['ARM']
        for n,h in r['rtl_hashes'].items():read(d/n);assert sha(d/n)==h
        pins[str(d/'output.elf')]=sha(d/'output.elf');assert load_image(d/'output.elf')==load_image(old/'output.elf')
        for n in ('CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc','cycles.csv','blocks.txt','source-ARM-blocks.csv','transaction-cost280.hex','source-cost280.hex','source-length280.hex','source-expected280.hex','control280.hex','source-ARM-decoder.elf','source-ARM-nes_decode280.c'):
            pins[str(d/n)]=sha(d/n);assert sha(d/n)==sha(old/n),(tag,n)
        read(d/'joint266_tb.sv');assert sha(d/'joint266_tb.sv')==r['tb_sha256']
        assert 'Errors: 0, Warnings: 0' in read(d/'vlog.log')
        ev=list(csv.reader(read(d/'joint-events.csv').splitlines()))
        assert [x for x in ev if not x[0].endswith('337')]==list(csv.reader(read(old/'joint-events.csv').splitlines())),tag
        calls=js(d/'calls337.json');profile=js(d/'metadata317.json')
        source_rows=list(csv.DictReader(read(d/'source-ARM-blocks.csv').splitlines()))
        rows=[]
        for prior in previous['runs'][tag]['rows']:
            f=prior['frame'];e=[x for x in ev if len(x)>1 and x[1]==str(f)]
            first=lambda name:next(x for x in e if x[0]==name)
            begin=[x for x in e if x[0]=='input_begin337'];wires=[x for x in e if x[0]=='input_wire337']
            decode=[x for x in e if x[0]=='input_decode337'];assert len(begin)==len(wires)
            block=[x for x in source_rows if int(x['frame'])==f];payload=sum(int(x['length']) for x in block)
            assert sum(x[0]=='input_publish337' for x in e)==len(block)
            assert len(decode)==len(block) and sum(int(x[3]) for x in decode)==sum(int(x['instructions']) for x in block)
            assert sum(int(x[4]) for x in wires if not int(x[3]))==len(block)
            assert sum(int(x[3]) for x in wires)==1
            for b,w in zip(begin,wires):
                actual=(int(w[-1])-int(b[-1]))/1e6
                predicted=int(b[5])/84+8+int(w[5])*8*(2*190.476190476)/1000
                assert abs(actual-predicted)<.002,(tag,f,actual,predicted)
            start=first('start319');done=first('input_done337');req=next(x for x in e if x[0]=='firstreq305' and x[2]=='0')
            if tag!='normal01':assert not 330088<=int(req[3])%357368<354640
            start_ms=int(start[2])/1e9;done_ms=int(done[-1])/1e9;request_ms=int(req[-1])/1e9
            assert abs(done_ms-start_ms-prior['source_ms'])<.001
            first_e9=next(x for x in e if x[0]=='ARM_wire_start334' and x[2]=='233')
            last_close_cycle=(int(req[3])//357368)*357368+354640
            if last_close_cycle>int(req[3]):last_close_cycle-=357368
            close_ms=request_ms+(last_close_cycle-int(req[3]))*45.454/1e6
            # Inclusive end and edge alignment can only make this optimistic.
            close_latest_ms=close_ms+2*45.454/1e6
            floor_wire_bytes=payload+15*len(block)+8
            wire_floor_ms=floor_wire_bytes*8*(2*190.476190476)/1e6+8*(len(block)+1)/1000
            # D5 publishes input ACK at its last rising SCK edge, before
            # the final half-bit and4us SS tail. Do not charge that tail as
            # necessary before input_done. Ignore CDC delay optimistically.
            commit_floor_ms=wire_floor_ms-(4000+190.476190476)/1e6
            first_plan_wire_ms=8/1000+int(first_e9[3])*8*(2*190.476190476)/1e6
            publish_ms=int(first('input_publish337')[-1])/1e9
            first_payload_prefix_ms=.004+13*8*(2*190.476190476)/1e6
            publish_delay_floor=max(0,publish_ms-start_ms-first_payload_prefix_ms)
            empty_wire_ms=sum((8+int(w[5])*8*(2*190.476190476)/1000)/1000 for w in wires if not int(w[3]) and not int(w[4]))
            call_cost={}
            for name in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286'):
                matching=[c for c in calls if c['name']==name];assert len(matching)==3
                call=matching[f-905];call_cost[name]=call['end']['instruction']-call['start']['instruction']
            # Top-level boundaries are independent; nested watch envelopes
            # are retained as evidence, never added again to these costs.
            arm=js(d/f'arm{f}.json');assert arm==js(old/f'arm{f}.json')
            plan_cost=[]
            for t in arm['transfers']:
                tx=bytes.fromhex(t['tx'])
                if tx[:1]==b'\xe9':plan_cost.append(fixed_plan_cost(tx))
                if tx[:1]==b'\xe1':
                    for bank in (0,1):queue_layout(tx[1:-2],bank);packet_cases+=1
            for name,n in call_cost.items():assert n==next(x for x in r['ARM']['frames'] if x['frame']==f)['components'][name]
            rows.append(dict(frame=f,total_ms=prior['total_ms'],unchanged_timeline=True,start_ms=start_ms,input_done_ms=done_ms,source_ms=prior['source_ms'],first_request_ms=request_ms,first_accept_ms=prior['first_accept_ms'],post_ROM_ms=prior['post_ROM_ms'],
                source_blocks=len(block),source_payload_bytes=payload,source_actual_wire_bytes=sum(int(x[5]) for x in wires),source_empty_polls=sum(not int(x[3]) and not int(x[4]) for x in wires),
                source_wire_floor_bytes=floor_wire_bytes,source_transaction_floor_ms=wire_floor_ms,source_commit_wire_floor_ms=commit_floor_ms,first_E9_bytes=int(first_e9[3]),first_E9_wire_ms=first_plan_wire_ms,source_decoder_instructions=sum(int(x[3]) for x in decode),source_prefix_instructions=sum(int(x[5]) for x in begin),
                first_source_publish_ms=publish_ms,first_publish_delay_ms=publish_ms-start_ms,empty_poll_wire_occupancy_ms=empty_wire_ms,empty_polls_finished_before_first_publish=sum(not int(w[3]) and not int(w[4]) and int(w[-1])/1e9<=publish_ms for w in wires),
                retained_first_publish_commit_floor_ms=commit_floor_ms+publish_delay_floor,first_plan_wire_start_ms=int(first_e9[-1])/1e9,source_done_to_request_ms=request_ms-done_ms,
                top_level_prepare_instructions=call_cost,top_level_prepare_ms=sum(call_cost.values())/84000,
                previous_ROM_close_ms=close_ms,previous_close_latest_ms=close_latest_ms,available_before_previous_close_ms=close_latest_ms-start_ms,
                ideal_zero_processing_wire_miss_ms=start_ms+commit_floor_ms-close_latest_ms,ideal_zero_processing_plus_E9_miss_ms=start_ms+commit_floor_ms+first_plan_wire_ms-close_latest_ms,advance_request_to_previous_close_ms=request_ms-close_latest_ms,
                previous_window_bound_applies=tag!='normal01',published_blocks=sum(x[0]=='input_publish337' for x in e),
                fixed_plan_model={key:sum(x[key] for x in plan_cost) for key in ('plans','short','old_wire','new_wire','extra_packets')},
                fixed_plan_added_wire_ms=sum((x['new_wire']-x['old_wire'])*8*(2*190.476190476)/1e6+x['extra_packets']*.008 for x in plan_cost)))
        runs[tag]=rows
    exhaustive=0
    for op in (2,12,14):
        for n in range({2:16,12:20,14:21}[op],257):
            b=bytes([op])+bytes((i*37+n)&255 for i in range(1,n))
            for bank in (0,1):queue_layout(b,bank);exhaustive+=1
    if args.partial:print(json.dumps(dict(runs=runs,layout_cases=exhaustive,actual_packet_cases=packet_cases),indent=2));return
    assert len(runs)==3
    board=BASE/'probes/nes-read336/board01';br=js(board/'result.json');assert br['passed']
    for n,h in br['actual_inputs'].items():read(board/n);assert sha(board/n)==h
    report=board/'output_files/board.map.rpt';read(report);assert sha(report)==previous['pins'][str(report)]
    nodes=previous['own_entity_comb']
    own=lambda suffix:next(v for k,v in nodes.items() if k.endswith(suffix))
    source_transport=previous['groups']['source']-own('nes_core257:encoder')
    assert source_transport==420
    control_only=previous['groups']['queue_SPI']+source_transport+previous['groups']['plan']
    assert control_only==1731
    budget=dict(host=1146,validator_aperture=1160,queue_SPI=600,source=1100,plan=297)
    assert sum(budget.values())==previous['scope_with_132_margin']==4303
    # Existing sharing is evidence, not a new optimization/reclaim estimate.
    checks={'SPI_shared_request_fields':('nes_spi270.sv','Shared request fields replace source/plan args'),
            'source_plan_cursor_already_shared':('nes_core257.sv','assign plan_cursor319=cursor[9:0]'),
            'plan_payload_already_concatenated':('nes_plan_batch206.sv','payload[{writer,count[8:0]}]'),
            'source_payload_already_concatenated':('nes_transport257.sv','memory[{bank,used}]'),
            'plan_CRC_already_shared':('nes_plan_rom267.sv','SHARED_CRC307(1)')}
    for name,(file,fragment) in checks.items():assert fragment in read(root/'window01'/file),name
    read(ROOT/'tools/probe_nes_ingress337.py');read(ROOT/'tools/analyze_nes_ingress337.py')
    out=dict(stage=337,passed=True,selected_RTL=336,selected_ARM=336,runs=runs,whole=previous['whole'],comb_deficit=1970,new_measured_gain_ms=0,new_candidate_comb=None,
             groups=previous['groups'],already_shared=list(checks),scope_budget=budget,scope_reduction_required=2102,outside_comb=10973,
             impossible_delete_all_control_only_comb=control_only,remaining_even_free_control_only=1970-control_only,
             queue_layout=dict(exhaustive_cases=exhaustive,actual_packet_bank_cases=packet_cases,slot_bases=[512,768],slot_bytes=256,expected_end_exclusive=472,spare_bytes=40,wire_delta_bytes=0,new_RAM_bits=0,RTL_implemented=False),
             scope='Passive unchanged336 actual schedules; exact source wire lower bounds and pure address-layout model, no new RTL/MAP/FIT/STA.',pins=pins)
    (ROOT/'analysis/ingress337-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(passed=True,pins=len(pins),warm={k:v[-1] for k,v in runs.items()},layout=out['queue_layout'],scope_budget=budget),indent=2))


if __name__=='__main__':main()
