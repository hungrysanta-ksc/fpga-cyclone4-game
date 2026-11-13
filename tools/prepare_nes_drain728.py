"""Publish the existing advisory event only after the accepted DMA queue drains.

Replace source-class capture/stack/restore with the existing retired queue
cursor comparison. No new port, WRAM, FPGA register, packet or display ACK.
Event remains lossy on new packet/STOP and ARM expiry remains mandatory.
"""
import argparse,json
from pathlib import Path
from unittest.mock import patch
from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_raw506 import sha
import nes_rom636 as codec
from prepare_nes_longrun694 import optimal

def run(a):
 assert sha(a.base/'body.bin')=='f7973584dbd091976de76808f1444c25c770da5005f3426bc22b69ac5700b74d'
 b=bytearray((a.base/'body.bin').read_bytes());l=json.loads((a.base/'labels.json').read_text());origin=0x7e2000
 lo=l['dma_start680']-origin;hi=l['no_event680']-origin+6
 assert b[lo:lo+11]==bytes.fromhex('c220ad024329007048e220')
 assert b[l['dma_retired680']-origin:l['dma_retired680']-origin+6]==bytes.fromhex('68c90050d009')
 c=Code(origin+lo);c.labels.update(l)
 c.label('dma_start680');c.store(0x420b,1);c.jump('dma_continue680')
 c.label('dma_retired680')
 # A/X are already16-bit after the common range/cursor retirement. Publish
 # only when no accepted jobs remain; both partial and interior retire use it.
 c.absolute(0xad,0x1250);c.absolute(0xcd,0x1252);c.branch(0xd0,'no_event680')
 c.emit(0xe2,0x20);c.store(0x601d,0xa5);c.emit(0xc2,0x20)
 c.label('no_event680');call(c,'service');c.jump('retired_continue680')
 replacement=c.finish();assert len(replacement)<=hi-lo
 b[lo:hi]=replacement+bytes([0xea])*(hi-lo-len(replacement))
 at=l['retired526']-origin
 assert b[at]==0x4c
 b[at+1:at+3]=(c.labels['dma_retired680']&65535).to_bytes(2,'little')
 with patch.object(codec,'pack',optimal):codec.build(a.raw635,a.out,edit_body=lambda body,labels:bytes(b),allow_extension=True)
 (a.out/'labels.json').write_text(json.dumps(c.labels,indent=2)+'\n')
 info=json.loads((a.base/'build.json').read_text());packed=json.loads((a.out/'build.json').read_text())
 for n in ('body_bytes','prefix_B','encoded_B','loader_B','physical_free_B','verify_entry','boot_error'):info[n]=packed[n]
 info.update(candidate='drain728C',body_SHA256=sha(a.out/'body.bin'),body_identical693=False,new_persistent_WRAM_B=0,extra_DMA_stack_B=0,
  replaced_region_B=hi-lo,new_region_B=len(replacement),notice='accepted DMA queue empty after actual retirement; not final display ACK',source_sha=sha(Path(__file__)))
 (a.out/'build.json').write_text(json.dumps(info,indent=2)+'\n')
 print(json.dumps({n:info[n] for n in ('body_bytes','physical_free_B','prefix_B','encoded_B','replaced_region_B','new_region_B')}))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('base','raw635','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
