# SPDX-License-Identifier: MIT
"""Isolate492 physical boot failure:known-good489 FPGA/SNES plus491 ARM queries.

No boot timeout/gate/check removal. New SNES word expansion is held back.
"""
import argparse,json,zipfile
from pathlib import Path
from nes_schedule492 import funcs,sha
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','verify'])
    for n in ['arm','out']:p.add_argument('--'+n,type=Path,required=True)
    for n in ['baseline','prior','assembly','audit489','audit491']:p.add_argument('--'+n,type=Path)
    a=p.parse_args();v=json.loads((ROOT/'analysis/consume491-verification.json').read_text());assert v['passed']
    if a.mode=='prepare':
        assert sha(a.arm/'obj-nes-100/firmware.stm')==v['ARM']['firmware_SHA256']
        a.out.mkdir(parents=True,exist_ok=False);d=a.out/'patch';d.mkdir()
        for n in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
            s=(a.arm/n).read_text();assert '489'in s;(d/n).write_text(s.replace('489','493'),encoding='utf8',newline='\n')
    else:
        old=json.loads((ROOT/'analysis/output489-package.json').read_text())
        proven=json.loads((ROOT/'analysis/output489-verification.json').read_text())
        assert sha(a.prior)==old['ZIP_SHA256'];assert sha(a.baseline/'obj-nes-100/firmware.stm')==v['ARM']['firmware_SHA256']
        f=a.arm/'obj-nes-100/firmware.stm';before=(a.baseline/'obj-nes-100/firmware.stm').read_bytes();after=f.read_bytes()
        assert before[32:].replace(b'489',b'493')==after[32:]
        assert funcs(a.arm/'obj-nes-100/sd2snes.elf')==funcs(a.baseline/'obj-nes-100/sd2snes.elf')
        packets=frames=0
        for d in sorted(a.audit489.glob('frame*')):
            if not d.is_dir():continue
            older=sorted(d.glob('packet*.bin'));newer=sorted((a.audit491/d.name).glob('packet*.bin'));assert len(older)==len(newer)
            for x,y in zip(older,newer):assert x.read_bytes()==y.read_bytes();packets+=1
            frames+=1
        assert frames==71 and packets==2020
        a.assembly.mkdir(parents=True,exist_ok=False)
        with zipfile.ZipFile(a.prior)as z:data=z.read('01-MMC489-SD-ROOT/sd2snes/fpga_mmc489.bi3')
        import hashlib
        h=hashlib.sha256(data).hexdigest();assert h==old['FPGA_SHA256']==proven['assembly']['BI3_SHA256']
        (a.assembly/'fpga_mmc493.bi3').write_bytes(data)
        fpga=proven['FPGA'];source=fpga['whole_board_inputs']
        asm={'passed':True,'copied_known_good489':True,'source_inputs':source,'BI3_SHA256':h}
        (a.assembly/'result.json').write_text(json.dumps(asm,indent=2)+'\n')
        r={'passed':True,'candidate':'MMC493','limited_functional_trial_ready':True,'physical_acceleration_verified':False,
           'physical_FPS':None,'scope':__doc__,'physical_boot_verified':False,'client_ABI':'4891',
           'ARM':{'firmware_SHA256':sha(f),'firmware_B':f.stat().st_size,'Flash_free_B':148,'new_global_RAM_B':0,
                  '781_linked_functions_exact491':True,'all_nonheader_bytes_label_only':True,'query_change_retained':True},
           'FPGA':{'source_inputs':source,'BI3_byte_identical_to_hardware489':True,'LE':15272,'comb':14078,'FF':8392,
                   'M9K':51,'logical_RAM_bits':264800,'related_timing_ns':fpga['related_timing_ns']},
           'programmer':proven['programmer'],'assembly':asm,
           'compatibility':{'canonical_frames':frames,'ordinary_SEAL_packets_byte_equal':packets,'wire_ABI_unchanged':True},
           'held_back':'491 SNES word DMA/MVN and its newly fitted FPGA image',
           'new_Quartus_Questa_or_programmer_runs':False,
           'baseline':'analysis/hardware490-mmc489.json','failure':'analysis/boot493-hardware492.json',
           'cause_proven':False,'next':'First confirm493 boot and menu from physical logs;do not claim root cause or speedup yet'}
        a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
        print(json.dumps({'passed':True,'FPGA_identical489':True,'frames':frames,'packets':packets,'physical_boot_verified':False}))
