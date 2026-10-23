# SPDX-License-Identifier: MIT
"""Actual M4 queue-aware publication, including wrap and ambiguous failure."""
import argparse,json,struct
from pathlib import Path
from probe_nes_arm264 import ARM,crc
from unicorn.arm_const import UC_ARM_REG_R0
from nes_delta231 import sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    class Endpoint:
        def transfer(self,tx):
            assert tx[0]==0xe1 and len(tx)==29 and tx[1]==14
            assert crc(tx[:-2])==int.from_bytes(tx[-2:],'big')
            assert tx[22:27]==bytes.fromhex('0000021234')
            self.transfers.append(tx.hex());return bytes(len(tx))
    class CheckedARM(ARM):
        def hook(self,uc,address,size,user):
            io=address==(self.symbols['io259']&~1)
            super().hook(uc,address,size,user)
            if io and ep.fail:uc.reg_write(UC_ARM_REG_R0,0)
    ep=Endpoint();arm=CheckedARM(a.source/'output.elf',ep);rows=[]
    def put(n,v):arm.uc.mem_write(arm.symbols[n],v.to_bytes(4,'little'))
    def word(n):return int.from_bytes(arm.uc.mem_read(arm.symbols[n],4),'little')
    for sent,retired,fail in [(0,0,False),(7,7,False),(65535,65535,False),(1,0,False),(2,0,False),(0,65535,False),(1,65535,False),(0,0,True)]:
        arm.call('reset259',[]);ep.transfers=[];ep.fail=fail
        arm.uc.mem_write(arm.symbols['state259'],struct.pack('<HH',sent,retired))
        b=bytearray(27);b[1]=14;b[21]=1;b[22:27]=bytes.fromhex('0000021234')
        arm.uc.mem_write(arm.symbols['wire259'],bytes(b));put('batch_bytes260',26)
        ok=arm.call('publish_map332',[]);pending=(sent-retired)&65535
        if pending:assert ok and not ep.transfers and word('batch_bytes260')==26
        else:
            assert ok==int(not fail) and len(ep.transfers)==1 and word('batch_bytes260')==0
            # A failed transport may have accepted bytes; never resubmit it.
            again=arm.call('publish_map332',[]);assert again==int(not fail) and len(ep.transfers)==1
        rows.append(dict(sent=sent,retired=retired,transport_failure=fail,issued=len(ep.transfers),passed=True))
    out=dict(passed=True,cases=rows,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),scope=__doc__+' Explicit transport fixture; no RTL timing claim.')
    (a.out/'result.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n');print('PASS',len(rows))


if __name__=='__main__':main()
