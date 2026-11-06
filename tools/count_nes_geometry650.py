"""Count poll entry and D0 token-check instructions outside the timed SPI envelope."""
import argparse
import json
from pathlib import Path
from check_nes_game478 import Machine,UC_ARM_REG_R1
from nes_geometry650 import encode,legacy,sha


class Poll(Machine):
    def hook(self,u,pc,size,user):
        if pc==getattr(self,"spi",None):
            self.edges.append((u.mem_read(u.reg_read(UC_ARM_REG_R1),1)[0],self.instructions))
        super().hook(u,pc,size,user)


def count(src,data,compact,seed):
    m=Poll(src,bytes(128))
    args=((data/"frame955.geometry").read_bytes(),(data/"frame955.raw").read_bytes(),955)
    m.packets=(encode if compact else legacy)(*args)[0]
    m.prepared=False;m.spi_calls=m.index=0;m.start_token=seed
    layout=m.layout["nes_native165"]
    m.u.mem_write(m.state+layout["next_token"],seed.to_bytes(2,"little"))
    m.u.mem_write(m.state+layout["token_valid"],b"\1")
    rows=[]
    for i in range(7):
        m.edges=[];initial=m.instructions
        assert m.call("nes_native165_poll",[m.state,m.spi|1,0])
        assert [op for op,_ in m.edges]==([0xd0] if i==0 else [])+[0xd1,0xd2,0xd0]
        assert int.from_bytes(m.u.mem_read(m.state+layout["next_token"],2),"little")==((seed+i+1)&65535)
        rows.append(dict(before_first_SPI_ops=m.edges[0][1]-initial,after_confirm_D0_ops=m.instructions-m.edges[-1][1]))
    return rows


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("arm","data","trace","out"):p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--compact",action="store_true")
    a=p.parse_args()
    # All preceding inputs preserve their original packet count. Source token
    # begins at zero and advances once per accepted D2 (including COMMIT).
    seed=sum(e.get("opcode")=="0xd2" and e.get("input_generation",10000)<955
             for e in json.loads((a.trace/"events.json").read_bytes()))&65535
    rows=count(a.arm,a.data,a.compact,seed)
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/"obj-nes-100/firmware.stm"),seed=seed,blocks=rows),indent=2)+"\n")
