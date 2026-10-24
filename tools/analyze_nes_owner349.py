# SPDX-License-Identifier: MIT
"""NES349 static ownership/deletion audit; no new RTL timing or MAP claim."""
import json
from collections import Counter
from pathlib import Path
from nes_delta231 import BASE, ROOT, sha

def main():
    pins = {}
    def read(p):
        pins[str(p)] = sha(p)
        return p.read_text(encoding='utf-8-sig')
    prior = json.loads(read(ROOT/'analysis/fixed348-verification.json'))
    for name, digest in prior['pins'].items():
        assert sha(Path(name)) == digest, name
        pins[name] = digest
    baseline = json.loads(read(ROOT/'analysis/ingress338-verification.json'))
    d = BASE/'probes/nes-ingress338/window03'
    host = read(d/'nes_mux260.sv'); queue = read(d/'nes_queue260.sv')
    tb = read(d/'joint266_tb.sv')
    assert 'forever #5.952 host_clk=~host_clk' in tb
    for s in ('wire [7:0] header[0:20]', 'wire [191:0] record312=',
              'active305.left<=remaining-1\'b1', 'active305.token<=token+1\'b1',
              'header[0]==14?15:header[0]==12?14:10'):
        assert s in host, s
    for s in ('reg [7:0] buffer[0:1023]', 'expected_address313<472',
              'accepted[0],ingress_offset338', 'load_enable312?field338(load_at315):sn_address'):
        assert s in queue, s
    # Check the actual source address cases, not an inferred register-saving claim.
    mapping = [0,1,2,3,10,11,14,15,12,13,16,17,18,19,20]
    assert "0,1,2,3:field338={4'd0,i}" in queue
    for i in range(4,15):
        assert f'{i}:field338={mapping[i]};' in queue
    for count in (10,14,15):
        packet = bytes(range(256))
        assert bytes(packet[x] for x in mapping[:count]) == bytes(mapping[:count])
        assert len(set(mapping[:count])) == count
    rows = []
    for mode in ('window03','fixed01','normal01'):
        for f in (905,906,907):
            arm=json.loads(read(BASE/f'probes/nes-ingress338/{mode}/arm{f}.json'))
            ops=Counter(bytes.fromhex(t['tx'])[1] for t in arm['transfers'] if t['tx'].startswith('e1'))
            # HLOAD at=0..N plus HCHECK. CHECK semantics retained.
            clocks=sum(n*(17 if op==14 else 16 if op==12 else 12) for op,n in ops.items())
            sequential=sum(n*(23 if op==14 else 22 if op==12 else 18) for op,n in ops.items())
            rows.append(dict(mode=mode,frame=f,E1_packets=sum(ops.values()),ops=dict(ops),
                removable_loader_work_clocks=clocks,removable_loader_work_us=clocks*11.904/1000,
                sequential_full_header_extra_clocks=sequential-clocks,
                caveat='Direct service work only; not end-to-end gain across IRQ/ROM/VBlank thresholds.'))
    warm=next(r for r in rows if r['mode']=='window03' and r['frame']==907)
    assert warm['removable_loader_work_clocks']==185
    fixed=baseline['runs']['fixed01']['rows'][-1]
    request=fixed['first_request_ms']-fixed['start_ms']
    close=6.089722  # Previously derived fixed ROM allowed-window close, retained348 audit.
    read(ROOT/'docs/nes-fixed348-contract.ko.md')
    groups={'host':2161,'queue_SPI':798,'plan':459,'source':1747,'validator_aperture':1159,'outside':10950}
    assert groups['host']+groups['validator_aperture']==baseline['groups']['host_validator_aperture']
    for name in ('queue_SPI','plan','source'):
        assert groups[name]==baseline['groups'][name]
    assert groups['outside']==baseline['outside_comb']
    assert sum(groups.values())==baseline['whole']['comb']==17274
    budget=dict(whole_comb=17274,device_comb=15408,margin_target_comb=155,whole_cap=15253,
                required_net_deletion=2021,joint_host_queue_plan=3418,
                joint_cap_if_source_validator_outside_unchanged=1397,
                joint_removal_fraction=2021/3418,groups=groups,
                measured_candidate_saving=None)
    out=dict(stage=349,passed=True,scope='Static RTL ownership audit and evidence-derived arithmetic; no new simulator/ARM/MAP/FIT/STA run.',
        selected_RTL=338,selected_ARM=336,prior_pins_rehashed=len(prior['pins']),
        active_record_bits=16+48+32+8+17,aliases_storage_bits=0,
        RAM=dict(expected=[0,471],gap=[472,511],slots=[[512,767],[768,1023]],
                 full_21B_headers_two_slots_fit_gap=False,compact_15B_plus_5B_each_fit_gap=True,
                 compact_copy_writes_per_packet=15,active_mutable_context_still_required=True),
        loader_rows=rows,budget=budget,
        timing=dict(selected_continuous_ms=20.689660812,selected_gap_ms=4.022994145333332,
            fixed_ms=fixed['total_ms'],fixed_request_ms=request,prior_window_close_ms=close,
            required_request_advance_ms=request-close,source_ms=fixed['source_ms'],
            source_to_request_ms=request-fixed['source_ms'],
            source_to_request_cap_ms=close-fixed['source_ms'],
            post_ROM_ms=fixed['post_ROM_ms'],post_ROM_cap_ms=3.180,
            post_ROM_required_reduction_ms=fixed['post_ROM_ms']-3.180,
            normal_ms=baseline['runs']['normal01']['rows'][-1]['total_ms']),pins=pins)
    read(Path(__file__).resolve())
    (ROOT/'analysis/owner349-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:out[k] for k in ('stage','passed','prior_pins_rehashed','active_record_bits','budget','timing')},indent=2))
    print('warm loader direct work us:',warm['removable_loader_work_us'])

if __name__=='__main__':main()
