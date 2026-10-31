# SPDX-License-Identifier: MIT
"""Reconcile505 whole/steady timing without summing overlapping phases."""
import argparse,json
from pathlib import Path
from hashlib import sha256
def sha(p):return sha256(p.read_bytes()).hexdigest()
def analyze(root,client):
    read=lambda n:json.loads((root/n/'verification.json').read_text())
    sequences=[]
    for name,phase in [('sequence03',0),('phase02',85909)]:
        r=read(name);assert r['passed']and len(r['frames'])==12
        f=r['frames'];first,last=f[0],f[-1]
        whole_delta=last['candidate_ACK']-last['baseline_ACK']
        warm_delta=(last['candidate_ACK']-first['candidate_ACK'])-(last['baseline_ACK']-first['baseline_ACK'])
        sequences.append(dict(run=name,start_phase_masterclocks=phase,frames=12,early_descriptors=r['early_descriptors'],early_bytes=r['early_bytes'],whole12_delta_ms=whole_delta/21477.272,first_frame_delta_ms=first['ACK_delta_ms'],remaining11_delta_ms=warm_delta/21477.272,remaining11_mean_delta_ms=warm_delta/21477.272/11,early_DMA_endpoint_scanlines=r['early_DMA_endpoint_scanlines'],max_setup_masterclocks=r['max_setup_masterclocks'],identical_VRAM_DMA_bytes_and_RGB=r['identical_VRAM_DMA_bytes_and_RGB']))
    guards=[]
    for n in ['guards01','bad_coverage-01','bad_version-01','bad_count-01','zero_count-01','bad_length-01']:
        r=read(n);assert r['passed']and r['retained_active_RGB']and r['early_descriptors']>0
        guards.append(dict(run=n,mode=r['mode'],passed=True,old_active_pixels_and_identity_retained=True,tentative_bank_coverage_and_raw_certificate_invalidated=True))
    cold=read('cold03');stress=read('stall02');build=json.loads((client/'build.json').read_text())
    assert cold['poisoned_boot']and stress['modified_schedule_stress']and stress['early_bytes']>=4096
    assert build['body_bytes']==4516 and build['body_delta_vs489']==205 and build['new_WRAM_B']==4
    pins={p.relative_to(root).as_posix():sha(p)for p in root.rglob('*')if p.is_file()and p.name in ['verification.json','requests.bin','client.sfc','capture.lua','result.json','early505.csv','phases504.csv','error.txt','original_error.txt']}
    return dict(schema_version=1,experiment=505,functional_passed=True,selected_for_delivery=False,scope='Actual65816/file-aperture fixtures. No coupled ARM/SPI/IRQ/ROM execution, physical502 warm, new Quartus or menu proof.',physical_baseline='MMC502',candidate_client_SHA256=sha(client/'sink165.sfc'),cost=dict(SNES_body_B=4516,body_delta_B=205,body_free_B=444,program_B=5120,additional_WRAM_B=4,observed_stack_B=11,new_framebuffer_B=0,new_ARM_code_B=0,new_FPGA_control=0,new_M9K=0,Quartus_Lite_remeasured=False),sequences=sequences,cold502=dict(early_bytes=cold['early_bytes'],ACK_delta_ms=cold['frames'][0]['ACK_delta_ms'],poisoned_metadata_boot_passed=True,raw_zero_certificates_rebuilt='8080'),guard_cases=guards,stalled4096=dict(passed=True,early_bytes=stress['early_bytes'],endpoint_scanlines=stress['early_DMA_endpoint_scanlines'],max_setup_masterclocks=stress['max_setup_masterclocks'],not_a_performance_comparison=True),preserved_failure='cold02 harness expected raw certificate0000;existing raw_boot489 deliberately clears VRAM and rebuilds8080. Corrected oracle,cold03 PASS;candidate bytes unchanged.',decision='Functional boundary valid;remaining11 timing -0.012758/+0.032686ms is not sustained improvement. Freeze isolated prefix tuning;require changed wire/body or readiness dependency plus coupled steady measurement before board build/delivery.',next=['Keep502 hardware baseline and existing independent transport CRC/semantic checks;no weakened equality/coverage shortcut','Measure map/ordinary readiness and actual ARM+SPI+IRQ+ROM schedule for a changed transfer/ABI dependency;do not repeat505 phase/opcode tuning','Select only with sustained warm budget improvement,then one matching whole Quartus Lite gate and uniquely named trial without RESTORE'],evidence_pins=pins)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['root','client','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=analyze(a.root,a.client);a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(dict(functional_passed=r['functional_passed'],selected_for_delivery=r['selected_for_delivery'],cost=r['cost'],sequences=r['sequences'])))
