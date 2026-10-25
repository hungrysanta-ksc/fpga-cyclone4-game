# SPDX-License-Identifier: MIT
"""Added ABI cost sensitivity on unchanged338/355/359 + BG5/OBJ2 RTL.

The old packets still traverse the real two-slot receiver. Measured converter
instructions and positive wire deltas delay their issue; extra fragment CS and
14B response are allocations. New fragment credit waits / receiver are absent.
This is a coupled diagnostic, not proof of a new protocol's execution time.
"""
import json,os,shutil,sys
if '--keep-source' not in sys.argv:sys.argv.append('--keep-source')
import probe_nes_objpath362 as previous
from probe_nes_abi364 import Converter
from nes_delta231 import BASE,ROOT,sha
import probe_nes_live287 as live
mode=int(os.environ['NES364_ABI']);assert mode in (0,1)
old_exchange=live.Live.exchange

def exchange(self,tx):
    row=None
    if tx and tx[0] in (0xe1,0xe9):
        if not hasattr(self,'converter364'):
            self.converter364=Converter(BASE/'probes/nes-abi364/arm01/abi364.elf',mode);self.cost364=[]
        serial=int.from_bytes(tx[5:9],'little') if tx[0]==0xe1 else self.converter364.serial
        assert serial
        encoded,instructions,count=self.converter364.convert(tx,serial)
        extra=count-1;positive=max(0,len(encoded)-len(tx))
        cycles=positive*256+extra*(2*672+14*256)
        row=dict(serial=serial,command=tx[0],old_bytes=len(tx),new_bytes=len(encoded),new_packets=count,
            helper_instructions=instructions,positive_wire_bytes=positive,extra_wire_CS_cycles=cycles,
            before_RTL_ns=self.now,new_hex=encoded.hex())
        self.arm.instructions+=instructions
        self.exception_cycles+=cycles
    result=old_exchange(self,tx)
    if row:
        row['after_RTL_ns']=self.now;self.cost364.append(row)
        self.transfers[-1]['ABI364']=row
        (self.d/'abi-cost364.json').write_text(json.dumps(dict(mode=mode,rows=self.cost364),indent=2)+'\n')
    return result

live.Live.exchange=exchange
engine=previous.engine;old_prepare=engine.prepare
def prepare(*args,**kwargs):
    src,pins=old_prepare(*args,**kwargs);d=args[0]
    for n in ('nes_abi364.c','probe_nes_abi364.py','probe_nes_abipath364.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    elf=BASE/'probes/nes-abi364/arm01/abi364.elf';shutil.copyfile(elf,d/'abi364.elf');pins[str(elf)]=sha(elf)
    return src,pins
engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
