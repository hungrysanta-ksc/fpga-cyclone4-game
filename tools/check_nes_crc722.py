"""Linked shared CRC matches independent bitwise reference for every E9 length.

The assembler routine requires positive length. Empty flush must not call it;
all encoded E9 records are nonempty. No table or instruction replacement hook.
"""
import argparse,json,random
from pathlib import Path
from check_nes_supply485_arm import ARM,crc,sha

def run(a):
 m=ARM(a.arm,'normal');m.setup();rng=random.Random(722);rows=[];buf=0x20012000
 for n in range(1,241):
  b=bytes(rng.randrange(256) for _ in range(n));m.u.mem_write(buf,b)
  before=m.instructions;got=m.call('crc_xmodem_block',[65535,buf,n])
  assert got==crc(b,16,0x1021,65535),(n,got)
  rows.append(dict(bytes=n,instructions=m.instructions-before))
 before=len(m.endpoint.calls)
 assert m.call('nes_plan549_first',[m.p]) and len(m.endpoint.calls)==before
 a.out.write_text(json.dumps(dict(passed=True,scope=__doc__,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),lengths=rows,empty_flush_no_SPI=True),indent=2)+'\n')
 print('PASS722 shared CRC240 lengths + empty flush')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
