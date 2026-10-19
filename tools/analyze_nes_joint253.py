# SPDX-License-Identifier: MIT
"""Measured integrated boundary cost and explicitly conditional whole schedule."""
from pathlib import Path
import argparse,csv,json,re,shutil
from nes_delta231 import BASE,sha

def area(s):
    return {k:int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',s).group(1).replace(',','')) for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('bits','Total memory bits')]}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--test',type=Path,required=True);p.add_argument('--incremental',type=Path,required=True);p.add_argument('--map',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={}
    def pin(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f
    def read(f):return json.loads(pin(f).read_text())
    def rows(f):return list(csv.DictReader(pin(f).open()))
    test=read(a.test/'result.json');mapped=read(a.map/'result.json');reference=read(a.reference/'result.json')
    incremental=read(a.incremental/'result.json')
    assert incremental['passed'] and incremental['frames']==4 and incremental['incremental_shadow_granules']==8
    assert incremental['rtl_hashes']==test['rtl_hashes']
    assert test['passed'] and test['frames']==71 and len(test['guards'])==14 and mapped['passed'] and reference['passed']
    assert test['rtl_hashes']==mapped['rtl_hashes']
    for n,h in test['rtl_hashes'].items():assert sha(pin(a.test/n))==sha(pin(a.map/n))==h
    for r in (test,incremental,mapped,reference):
        for n,h in r['input_hashes'].items():assert sha(pin(BASE/n))==h,n
    before=area(reference['summary']);after=area(mapped['summary'])
    def hierarchy(path,names):
        report=pin(path).read_text();result={}
        for name in names:
            line=next(l for l in report.splitlines() if l.startswith(';') and l.split(';')[1].strip()==name)
            cols=line.split(';');nums=[tuple(map(int,re.findall(r'\d+',cols[i]))) for i in (2,3)]
            result[name]=dict(comb=nums[0][0],own_comb=nums[0][1],FF=nums[1][0],own_FF=nums[1][1])
        return result
    old_h=hierarchy(a.reference/'output_files/reference.map.rpt',['|nes_source240','|nes_source_encoder240:encoder|','|nes_source_query235:reader|','|nes_source_spi235:transport|'])
    new_h=hierarchy(a.map/'output_files/joint.map.rpt',['|nes_joint253','|nes_core253:encoder|','|nes_query253:reader|','|nes_transport253:transport|'])
    for h in (old_h,new_h):
        top,*children=h.values();assert top['comb']==top['own_comb']+sum(c['comb'] for c in children)
    src={int(r['frame']):{k:int(v) for k,v in r.items()} for r in rows(a.test/'cycles.csv')}
    out={int(r['frame']):{k:int(v) for k,v in r.items()} for r in rows(a.test/'output-cycles.csv')}
    oldsrc={int(r['frame']):{k:int(v) for k,v in r.items()} for r in rows(BASE/'probes/nes-source240/test01/cycles.csv')}
    prior=read(BASE/'probes/nes-joint252/test03/result.json')
    j250=read(BASE/'probes/nes-joint250/analysis02/result.json')
    j249=read(BASE/'probes/nes-joint249/analysis02/result.json')
    wire={r['frame']:r['source_spi_bytes'] for r in j249['wire_rows'] if r['codec']=='block'}
    oldcost={(r['frame'],r['map_setup_clocks'],r['retained_policy']):r for r in j250['rows']}
    frame_rows=[]
    for f in range(905,976):
        s=src[f];o=out[f];old=oldsrc[f]
        frame_rows.append(dict(frame=f,source_total_cycles=s['total'],source_prepare_cycles=s['prepare'],
            source_transfer_cycles=s['transfer'],source_blocked_cycles=s['blocked'],source_ackwait_cycles=s['ackwait'],
            old240_source_total_cycles=old['total'],old240_source_prepare_cycles=old['prepare'],
            source_total_delta_cycles=s['total']-old['total'],output_cycles=o['total'],hash_state_cycles=o['hash_states'],
            transport_crc_cycles=o['transport_crc_cycles'],source_ms=s['total']/22000,output_ms=o['total']/22000,
            combined_measured_boundary_ms=(s['total']+o['total'])/22000))
    schedules=[]
    for row in rows(BASE/'probes/nes-joint252/test03/schedules.csv'):
        if row['binding_policy']!='shadow':continue
        f=int(row['frame']);setup=int(row['setup']);key=(f,setup,row['retained_policy']);old=oldcost[key]
        # Source duration includes query, preparation, real source SPI pins,
        # FIFO stalls and input ACK. Remove old wire+prepare terms together;
        # adding the measured duration on top would double-count input.
        removed_source=wire[f]*8/2625+old['source_prepare_ms']
        removed_output=old['receipt_core_ms']+float(row['FPGA_extra_allocated_ms'])
        measured_source=src[f]['total']/22000;measured_output=out[f]['total']/22000
        total=float(row['total_ms'])-removed_source-removed_output+measured_source+measured_output
        schedules.append(dict(frame=f,setup=setup,retained_policy=row['retained_policy'],old252_ms=float(row['total_ms']),
            removed_input_model_ms=removed_source,measured_input_ms=measured_source,removed_output_model_ms=removed_output,
            measured_output_ms=measured_output,total_ms=total,residual_ms=1000/60-total))
    summaries=[]
    for setup in (500,1000):
        for policy in ('command_tail','only_bitmap_removed'):
            rr=[r for r in schedules if r['setup']==setup and r['retained_policy']==policy]
            worst=max(rr,key=lambda r:r['total_ms'])
            summaries.append(dict(setup=setup,retained_policy=policy,max_ms=worst['total_ms'],min_residual_ms=worst['residual_ms'],worst_frame=worst['frame'],over=[r['frame'] for r in rr if r['residual_ms']<0]))
    warm=frame_rows[2:]
    bounds={k:[min(r[k] for r in warm),max(r[k] for r in warm)] for k in ('source_total_cycles','source_prepare_cycles','output_cycles','hash_state_cycles','source_ms','output_ms','combined_measured_boundary_ms','source_total_delta_cycles')}
    result=dict(passed=True,stage=253,scope=__doc__,test={k:v for k,v in test.items() if k!='input_hashes'},incremental={k:v for k,v in incremental.items() if k!='input_hashes'},
        area_before=before,area_after=after,area_delta={k:after[k]-before[k] for k in before},
        hierarchy_before=old_h,hierarchy_after=new_h,
        integrated_core_listed_in_Quartus_FSM_table='State Machine - |nes_joint253|nes_core253:encoder|state' in (a.map/'output_files/joint.map.rpt').read_text(),
        memory_before=reference['ram_rows'],memory_after=mapped['ram_rows'],warm_bounds=bounds,
        source_faster_frames=sum(r['source_total_delta_cycles']<0 for r in warm),source_slower_frames=sum(r['source_total_delta_cycles']>0 for r in warm),
        mean_source_delta_ms=sum(r['source_total_delta_cycles'] for r in warm)/len(warm)/22000,
        summaries=summaries,rows=schedules,frames_detail=frame_rows,input_hashes=pins,
        limitations=[
          'Baseline is the original240 source boundary including query and SPI. Candidate additionally contains receipt and H2 verification; it is not an attribution experiment for CRC sharing alone.',
          'Standalone MAP is not wholeboard FIT: the 490LE/40LAB shortage cannot be reduced by subtracting these counts.',
          'Actual frame201/query/projector/source/SPI runs; output consumed bytes/ranges and final display ACK are fixtures derived from the prior actual C/SNES output.',
          'Source/receipt share one FSM and one RAM; source stream/block/output CRC16 share one combinational datapath. Query and asynchronous SPI host/mailbox controllers remain.',
          'Timing uses fixture SPI command gaps and host service. Actual ARM planner, output parser/consumption adapter, SNES execution and physical clocks are not measured.',
          'Source timing starts after the captured frame is ready; NES frame execution/capture and its overlap with the real display lease remain outside this timing experiment.',
          'Conditional schedules replace only modeled source input and receipt/shadow durations. They retain 32000 ARM cycles, 32 certificate bytes, parser allocation and other old allocations.',
          'Removal of SNES validate181 remains conditional. CRC16 is error detection, not authentication or a collision-free proof.',
          'No new whole-board FIT/STA, MCU hardware cycles/full RUN/IRQ, physical60fps or firmware package.'])
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    summary={k:v for k,v in result.items() if k not in ('input_hashes','rows','frames_detail')}
    summary.update(input_count=len(pins),private_result_sha256=sha(d/'result.json'))
    (d/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    for name,rr in [('frames.csv',frame_rows),('schedules.csv',schedules)]:
        with (d/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
    shutil.copyfile(__file__,d/'analyzer.py');print(json.dumps({k:result[k] for k in ('area_before','area_after','area_delta','warm_bounds','summaries')},indent=2))

if __name__=='__main__':main()
