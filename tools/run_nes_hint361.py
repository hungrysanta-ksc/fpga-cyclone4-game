# SPDX-License-Identifier: MIT
"""Run M4 hint producer on just-received SPI block and prior committed ARM RAM."""
import argparse,binascii,json
from nes_delta231 import BASE,sha
from probe_nes_arm264 import ARM,ELFFile
from pathlib import Path
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--job',type=Path,required=True);d=ap.parse_args().job.resolve()
 prior=d/'hint-consumed-prior361.bin';blob=(d/'hint-prior361.bin').read_bytes();prior.write_bytes(blob);ref=ARM(d/'output.elf',None)
 elf=BASE/'probes/nes-hint360/arm03/decoder.elf';arm=ARM(elf,None)
 with (d/'output.elf').open('rb') as f:
  syms=ELFFile(f).get_section_by_name('.symtab')
  sizes={n:syms.get_symbol_by_name(n)[0]['st_size'] for n in ('receiver280','resident285')}
 def copy(name,address,length):
  offset=ref.symbols[name]-0x20000000;arm.uc.mem_write(address,blob[offset:offset+length])
 copy('receiver280',arm.symbols['receiver280'],sizes['receiver280']);copy('history286',0x20010000,4910);copy('resident285',0x20020000,sizes['resident285'])
 block=bytes(int(x,16) for x in (d/'hint-block361.hex').read_text().split());arm.uc.mem_write(0x20018000,block)
 before=arm.instructions;assert arm.call('block280',[0x20010000,0x20018000,len(block),binascii.crc_hqx(block,65535)])==1;decode=arm.instructions-before
 epoch=int.from_bytes(block[4:8],'little');serial=int.from_bytes(block[12:16],'little')
 before=arm.instructions;arm.call('hint_reset360',[]);calls=[];packet=b''
 for i in range(70):
  at=arm.instructions;n=arm.call('hint360',[0x20020000,epoch,serial-1,1]);calls.append(arm.instructions-at)
  if n:packet+=bytes(arm.uc.mem_read(arm.symbols['packet360'],n))
  if int.from_bytes(arm.uc.mem_read(arm.symbols['hint_done360'],4),'little'):break
 extra=arm.instructions-before;assert len(packet)==24 and packet[1]==5 and binascii.crc_hqx(packet[:-2],65535)==int.from_bytes(packet[-2:],'little')
 (d/'hint361.hex').write_text(' '.join(f'{v:02x}' for v in packet)+'\n')
 (d/'hint-cost361.hex').write_text(f'{extra:08x} {decode:08x}\n')
 result=dict(passed=True,epoch=epoch,serial=serial,extra_instructions=extra,decode_instructions=decode,calls=calls,packet=packet.hex(),pins={str(p):sha(p) for p in (prior,d/'output.elf',elf,d/'hint-block361.hex',Path(__file__).resolve())},scope=__doc__)
 (d/'hint-arm361.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
