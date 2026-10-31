# SPDX-License-Identifier: MIT
"""504 measured cost ledger and explicitly unimplemented structural budgets."""
import argparse,json,math,statistics
from pathlib import Path
from hashlib import sha256
from test_nes_capture502_pipeline import source
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:sha256(p.read_bytes()).hexdigest()

def common_generation(records,gen):
    packets=[];buf=bytearray();count=0
    for record in records:
        assert int.from_bytes(record[2:4],'big')==gen
        b=record[:2]+record[4:]
        if len(buf)+len(b)+4>256:
            packets.append(bytes([0x51,count])+gen.to_bytes(2,'big')+buf);buf=bytearray();count=0
        buf+=b;count+=1
    if count:packets.append(bytes([0x51,count])+gen.to_bytes(2,'big')+buf)
    return packets

def decode(packets,gen):
    result=[]
    for p in packets:
        assert len(p)<=256 and p[0]==0x51 and p[1]>0 and int.from_bytes(p[2:4],'big')==gen
        at=4
        for _ in range(p[1]):
            assert at+2<=len(p);key=int.from_bytes(p[at:at+2],'big');kind,index=key>>13,key&8191
            width=8 if kind==0 and index&4096 else [2,1,7,4,7,1,2,8][kind]
            assert at+2+width<=len(p)
            result.append(p[at:at+2]+p[2:4]+p[at+2:at+2+width]);at+=2+width
        assert at==len(p)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['cold','sequence','export','arm','board','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    physical=ROOT/'analysis/hardware503-mmc502.json';r=json.loads(physical.read_text())['runs'][0];n=r['display']['completed']
    ops=r['driver_ops_nested'];rows=[]
    for k,v in ops.items():rows.append(dict(op=k,calls_per_display=v['calls']/n,B_per_display=v['bytes']/n,wire_ms=v['bytes']/n*8/2625,driver_ms=v['ms_per_completed_display']))
    assert math.isclose(sum(x['wire_ms']for x in rows),r['wire_ms_per_display'])
    measurements={}
    for name,folder in [('cold502',a.cold),('historical12',a.sequence)]:
        m=json.loads((folder/'measurement.json').read_text());assert m['passed'] and m['identical_ACK_clocks_and_pixels']
        assert sha(folder/'phases504.csv')==m['phases_SHA256'] and sha(folder/'result.json')==m['result_SHA256']
        for file,h in m['input_pins'].items():assert sha(folder/file)==h
        stages=m['stages'];measurements[name]=dict(measurement_SHA256=sha(folder/'measurement.json'),stages=stages,mean_seal_pre_upload_ms=statistics.mean(x['seal_pre_upload_ms']for x in stages),mean_upload_through_ACK_ms=statistics.mean(x['upload_through_ACK_ms']for x in stages),scope=m['scope'])
    _,_,packets,src=source(a.export);records=[]
    for packet in packets:
        at=0
        while at<len(packet):
            key=int.from_bytes(packet[at:at+2],'big');kind,index=key>>13,key&8191;width=8 if kind==0 and index&4096 else [2,1,7,4,7,1,2,8][kind]
            b=packet[at:at+4+width];assert len(b)==4+width;records.append(b);at+=4+width
    # Keep the terminal COMMIT in a separate packet, as in the existing fixture.
    newer=common_generation(records[:-1],1)+common_generation(records[-1:],1)
    assert decode(newer,1)==records
    negatives=[]
    for name,changed in [('version',bytes([0])+newer[0][1:]),('generation',newer[0][:2]+b'\x00\x02'+newer[0][4:]),('count',newer[0][:1]+bytes([newer[0][1]+1])+newer[0][2:]),('truncated',newer[0][:-1]),('extra',newer[0]+b'\x00')]:
        try:decode([changed],1)
        except AssertionError:negatives.append(name)
        else:raise AssertionError(name)
    packet_budget=dict(scope='Pure Python ABI byte prototype over one actual502 cold export;not RTL/ARM implementation or gameplay savings',source=src,records=len(records),old_packets=len(packets),new_packets=len(newer),old_payload_B=sum(map(len,packets)),new_payload_B=sum(map(len,newer)),old_one_poll_transport_B=sum(map(len,packets))+19*len(packets),new_one_poll_transport_B=sum(map(len,newer))+19*len(newer),exact_record_roundtrip=True,negative_cases=negatives)
    packet_budget['one_poll_transport_wire_delta_ms']=(packet_budget['old_one_poll_transport_B']-packet_budget['new_one_poll_transport_B'])*8/2625
    pins={}
    for root,names in [(a.arm,['nes_native165.c','nes_native_runtime165.c','nes_native165_bulk.inc','nes_game149_spi.inc','nes_dma182.inc','nes_cost471.c','nes_budget210.c']),(a.board,['nes_native_export203.sv','nes_tile_bulk206.sv'])]:
        for name in names:
            f=root/name
            assert f.is_file(),f
            pins[name]=sha(f)
    for name in ['nes_dirty212.py','nes_output489.py','measure_nes_budget504.py']:pins['tools/'+name]=sha(ROOT/'tools'/name)
    payload=sum(r['command_body_projection'].values());allB=r['wire_bytes']/n;nonqueryB=r['nonquery_wire_projection_ms']*2625/8
    result=dict(passed=True,physical_evidence_SHA256=sha(physical),physical=r['display'],op_ledger=rows,measurements=measurements,input_ABI_byte_prototype=packet_budget,
                budgets=dict(spi_hz=2625000,wire_B_per_60Hz=5468.75,provisional_wire12ms_B=3937.5,observed_all_B=allB,observed_nonquery_B=nonqueryB,observed_command_body_B=payload,
                             nonquery_reduction_to_period_B=max(0,nonqueryB-5468.75),nonquery_reduction_to_12ms_B=max(0,nonqueryB-3937.5),
                             driver_minus_wire_ms=sum(v['ms_per_completed_display']for v in ops.values())-r['wire_ms_per_display'],
                             four_2us_per_call_budget_ms=sum(v['calls']for v in ops.values())/n*.008,
                             tile_output_B_per_display=sum(x['out']for x in r['bins'])/n,map_dirty_rows_per_display=sum(x['mapdirty']for x in r['bins'])/n,
                             canonical_history_with7raw_B=5741+7*256,min_M9K_by_bits=math.ceil((5741+7*256)*8/9216),bytewide_M9K=math.ceil((5741+7*256)/1024),free_M9K=5,free_LE=121,free_ARM_Flash_B=148),
                source_pins=pins,selected_next_boundary='Nonblocking early inactive-VRAM drain of immutable dirty-list prefix;preserve mutable append tail,checks and final visibility ACK. Input packet-common context remains companion ABI study,not60fps-approved.',
                A2_full_60Hz_budget_passed=False,actual_new_FPGA_LE=None,new_firmware=False,new_Quartus=False,
                limits=['Physical op/quiet/phase counters overlap;not additive savings. No same-scene rate claim.',
                        'Measured CPU fixtures retain original clocks/pixels;historical12 is not502 warm source/real ARM IRQ ROM timing.',
                        'SPI setup upper allocation includes70/73 paths;driver-minus-wire includes polling/IRQ/guards,not all removable.',
                        'Common-generation proposal must retain wire CRC,format bounds,COMMIT/STOP generation and unknown service/area/stack cost.',
                        'Full7533B previous-image cache cannot fit5 spareM9K without reclaim;no CRC-only equality shortcut.',
                        'Early DMA does not remove mandatory bytes or expand VBlank bandwidth. Palette/OAM/HDMA/global selection stay at final verified VBlank;STOP invalidates tentative bank.',
                        'No confirmed joint60fps architecture yet;next execution gate must measure complete benefit and new costs.'])
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({'budgets':result['budgets'],'packet':packet_budget}))
