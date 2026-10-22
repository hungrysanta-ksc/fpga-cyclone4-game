# SPDX-License-Identifier: MIT
"""Bind the NES258 area pair, arbitration tests and actual CPU traces."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

GUARDS=[
 'wrong consume token after complete DMA',
 'stale map token after bank/identity reuse',
 'stale admitted serial after STOP',
 'ordinary ACK writes while typed owns head',
 'consume after partial DMA',
 'wrong ordinary ACK sequence',
 'STOP during map fill, restart with next token',
 'STOP during DMA, old token against new chunk',
 'STOP during ordinary ACK checker, no leaked retire',
 'STOP during tile CDC input, clean restart',
 'duplicate consume after receipt',
 'last token FFFFFFFE allowed, FFFFFFFF rejected',
 'new identity blocked until final display ACK',
 'serial FFFFFFFF to zero after STOP rejected',
 'map lease backpressures tile, then tile drains before final ACK',
 'two sealed tile banks, partial DMA STOP, stale second token rejected',
]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();assert not out.exists();out.mkdir(parents=True)
 base=BASE/'probes/nes-mux258';pins={}
 def pin(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f
 def read(d,n='result.json'):return json.loads(pin(d/n).read_text())
 def text(d,n):return pin(d/n).read_text(errors='replace')
 def rtl(d,r):
  for n,h in r['rtl_hashes'].items():assert sha(pin(d/n))==h,(d,n)
 def archived_inputs(d,r):
  for n,h in r.get('input_hashes',{}).items():
   # Testbench/runner revisions differ between runs; check archived copies.
   f=d/Path(n).name
   assert f.exists() and sha(pin(f))==h,(d,n)
 td=base/'test07';unit=read(td);rtl(td,unit);archived_inputs(td,unit)
 assert unit['passed'] and len(unit['cases'])==34
 assert {(c['shared'],c['guard']) for c in unit['cases']}=={(s,g) for s in (0,1) for g in range(17)}
 for c in unit['cases']:
  log=text(td/f"shared{c['shared']}-guard{c['guard']:02}",'vsim.log')
  assert 'PASS MUX258' in log and not re.search(r'\*\* (Error|Fatal):',log)
 normal=[c for c in unit['cases'] if c['guard']==0]
 assert {k:v for k,v in normal[0].items() if k!='shared'}=={k:v for k,v in normal[1].items() if k!='shared'}
 assert text(td/'shared0-guard00','events.csv')==text(td/'shared1-guard00','events.csv')
 assert normal[0]['bytes']==288 and normal[0]['ticks']==137315
 areas=[]
 for label,s in [('map-separate02',0),('map-shared02',1)]:
  d=base/label;r=read(d);assert r['passed'] and r['shared']==s
  rtl(d,r);archived_inputs(d,r);assert r['rtl_hashes']==unit['rtl_hashes']
  assert r['test_hash']==sha(pin(base/'test06/result.json'))
  text(d,'map.log');text(d,'output_files/mux.map.rpt')
  summary=text(d,'output_files/mux.map.summary');assert summary==r['summary']
  assert 'Lite Edition' in summary
  area={}
  for name,label2 in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:
   area[name]=int(re.search(label2+r'\s*:\s*([\d,]+)',summary)[1].replace(',',''))
  areas.append(area)
 assert areas==[dict(LE=3559,comb=2177,FF=1922,RAM_bits=73984),dict(LE=3319,comb=2062,FF=1751,RAM_bits=41216)]
 coupled=[]
 for label,shared in [('coupled05',True),('reference02',False)]:
  d=base/label;r=read(d);rtl(d,r);archived_inputs(d,r)
  assert r['passed'] and r['shared']==shared
  assert r['bridge']==dict(script_timeout_seconds=90,injected_rpc140_wall_delay_ms=2500,fail_fast_rpc_errors=True)
  for n,h in unit['rtl_hashes'].items():assert r['rtl_hashes'][n]==h
  for n in ['slice257_tb.sv','capture.lua','rpc.do','vlog.log','vsim.log','bridge.json','probe_nes_mux258_coupled.py','nes_mux258.py']:pin(d/n)
  assert not (d/'rpc-error.txt').exists()
  rows=[list(map(int,x)) for x in csv.reader(text(d,'cpu-bus.csv').splitlines())]
  reads=[x for x in rows if x[1]==0 and 0x400800<=x[2]<=0x400fff]
  assert len(reads)==80
  assert [x[2] for x in reads]==list(range(0x400800,0x400810))+list(range(0x400800,0x400840))
  assert bytes(x[3] for x in reads[:16])==bytes.fromhex(text(d,'tile.hex'))
  assert bytes(x[3] for x in reads[16:])==bytes.fromhex(text(d,'selected.hex'))
  ordinary=[x for x in rows if x[1]==0 and 0x400000<=x[2]<=0x4000ff]
  assert len(ordinary)==16 and ordinary[0][3]==2
  ack=[x for x in rows if x[1]==1 and x[2]==0x601c];assert len(ack)==1 and ack[0][3]==0xa5
  cpu=read(d,'cpu-result.json');assert cpu==r['cpu'] and cpu['passed'] and cpu['dma_bytes']==80
  assert r['rom_sha256']==sha(pin(d/'slice.sfc'))
  events=[(n,int(t)) for n,t in csv.reader(text(d,'events.csv').splitlines())]
  assert [x[0] for x in events]==['input_done','staged','staged','dma_done_range','receipt','sealed','display_ack']
  assert [x[1] for x in events]==sorted(x[1] for x in events)
  coupled.append(dict(cpu=cpu,events=events,rom_sha256=r['rom_sha256'],rom_body_bytes=r['rom_body_bytes']))
 assert coupled[0]==coupled[1]
 assert text(base/'coupled05','cpu-bus.csv')==text(base/'reference02','cpu-bus.csv')
 for n in ['cpu-bus.csv','events.csv']:
  assert text(base/'coupled05',n)==text(base/'coupled04',n)
 assert '292037' in text(base/'license01','map.log') and 'evaluation period has expired' in text(base/'license01','map.log')
 bridge_error=text(base/'timeout01','rpc-error.txt')
 assert 'Maximum execution time (1 seconds) exceeded' in bridge_error and re.search(r'seq=14[01] ',bridge_error)
 assert read(base/'timeout01','bridge.json')['injected_rpc140_wall_delay_ms']==2500
 # Preserve the initial intermittent failure and do not overwrite it with PASS.
 text(base/'coupled03','vsim.log');text(base/'coupled03','cpu-bus.csv')
 public=dict(passed=True,stage='R1_bounded_arbitration_complete_full_R1_open',
  selected=dict(unit='test07',coupled='coupled05',reference='reference02',maps=['map-separate02','map-shared02'],timeout_negative='timeout01'),
  scope='ordinary16B header ACK + actual206 tile producer + typed64B map, one queue and exclusive staging lease; bounded source257/receipt/Mesen join',
  area=dict(boundary='nes_mux258 inclusive output adapter; source/core/capture lease/upstream tile192 excluded',
   separate=areas[0],shared=areas[1],shared_minus_separate={k:areas[1][k]-areas[0][k] for k in areas[0]},
   schedule='identical serialized ownership; concurrent dual-aperture reference not evaluated',whole_FIT=False,STA=False),
  normal=normal,guards=[dict(case=i+1,description=s,passed_both_variants=True) for i,s in enumerate(GUARDS)],
  coupled=coupled[0],timing=dict(unit_host_tick_ns=10,unit_total_ms=normal[0]['ticks']/100000,
   map_wait_tile_us=normal[0]['map_wait_tile']/100,ordinary_intentional_hold_us=normal[0]['ordinary_hold']/100,
   ordinary_ACK_check_cycles=normal[0]['ack_check'],actual_CPU_trace_identical=True,
   map_DMA_start_to_consume_master=coupled[0]['cpu']['consume_master']-coupled[0]['cpu']['dma_start_master'],
   physical_timeline=False,whole_frame_bound_ms=None,sixty_fps=False,
   caveat='unit fixed8-NES-cycle receipt endpoint; coupled logical RPC 200+200ns bus and100us poll advance, no common timeline'),
  bridge=dict(negative_error=bridge_error,default_one_second_timeout_reproduced=True,
   original_coupled03='missing Lua return/trace after RPC140; consistent with reproduced timeout, original callback error was not captured',
   repair='per-process90s Lua timeout plus fail-fast error file; both final runs tolerate injected2.5s host delay without emulated trace change'),
  licenses=dict(Standard='292037 evaluation expired before synthesis',Lite='two successful25.1std MAPs',Questa='authorized temporary FLOAT worked'),
  open=['full ARM planner/serializer/RUN/IRQ','ordinary payload semantic consumer','upstream tile192 ROM arbiter',
        'remaining90ranges/8224B and H2 remain255 fixtures','tail/scroll/OAM/H2 actual output transfer',
        'shared physical SPI and source/output scheduling','CDC/IO/STA/whole FIT/mapper margin','heavy7/71/full frame/physical60fps'],
  production227_unchanged=True,P2_selected=False,pins=pins)
 (out/'verification.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 (ROOT/'analysis/mux258-verification.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps(dict(passed=True,area=public['area'],pins=len(pins)),ensure_ascii=False))

if __name__=='__main__':main()
