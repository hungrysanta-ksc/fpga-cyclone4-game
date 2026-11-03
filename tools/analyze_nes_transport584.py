# SPDX-License-Identifier: MIT
"""Publish metadata-only linked cost and bounded ARM584 evidence."""
import argparse,json,hashlib
from pathlib import Path
from check_nes_supply485_arm import ELFFile

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def elf_cost(p):
    with p.open('rb') as f:
        e=ELFFile(f)
        return dict(code_B=sum(s['sh_size'] for s in e.iter_sections() if s['sh_flags']&4),
                    bss_B=sum(s['sh_size'] for s in e.iter_sections() if s['sh_type']=='SHT_NOBITS' and s['sh_flags']&2))

def run(a):
    report=json.loads((a.test/'result.json').read_text())
    assert report['passed'] and len(report['rows'])==4 and len(report['faults'])==18
    root=Path(__file__).resolve().parents[1]
    assert report['checker_SHA256']==sha(root/'tools/check_nes_transport584.py')
    modules={}
    for m in ('nes_native165','nes_native_runtime165','nes_sink_window184','nes_plan_service200'):
        old=elf_cost(a.base/f'obj-nes-100/{m}.o')['code_B'];new=elf_cost(a.arm/f'obj-nes-100/{m}.o')['code_B']
        modules[m]=dict(baseline_B=old,candidate_B=new,delta_B=new-old)
    cost={}
    for name,src in [('baseline',a.base),('candidate',a.arm)]:
        p=src/'obj-nes-100/firmware.stm'
        cost[name]=dict(firmware_B=p.stat().st_size,firmware_SHA256=sha(p),**elf_cost(src/'obj-nes-100/sd2snes.elf'))
    delta=cost['candidate']['firmware_B']-cost['baseline']['firmware_B']
    assert sum(m['delta_B'] for m in modules.values())==delta==444
    driver=a.base/'nes_native165_bulk.inc'
    assert 'count>259' in driver.read_text()
    calls=[]
    for row in report['rows']:
        g=row['generation'];delay=row['modeled_service_delay']
        for variant in ('577','584'):
            p=a.test/f'{g}-{delay}-{variant}-calls.json';c=json.loads(p.read_text())
            assert max(x['bytes'] for x in c)<=259
            calls.append(dict(file=p.name,SHA256=sha(p),count=len(c),max_transfer_B=max(x['bytes'] for x in c)))
    report.update(decision='reject_transport_only_candidate',modules=modules,linked_cost=cost,
        firmware_delta_B=delta,capacity_excess_B=cost['candidate']['firmware_B']-212992,
        patch=json.loads((a.patch/'manifest.json').read_text()),call_evidence=calls,
        driver=dict(SHA256=sha(driver),unchanged_max_B=259,largest_legal_payload_under_candidate_B=254,
                    advertised_max_payload_B=256,guard_test='mirrored count check, not peripheral execution'),
        producer_scope='Current577 runtime serializes next input poll after display/EA; concurrent next-generation COMMIT is not proven',
        source_pins={n:sha(a.base/n) for n in ('nes_runtime_board165.inc','nes_native165_bulk.inc','nes_dma182.inc')},
        tool_pins={n:sha(root/'tools'/n) for n in ('prepare_nes_transport584.py','check_nes_transport584.py','analyze_nes_transport584.py')},
        firmware_installable=False,product_modified=False,new_FPGA_FIT=False,new_physical_FPS=False)
    a.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(dict(decision=report['decision'],firmware_delta_B=delta,capacity_excess_B=report['capacity_excess_B'],modules=modules)))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','arm','test','patch','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
