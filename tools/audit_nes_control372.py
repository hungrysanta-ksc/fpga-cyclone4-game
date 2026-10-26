# SPDX-License-Identifier: MIT
"""Disjoint whole-MAP replacement ceilings and real RAM/clock constraints."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,sha
from analyze_nes_source368 import whole
from nes_bg295 import unbatch

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=BASE/'probes/nes-source368/map01';pins={}
 def read(name):
  f=d/name;pins[str(f)]=sha(f);return f.read_text(encoding='utf-8-sig')
 names=['nes_core257:encoder','nes_transport257:transport','nes_spi270:spi_front270','nes_validator278:validator','nes_output260:flow','nes_plan_batch206:transport','nes_plan_spi200:endpoint','nes_queue260:queue']
 rpt=d/'output_files/board.map.rpt';pins[str(rpt)]=sha(rpt);cost={}
 for line in rpt.read_bytes().splitlines():
  cells=line.decode('ascii',errors='replace').split(';')
  if len(cells)>3 and cells[1].strip().strip('|') in names:
   cost[cells[1].strip().strip('|')]=int(re.search(r'\((\d+)\)',cells[2])[1])
 assert len(cost)==8 and sum(cost.values())==6064 and cost[names[-1]]==224
 for f in (d/'result.json',BASE/'probes/nes-source371/map01/result.json'):pins[str(f)]=sha(f)
 value=whole(d);required=value['comb']-15408+155;assert required==2445
 retained=cost[names[0]]+cost[names[3]];pool=sum(cost.values())-retained
 pure_host=cost[names[2]]+cost[names[4]]+cost[names[6]]+cost[names[7]]
 q=read('nes_queue260.sv');flow=read('nes_mux260.sv');v=read('nes_validator278.sv');plan=read('nes_plan_batch206.sv');source=read('nes_transport257.sv');read('nes_spi270.sv')
 assert 'expected_address313<472' in q and "{1'b1,accepted[0],ingress_offset338}" in q
 assert 'rec_i<24?{4\'b1110,rec_i[4:0]}' in v and 'cursor<166' in v
 assert 'count<512' in plan and 'seal_plans>16' in plan
 assert 'always @(posedge clk)' in q and '.clk(host_clk)' in flow and 'always @(posedge nes_clk)' in plan and 'always @(posedge src_clk)' in source
 native=[];frontiers=[]
 for frame in range(905,915):
  file=BASE/f'probes/nes-source370/joint02/actual-plans293-{frame}.bin';pins[str(file)]=sha(file);records=unbatch(file.read_bytes())
  old_clocks=2*sum(map(len,records));n=len(records)
  native.append(dict(frame=frame,records=n,old_read_data_clocks=old_clocks,native32B_pipelined_data_clocks=32*n,native32B_two_cycle_data_clocks=64*n,
   pipelined_delta_us=(32*n-old_clocks)/22,two_cycle_delta_us=(64*n-old_clocks)/22,
   native32bit_8word_pipelined_clocks=8*n,native32bit_8word_two_cycle_clocks=16*n,
   word_pipelined_delta_us=(8*n-old_clocks)/22,word_two_cycle_delta_us=(16*n-old_clocks)/22,excludes_control_and_END=True))
  af=BASE/f'probes/nes-source370/joint02/arm{frame}.json';pins[str(af)]=sha(af)
  blocks=[bytes.fromhex(t['rx'])[:-2] for t in json.loads(af.read_text())['transfers'] if t.get('source_phase367')==2 and t['rx']]
  data=b''.join(blocks);assert data[:3]==b'N5\2';records=[data[:20]];at=20;cut=None;BG=False
  while at<len(data):
   if data[at:at+3]==b'\xff\xff\0':size=10 if data[at+3]==3 else 6;assert data[at+3] in (3,4)
   else:
    index=data[at]&127
    if index<32:BG=True;cut=len(records)+1
    length=66 if index<32 else 46 if index==67 else 64;mb=(length+7)//8
    size=4 if data[at]&128 else 1+mb+sum(x.bit_count() for x in data[at+1:at+1+mb])
   records.append(data[at:at+size]);at+=size
  assert at==len(data)
  def pack(boundary=None):
   out=[];held=b''
   for i,rec in enumerate(records):
    if held and (len(held)+len(rec)>248 or i==boundary):out.append(held);held=b''
    held+=rec
    if len(held)==248 or rec[:4]==b'\xff\xff\0\4':out.append(held);held=b''
   assert not held;return out
  assert pack()==blocks,'Actual record-atomic block boundaries must match'
  proposed=pack(cut) if cut is not None and not(data[3]&1) else blocks
  assert b''.join(proposed)==data
  frontiers.append(dict(frame=frame,old_block_lengths=list(map(len,blocks)),proposed_lengths=list(map(len,proposed)),
   first_payload_reduction_bytes=len(blocks[0])-len(proposed[0]),extra_header_CRC_bytes=15*(len(proposed)-len(blocks)),
   current_source_bytes_unchanged=True,RTL_implemented=False,timing_credit_ms=0))
 lengths=BASE/'probes/nes-source370/joint02/source-ARM-blocks.csv';pins[str(lengths)]=sha(lengths);frames={}
 for row in list(csv.reader(lengths.read_text().splitlines()))[1:]:frames.setdefault(int(row[0]),[]).append(int(row[2]))
 assert len(frames)==71
 bounds=[]
 for frame,lens in frames.items():
  if frame<907:continue
  slots=[]
  for capacity in (2,4):
   k=max(0,len(lens)-capacity);wire=sum(lens[:k])+15*k+(8 if k else 0)
   slots.append(dict(FPGA_packets=capacity,min_ARM_raw_slots=k,wire_byte_lower_bound=wire,wire_us_lower_bound=wire*64/21))
  bounds.append(dict(frame=frame,packets=len(lens),slots=slots))
 tb=BASE/'probes/nes-source370/joint02/joint266_tb.sv';pins[str(tb)]=sha(tb);assert '#190.476190476' in tb.read_text()
 result=dict(passed=True,new_RTL=False,new_MAP=False,whole370=value,whole371=whole(BASE/'probes/nes-source371/map01'),
  disjoint_self_comb=cost,required_with155reserve=required,retained_codec_checker_scenario=retained,control_pool_with_queue=pool,replacement_control_ceiling=pool-required,
  cases=[dict(name='Host only,keep mixed-clock source/plan',pool_upper_bound=pure_host,replacement_upper_bound=pure_host-required),
   dict(name='Host plus entire mixed-clock source transport,optimistic upper bound',pool_upper_bound=pure_host+cost[names[1]],replacement_upper_bound=pure_host+cost[names[1]]-required),
   dict(name='All eight modules including codec/checker control',pool_upper_bound=sum(cost.values()),replacement_upper_bound=sum(cost.values())-required)],
  port_contract=[dict(RAM='source512B',A='NES source write',B='host D4 read',constraint='Move producer clock only with actual row bridge/ownership replacement;no clock mux or free CDC.'),
   dict(RAM='queue1024B',A='host E1 writes',B='host packet/header OR independent expected R/W',constraint='0..471 expected,512..1023 two immutable256B slots.472..511 candidate40B only;expected read consumption must be bounded.'),
   dict(RAM='phase1024B',A='NES source',B='host validator',constraint='Source scratch/H2/valid/hash/receipt lifetimes remain explicit;row/state storage is not free.'),
   dict(RAM='plan1024B',A='host write',B='NES read',constraint='Two512B banks;32B native record*16 fits capacity but decoding/seal/clock costs are unimplemented.')],
  host_context_candidate=dict(SPI_request=[472,483],active_record=[484,499],execution=[500,507],spare=[508,511],bytes=36,
   retained_FF='SPI shift/synchronizers,immutable snapshot and token/serial burn history,CDC grants;source/checker states not included.',
   implemented=False,port='Would add an A-side read/owner arbiter;B remains expected/read-event priority. No throughput or area credit.'),
  native_plan_data_read_allocations=native,geometry_boundary_packet_replay=frontiers,recorded71_packet_capacity_bounds=bounds,
  raw_slot_condition='Background raw-only reception while previous planner owns history;no semantic consumption until that retire.',
  overlap_candidate=dict(source_packet_RAM_bytes=1024,source_shadow_RAM_bytes=1024,incremental_RAM_bits=12288,
   proposed_whole_bits=value['RAM_bits']+12288,logical_source_packets=4,output_queue_packets=2,
   ARM_raw_prefetch_bytes_for_max_fixture=250*max(max(0,len(x)-4) for f,x in frames.items() if f>=907),
   input_context_and_display_context_separate=True,implemented=False,extra_FPGA_logic=None,whole_area_saving=None),
  implemented_area_saving_vs370=0,scope='Actual whole Lite self costs and source-port audit. Replacement ceilings/data-read allocations,71 fixture size wire lower bounds and record-boundary repacking are budgets,not new71 timing or synthesized candidates. Queue224 is counted separately from parent self2058,never parent inclusive2720.',pins=pins)
 assert result['replacement_control_ceiling']==1227 and result['cases'][0]['replacement_upper_bound']==500
 pins[str(Path(__file__).resolve())]=sha(Path(__file__))
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('control_pool_with_queue','replacement_control_ceiling','cases')}))
if __name__=='__main__':main()
