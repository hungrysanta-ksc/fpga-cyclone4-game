# SPDX-License-Identifier: MIT
"""Joint linked-output budget and source replacement preflight, not FIT/FPS."""
from pathlib import Path
import argparse,json,re,struct
from nes_runtime233 import BASE,sha
from analyze_nes_delta231 import merge
from analyze_nes_geometry230 import packets


def main():
 p=argparse.ArgumentParser()
 for n in ('arm-check','runtime-test','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 read=lambda p:json.loads(p.read_text(encoding='utf-8'))
 arm=read(a.arm_check/'result.json');test=read(a.runtime_test/'result.json')
 assert arm['passed'] and arm['output231_bound'] and not arm['ingress_delta_bound'] and test['passed']
 assert arm['remaining_margin']==1616 and arm['irq_reserve']==508
 fit=BASE/'probes/nes-counter224/mapfit02/output_files/board.fit.rpt'
 text=fit.read_text(encoding='latin-1');line=next(l for l in text.splitlines() if '|nes_native_export203:native_export|' in l and '; 644 (644)' in l)
 cols=[c.strip() for c in line.split(';')]
 export=int(cols[2].split()[0]);assert export==644
 total=int(re.search(r'Total logic elements\s*;\s*([\d,]+) /',text)[1].replace(',',''));assert total==15249
 source=BASE/'probes/nes-delta231/test07';model=read(BASE/'probes/nes-delta231/analysis03/result.json')
 sparse=read(BASE/'probes/nes-sparse232/analysis02/result.json');rows=[]
 for f in sparse['remaining_frames']:
  plans=[tuple(map(int,l.split(','))) for l in (source/f'frame{f}.plans').read_text().splitlines()]
  pattern=merge([(k,slot*n,n) for k,slot,n in plans],0);meta=[]
  for q in packets((source/f'frame{f}.packets').read_bytes()):
   if q[0] not in (2,4,5,8):continue
   k=q[1];at,n,expanded=struct.unpack_from('<HHH',q,10);n=n if q[0]==2 else expanded
   if k==2:meta.append((2,at,n))
   if k==5 and 1121<=at<3169:meta.append((5,at-1121,min(n,3169-at)))
  merged=merge(pattern+meta,96)
  parts={str(k):dict(bytes=sum(n for t,at,n in merged if t==k),commands=sum(t==k for t,at,n in merged)) for k in (0,1,2,5)}
  charge=sum(n+96 for k,at,n in merged)+960
  assert charge==next(r['charge_model'] for r in sparse['frame_results'] if r['frame']==f)
  rows.append(dict(frame=f,parts=parts,final_charge=960,total_charge=charge,over_4192=charge-4192))
 # Proposed ONE 8-bit base bank. Two byte-wide scans are a design scenario,
 # not measured cycles or a universal limit on other producer architectures.
 sdc=BASE/'probes/nes-counter224/mapfit02/board.sdc'
 period=float(re.search(r'-name nes -period ([\d.]+)',sdc.read_text())[1]);assert period==45.454
 geometry=5741;base_blocks=(geometry+1023)//1024;scratch_bytes=2*66+240+13
 assert base_blocks==6 and scratch_bytes<=1024
 warm=model['frame_results'][2:];worst=max(warm,key=lambda r:r['ready4_wire_model'])
 wire_ms=worst['ready4_wire_model']*8/2625000*1000
 scan_cycles=2*geometry;scan_ms=scan_cycles*period/1e6
 r=dict(passed=True,scope=__doc__,arm={k:arm[k] for k in ('firmware_bytes','firmware_sha256','ram_static','ram_free_outside_run','foreground_bound','irq_reserve','remaining_margin','output231_bound','ingress_delta_bound')},
  arm_margin_above_1024=arm['remaining_margin']-1024,source_parser_callchain_approved=False,
  runtime_test=test['output'],remaining_vblank_frames=rows,
  fpga=dict(existing_total_le=total,total_capacity_le=15408,existing_spare_le=15408-total,
            replaceable_exporter_le=export,replacement_arithmetic_ceiling_le=15408-total+export,
            old_exporter_registers=225,existing_m9k=47,capacity_m9k=56,packed_base_bytes=geometry,
            base_m9k_capacity_model=base_blocks,scratch_bytes_capacity_model=scratch_bytes,
            scratch_m9k_capacity_model=1,remaining_m9k_capacity_model=2,
            control_le_proven=False,fit_proven=False,placement_timing_proven=False),
  serialized_two_scan_scenario=dict(frame=worst['frame'],ready4_wire_model=worst['ready4_wire_model'],spi_ms=wire_ms,
            sdc_period_ns=period,minimum_scan_cycles=scan_cycles,scan_only_ms=scan_ms,total_minimum_scenario_ms=wire_ms+scan_ms,
            deadline_ms=1000/60,read_write_query_fsm_cost_excluded=True,physical_clock_measured=False,
            rejected=wire_ms+scan_ms>1000/60),
  decision='Output RUN approved within1024B gate. Do not implement serial two-full-scan source on ready4 worst-case assumptions. Next bound one-pass END-count framing or justified capture/transport overlap; replace exporter, do not append it. Establish logic/ports before whole-board FIT. Keep parallel metadata B if A cannot meet joint budget.',
  retained_protocol_requirements=['base serial/epoch and immutable current lease','no source base valid before verified END/admission','partial transfer poisons both bases until common reset','row shift/raster preserve fetch-time data','no active display-bank writes','early VRAM upload would require per-range valid coverage before gap DMA'],
  limits=['source capacity model is not mapped RAM/controller','subtracting old entity LE is arithmetic, not reclaim/placement guarantee','no source decoder/producer RTL integration','ready4 scenario excludes real polling/CPU/gaps','source before previous-display retire overlap is not implemented','232 fileRPC is not production frame timing','no hardware package or FPS proof'],
  pins={str(f.relative_to(BASE)):sha(f) for f in (fit,sdc,BASE/'probes/nes-delta231/analysis03/result.json',BASE/'probes/nes-sparse232/analysis02/result.json')},
  arm_check_sha256=sha(a.arm_check/'result.json'),runtime_test_sha256=sha(a.runtime_test/'result.json'),script_sha256=sha(Path(__file__)))
 assert r['serialized_two_scan_scenario']['rejected']
 a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:r[k] for k in ('arm','remaining_vblank_frames','fpga','serialized_two_scan_scenario')},indent=2))


if __name__=='__main__':main()
