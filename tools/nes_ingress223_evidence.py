# SPDX-License-Identifier: MIT
"""Reconcile functional/ARM/whole-board evidence; never turn a failed gate green."""
from pathlib import Path
import argparse,csv,json,re,collections
from nes_ingress223 import ROOT,BASE,sha
from check_nes_boundary165 import measurements


def read(p):return json.loads(p.read_bytes())
def rows(p):return list(csv.DictReader(p.open(),delimiter='\t'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);a=p.parse_args();d=a.archive
    assert not (d/'manifest01.json').exists()
    prep=read(d/'source01/preparation-ingress223.json')
    for place in ['source01','mapfit01','timing01','io01','paths01']:
        for n,h in prep['sources'].items():
            if n=='board.qsf' and place not in ['source01','mapfit01']:
                expected=(d/'source01'/n).read_text().replace('LAST_QUARTUS_VERSION "25.1std.0 Lite Edition"','LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"')
                assert (d/place/n).read_text()==expected,(place,n)
            else:assert sha(d/place/n)==h,(place,n)
    test=read(d/'test01/result.json');arm=read(d/'check01/result.json')
    assert test['passed'] and arm['passed'] and arm['remaining_margin']>=1024
    for n,h in test['preparation']['generated'].items():assert sha(d/'test01'/n)==h,n
    for n,h in test['preparation']['source_pins'].items():assert sha(BASE/n)==h,n
    for n,h in test['public_sources'].items():assert sha(ROOT/n)==h,n
    for n in ['nes_native_export203.sv','nes_native_spi165.sv']:
        assert sha(d/'source01'/n)==sha(d/'test01'/n)
    assert sha(d/'arm01/src/nes_native165.c')==sha(d/'test01/nes_native165.c')
    assert sha(d/'arm01/src/obj-nes-100/firmware.stm')==arm['firmware_sha256']
    for n in ['map','fit']:assert (d/'mapfit01'/(n+'.exitcode')).read_text()=='0'
    for n in ['nes_board204_timing','nes_cdc206_inventory','nes_board205_paths','nes_reset207_shared_paths']:
        assert (d/'timing01'/(n+'.exitcode')).read_text()=='0'
    assert (d/'io01/io.exitcode').read_text()=='0'
    assert (d/'paths01/nes_ingress223_paths.exitcode').read_text()=='0'
    summary=(d/'mapfit01/output_files/board.fit.summary').read_text()
    fit=(d/'mapfit01/output_files/board.fit.rpt').read_text(errors='replace')
    resource=dict(le=int(re.search(r'Total logic elements\s*:\s*([\d,]+)',summary)[1].replace(',','')),
                  ff=int(re.search(r'Total registers\s*:\s*(\d+)',summary)[1]),
                  lab=int(re.search(r'Total LABs:.*?;\s*(\d+) / 963',fit)[1]),
                  m9k=int(re.search(r'M9Ks\s*; (\d+) / 56',fit)[1]))
    timing={}
    for view in ['nominal','implementation']:
        rs=rows(d/'timing01'/(view+'-paths204.tsv'));assert len({r['corner'] for r in rs})==3
        timing[view]={k:min((r for r in rs if r['kind']==k and ((r['from_clock']=='nes')==(r['to_clock']=='nes'))),
                           key=lambda r:float(r['slack'])) for k in ['setup','hold']}
    approved=all(float(timing[v][k]['slack'])>=0 for v in timing for k in timing[v])
    inv=rows(d/'timing01/inventory206.tsv');top=rows(d/'timing01/topology206.tsv')
    assert len(top)==45
    for x in top:
        expected=x['first'].replace('epoch_meta','epoch_sync') if 'epoch_meta' in x['first'] else x['first'][:-3]+'[1]'
        assert x['fanout']==expected,x
    first={r['first'] for r in top};held=[];gray=[];other=[];classes=collections.Counter()
    for r in inv:
        if ((r['from_clock']=='nes')==(r['to_clock']=='nes')):g='related'
        elif r['kind'] in ['recovery','removal']:g='inherited_reset_review'
        elif r['to'] in first:
            g='gray_first' if '|epoch_meta[' in r['to'] else 'control_first'
            if g=='gray_first' and r['kind']=='setup':gray.append(r)
        elif 'direct_path' in r['from'] and '|held[' in r['from'] and r['to']==r['from'].replace('|held[','|received['):
            g='held_payload'
            if r['kind']=='setup':held.append(r)
        elif 'direct_path' in r['from'] or 'direct_path' in r['to']:g='new_other';other.append(r)
        else:g='inherited_unmodified'
        classes[g]+=1
    assert not other
    heldmax=max(float(r['delay']) for r in held);graymax=max(float(r['delay']) for r in gray)
    assert 11.904-heldmax-2>0 and 45.454-graymax-2>0
    resets=rows(d/'timing01/reset207.tsv')
    assert len(resets)==576 and len({r['to'] for r in resets})==96
    assert all(float(r['slack'])>=0 for r in resets)
    io=measurements(d/'io01')
    costs=[]
    for r in test['cases']:
        costs.append(dict(**r,reduction_percent=100*(1-r['new_bytes']/r['old_bytes']),
                          new_payload_wire_ms=r['new_bytes']*8000/2625000,
                          old_payload_wire_ms=r['old_bytes']*8000/2625000))
    result=dict(evidence_consistent=True,functional_pass=True,arm_pass=True,fit_pass=True,
                related_timing_pass=approved,adopted=False,trial_ready=False,physical=False,new_package=False,
                resource=resource,timing=timing,conditional_io=io,
                cdc=dict(rows=len(inv),single_fanout_first_stages=len(top),classification=dict(classes),
                         new_other=0,held_max_ns=heldmax,gray_max_ns=graymax,reset_paths=len(resets)),
                functional=dict(cases=costs,serial_cases=5,source_faults=4,receiver_faults=14,
                                full_board_cosimulation=False,actual_scroll_capture=False),
                arm=arm,inputs=dict(test=sha(d/'test01/result.json'),board=sha(d/'source01/preparation-ingress223.json'),
                                    arm=sha(d/'check01/result.json')),
                next='Close exact check_response_address[5]->commit_clear strict residual without changing acceptance edge/response ownership/STOP priority. Prefer proven local qualification sharing; no clock/SDC waiver or seed loop. Then full paired board/SNES212 ROM checks and real first-level trial. Keep compact geometry and scroll-map joint16.67ms budget; packing alone not60fps.',
                limitations=['Synthetic geometry reductions are not measured SMB3/FPS. Current real D1 map share is unknown.',
                             'Nominal passes but implementation stricter gate fails; no installable image.',
                             'Conditional IO/held-data bounds are not full electrical/MTBF signoff.',
                             'ARM1912B margin preserved; future mapper/state feature headroom not guaranteed.'])
    files=['nes_ingress223.py','test_nes_ingress223.py','nes_ingress223_build.py','check_nes_ingress223_arm.py',
           'nes_ingress223_evidence.py','nes_ingress223_paths.tcl']
    result['public_sources']={'tools/'+n:sha(ROOT/'tools'/n) for n in files}
    result['public_sources']['tests/nes-functional/ingress223_host.c']=sha(ROOT/'tests/nes-functional/ingress223_host.c')
    text=json.dumps(result,indent=2)+'\n'
    (d/'analysis.json').write_text(text,encoding='utf8')
    (ROOT/'analysis/ingress223-verification.json').write_text(text,encoding='utf8')
    print(json.dumps(dict(resource=resource,timing=timing,cdc=result['cdc'],io=io,
                          trial_ready=False,arm_margin=arm['remaining_margin'])))


if __name__=='__main__':main()
