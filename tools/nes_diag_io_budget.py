# SPDX-License-Identifier: MIT
"""FPGA-only routed bounds and explicitly assumed PCB budget; never signoff."""
from pathlib import Path
import argparse,csv,json,math,hashlib

GROUPS={'address':['ROM_ADDR'], 'ce':['ROM_1CE','ROM_2CE'], 'oe':['ROM_OE'],
        'we':['ROM_WE'], 'byte':['ROM_BHE','ROM_BLE'], 'data':['ROM_DATA']}
def calculate(path,pcb_leg_ns=20.0,extra_ns=5.0):
    assert math.isfinite(pcb_leg_ns) and math.isfinite(extra_ns) and min(pcb_leg_ns,extra_ns)>=0
    with path.open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    corners=sorted({r['corner'] for r in rows});assert len(corners)==3
    for r in rows:
        for n in ['data_delay','arrival','launch','required','latch']:
            r[n]=float(r[n]);assert math.isfinite(r[n])
    expected={'ROM_ADDR['+str(i)+']' for i in list(range(14))+[19]}
    expected|={'ROM_DATA['+str(i)+']' for i in range(16)}
    expected|={'ROM_1CE','ROM_2CE','ROM_OE','ROM_WE','ROM_BHE','ROM_BLE'}
    for corner in corners:
        for typ in ['setup','hold']:
            out=[r for r in rows if r['corner']==corner and r['analysis']==typ and r['direction']=='out']
            assert {r['to'] for r in out}==expected
            inp=[r for r in rows if r['corner']==corner and r['analysis']==typ and r['direction']=='in']
            assert {r['from'] for r in inp}=={'ROM_DATA['+str(i)+']' for i in range(16)}
            assert all('reader|data_hold[' in r['to'] for r in inp)
    bounds={}
    for name,prefixes in GROUPS.items():
        rr=[r for r in rows if r['direction']=='out' and any(r['to'].startswith(p) for p in prefixes)]
        lo=min(r['arrival']-r['launch'] for r in rr if r['analysis']=='hold')
        hi=max(r['arrival']-r['launch'] for r in rr if r['analysis']=='setup')
        assert lo<=hi
        bounds[name]=dict(min_ns=round(lo,3),max_ns=round(hi,3))
    inp=[r for r in rows if r['direction']=='in']
    imin=min(r['arrival']-r['launch'] for r in inp if r['analysis']=='hold')
    imax=max(r['arrival']-r['launch'] for r in inp if r['analysis']=='setup')
    setup_adjust=min(r['required']-r['latch'] for r in inp if r['analysis']=='setup')
    hold_adjust=max(r['required']-r['latch'] for r in inp if r['analysis']=='hold')
    lo=lambda n:bounds[n]['min_ns'];hi=lambda n:bounds[n]['max_ns']
    # Conservative global min/max across all corners and launch registers.
    # Allowances are FPGA budget left for unspecified PCB/analog uncertainty.
    limits={
      'address_before_ce':125+lo('ce')-hi('address'),
      'address_before_oe':125+lo('oe')-hi('address'),
      'write_pulse_tWP46':375+lo('we')-hi('we')-46,
      'write_address_tAW70':500+lo('we')-hi('address')-70,
      'write_ce_tCW70':375+lo('we')-hi('ce')-70,
      'write_byte_tBW70':500+lo('we')-hi('byte')-70,
      'write_data_tDW23':500+lo('we')-hi('data')-23,
      'write_data_hold_tDH0':125+lo('data')-hi('we'),
      'write_address_hold_tWR0':125+lo('address')-hi('we'),
      'read_tAA70':500+setup_adjust-imax-hi('address')-70,
      'read_tCO70':375+setup_adjust-imax-hi('ce')-70,
      'read_tBA70':375+setup_adjust-imax-hi('byte')-70,
      'read_tOE20':375+setup_adjust-imax-hi('oe')-20,
      'read_sample_hold_disable_min0':125+min(lo('ce'),lo('oe'))+imin-hold_adjust,
      'normal_ce_low_tCEM8000':8000-500-hi('ce')+lo('ce'),
      'normal_ce_high_tCPH5':125+lo('ce')-hi('ce')-5}
    limits={n:round(v,3) for n,v in limits.items()}
    assumed_cost=2*pcb_leg_ns+extra_ns
    scenario={n:round(v-assumed_cost,3) for n,v in limits.items()}
    return dict(candidate='NES-DIAG-SAFETY-068',path_rows=len(rows),corners=corners,output_dynamic_bits=len(expected),
       constant_address_bits=[14,15,16,17,18,20,21],fpga_clock_to_pin=bounds,
       input=dict(min_pin_to_capture_ns=round(imin,3),max_pin_to_capture_ns=round(imax,3),
                  setup_capture_adjust_ns=round(setup_adjust,3),hold_capture_adjust_ns=round(hold_adjust,3)),
       remaining_external_budget_ns=limits,scenario_assumptions=dict(pcb_each_leg_ns=pcb_leg_ns,extra_ns=extra_ns,measured=False),
       scenario_margin_ns=scenario,scenario_positive=all(v>=0 for v in scenario.values()),
       source_tsv_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
       scope='zero-IO-delay measurement overlay, FPGA paths only; normal continuous-clock equations',
       external_io_signoff=False,power_voltage_verified=False,clock_halt_safe=False,installable=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--paths',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--pcb-leg-ns',type=float,default=20);p.add_argument('--extra-ns',type=float,default=5)
    a=p.parse_args();assert not a.out.exists();r=calculate(a.paths,a.pcb_leg_ns,a.extra_ns)
    a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print('FPGA-only rows='+str(r['path_rows'])+' scenario_min_ns='+str(min(r['scenario_margin_ns'].values()))+' signoff=false')
