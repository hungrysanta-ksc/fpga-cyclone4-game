"""Share the bytewise CRC-8/ATM reduction between source, plan and queue status."""
import argparse
from pathlib import Path

from nes_raw506 import once


def prepare(src, out):
    out.mkdir(parents=True, exist_ok=False)
    name = "nes_native165.c"
    text = (src/name).read_text()
    old = next(line for line in text.splitlines() if line.startswith("uint8_t nes_wire_crc807("))
    new = """uint8_t nes_wire_crc807(const uint8_t *data,unsigned length){
 uint8_t crc=0;
 while(length--){
  unsigned x=crc^*data++;
  /* x^8 = x^2+x+1 modulo the wire polynomial. Reduce the two
   * overflow bits with the same identity; their degree is at most one. */
  unsigned product=x^(x<<1)^(x<<2);
  unsigned high=product>>8;
  crc=(uint8_t)(product^high^(high<<1)^(high<<2));
 }
 return crc;
}"""
    (out/name).write_text(once(text,old,new), newline="\n")
    name = "nes_sink_window184.c"
    text = (src/name).read_text()
    old = next(line for line in text.splitlines() if line.startswith("static uint8_t crc8("))
    text = once(text,old,"extern uint8_t nes_wire_crc807(const uint8_t *,unsigned);")
    text = once(text,"uint8_t c=0;for(unsigned i=1;i<19;i++)c=crc8(c,rx[i]);",
                "uint8_t c=nes_wire_crc807(rx+1,18);")
    (out/name).write_text(text, newline="\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src",type=Path)
    parser.add_argument("out",type=Path)
    args=parser.parse_args()
    prepare(args.src,args.out)
