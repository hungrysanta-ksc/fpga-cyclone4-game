"""Exercise final ACK and EA on the linked runtime with modeled peripherals."""
import argparse
import json
import zipfile
from pathlib import Path
from check_nes_receiver593 import Receiver
from check_nes_transport584 import Probe as Runtime
from check_nes_game478 import crc, sha


class Display(Runtime):
    guard_mode='normal'
    def setup_trial(self,geometry,raw,fault):
        source=Receiver.__new__(Receiver)
        source.serial=source.toggle=0
        source.token=65520
        source.previous=None
        source.calls=[]
        source.state_value=self.state_value
        source.setup(geometry,raw,905)
        self.source_model=source
        self.ep.generation=905
        self.guard_mode=fault
        self.saw_seal=False
        self.saw_ea=False

    def input_exchange(self,tx):
        return self.source_model.exchange(tx)

    def output_exchange(self,tx):
        if tx[0]==0xe1 and tx[1]==3:
            self.saw_seal=True
        if tx[0]==0xea:
            assert self.saw_seal and self.ep.last[:2]==bytes([1,3])
            self.saw_ea=True
            if self.guard_mode=='STOP_at_EA': self.cancelled=True
        response=super().output_exchange(tx)
        if self.guard_mode=='wrong_final_ACK' and tx[0]==0xe0 and self.ep.last[:2]==bytes([1,3]):
            response=bytearray(response)
            response[15]^=1  # generation of latest ACK; keep transaction CRC valid
            response[19]=crc(response[1:19],8,7,0)
        return bytes(response)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('arm','archive','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    with zipfile.ZipFile(args.archive) as z:
        geometry,raw=[z.read('data/frame905.'+s) for s in ('geometry','raw')]
    rows=[]
    for fault in ('normal','wrong_final_ACK','STOP_at_EA'):
        m=Display(args.arm,False,400)
        m.setup_trial(geometry,raw,fault)
        for _ in range(80):
            ok=m.call('nes_runtime165_step',[m.rt])
            if not ok or m.saw_ea:break
        else:raise AssertionError('no terminal display action')
        assert m.saw_seal and bool(ok)==(fault=='normal')
        assert m.saw_ea==(fault!='wrong_final_ACK')
        assert m.state_value()==(0 if ok else 4)
        rows.append(dict(fault=fault,step_ok=bool(ok),SEAL=m.saw_seal,EA=m.saw_ea,
                         displayed_frames=m.get(m.rt,'nes_native_runtime165','frames',4),
                         receiver_state=m.state_value()))
    assert [r['displayed_frames'] for r in rows]==[1,0,1]
    args.out.write_text(json.dumps(dict(ELF=sha(args.arm/'obj-nes-100/sd2snes.elf'),guards=rows,
        scope='Actual ARM runtime, modeled source/output ACK and retirement; no new 65816 execution.'),indent=2)+'\n')
    print(rows)

if __name__=='__main__':main()
