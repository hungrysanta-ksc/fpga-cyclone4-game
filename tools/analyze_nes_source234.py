# SPDX-License-Identifier: MIT
"""Shared-wire/resource gate for one-pass234, not a timing upper bound."""
from pathlib import Path
import argparse,csv,json,struct
from nes_delta231 import BASE,sha
from analyze_nes_geometry230 import summary


def blocks(lengths):
    n=used=0
    for size in lengths:
        assert 0<size<=248
        if used+size>248:n+=1;used=0
        used+=size
    return n+bool(used)


def main():
    p=argparse.ArgumentParser()
    for n in ('test','arm','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    test=read(a.test/'result.json');arm=read(a.arm/'result.json')
    assert test['passed'] and arm['passed'] and not arm['full_run_irq_approved']
    prior=read(BASE/'probes/nes-delta231/analysis03/result.json');old={r['frame']:r for r in prior['frame_results']}
    fitpath=BASE/'probes/nes-counter224/mapfit02/output_files/board.fit.rpt'
    fit=fitpath.read_text(encoding='latin-1')
    line=next(l for l in fit.splitlines() if '|nes_native_spi165:native_spi|' in l and '; 479 (479)' in l)
    cells=[c.strip() for c in line.split(';')];assert cells[2]=='479 (479)' and cells[6]=='1'
    costs={int(r['frame']):int(r['source_delta_payload']) for r in csv.DictReader((a.test/'cost.csv').open())}
    rows=[]
    for s in test['stats']:
        f=s['frame'];b=old[f];nb=blocks(s['lengths']);delta=s['wire_bytes']-b['source_delta_payload']
        assert delta==8 and costs[f]==s['wire_bytes']
        # Same whole-record248 framing model:3 transfer bytes+16 status/pop.
        ready4=b['ready4_wire_model']+delta+19*(nb-b['source_blocks_model'])
        ready1=b['ready1_wire_model']+delta+19*(nb-b['source_blocks_model'])
        geometry=(a.test/f'frame{f}.geometry').read_bytes();counts=struct.unpack_from('<6H',geometry,5728)
        raw=geometry[5740]*256
        # Inactive source fields MUST be canonical zero, not queried outside
        # the leased valid counts or reused from old collector RAM contents.
        for at,width,cap,count in zip((0,2112,2336,3360,3872,5664),(2,1,8,4,8,1),(1056,224,128,128,224,64),counts):
            assert count<=cap and not any(geometry[at+width*count:at+width*cap]),(f,at)
        queries=sum(counts)+raw
        cycles=s['base_reads']+s['changed_base_writes']+2*queries
        wire_ms=ready4*8/2625000*1000
        source_ms=cycles*45.454/1e6
        ingress_ms=(s['wire_bytes']+19*nb)*8/2625000*1000
        rows.append(dict(frame=f,source_wire_bytes=s['wire_bytes'],blocks=nb,ready4_wire_model=ready4,
                         ready1_wire_model=ready1,base_reads=s['base_reads'],changed_base_writes=s['changed_base_writes'],
                         logical_queries_model=queries,serialized_source_cycles_scenario=cycles,
                         source_ms_scenario=source_ms,wire_ms=wire_ms,serial_total_ms_scenario=wire_ms+source_ms,
                         ideal_ingress_overlap_lower_ms=wire_ms+max(0,source_ms-ingress_ms)))
    warm=rows[2:];worst=max(warm,key=lambda r:r['serial_total_ms_scenario'])
    out=dict(passed=True,scope=__doc__,frames=71,warm_frames=69,model_tests=test['model_cases'],
             actual_c_output=test['output'],exact_output_files=test['exact_output_files'],
             geometry_control_bytes=36,prior231_control_model=28,geometry_operation_bytes_equal231=True,
             stats={k:summary([r[k] for r in warm]) for k in ('ready4_wire_model','ready1_wire_model','serial_total_ms_scenario','ideal_ingress_overlap_lower_ms')},
             over_deadline_serial_scenario=[r['frame'] for r in warm if r['serial_total_ms_scenario']>1000/60],
             over_5468_75_ready1=[r['frame'] for r in warm if r['ready1_wire_model']>5468.75],worst_serial_scenario=worst,
             memory=dict(base_bytes=5741,base_m9k_capacity=6,encoder_scratch_bytes_conservative=635,
                         encoder_scratch_m9k_capacity=1,existing_spi_buffer_bytes=256,existing_spi_m9k=1,
                         proposed_replacement_spi_banks=2,proposed_replacement_spi_bytes=512,
                         existing_total_m9k=47,capacity_m9k=56,total_if_existing_spi_m9k_reused=54,
                         remaining_if_reused=2,remaining_if_new_spi_m9k_added=1,
                         existing_source_le=644,existing_spi_le=479,spare_le=159,
                         combined_replacement_arithmetic_ceiling_le=1282,fit_proven=False),
             arm_layout=arm['layout'],packet_own_stack=arm['stacks']['nes_source234_packet'],full_run_irq_approved=False,
             decision='END-count/CRC and exact one-forward-read algorithm pass. Serial one-pass still misses ready4 worst-case after query/write charge. Next replace exporter+single-block SPI together with bounded block ownership and query-to-canonical-byte bridge; stage packing while prior block transfers. Reuse existing SPI M9K capacity only after actual port/CDC/reset proof. No FIT until concrete control/ports; retain parallel metadata B fallback.',
             limits=['source schedule uses2cycles/logicalquery plus1/base read or changed write, not measured RTL latency',
                     'serial scenario excludes scratch accesses, encoder/CRC control, CPU/gaps and source/consumer stalls',
                     'ideal overlap is a LOWER bound, not a sufficient throughput proof or implemented pipeline',
                     'existing SPI seals a SINGLE block and cannot currently fill the next block until D2',
                     'native_spi479LE+export644LE arithmetic does not prove reclaim,placement or timing',
                     'CRC16 detects tested errors; not authentication or absence of all possible collisions',
                     'source bridge must synthesize zero for inactive fields; preserve leased fetch-time CHR/raster semantics',
                     'source state32B/packet own stack72B does not approve linked RUN IRQ or parser callback chain',
                     '232 five map/OBJ VBlank bursts remain; output packet equality reuses evidence, not a new65816 run',
                     'no production SPI,FPGA firmware,paired package or hardware60fps'],
             rows=rows,pins={str(p.relative_to(BASE)):sha(p) for p in (fitpath,BASE/'probes/nes-counter224/mapfit02/nes_native_spi165.sv',BASE/'probes/nes-counter224/mapfit02/nes_native_export203.sv',BASE/'probes/nes-counter224/mapfit02/nes_native_frame201.sv')},
             test_result_sha256=sha(a.test/'result.json'),arm_result_sha256=sha(a.arm/'result.json'),script_sha256=sha(Path(__file__)))
    assert worst['serial_total_ms_scenario']>1000/60
    a.out.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:out[k] for k in ('stats','worst_serial_scenario','memory','over_deadline_serial_scenario')},indent=2))


if __name__=='__main__':main()
