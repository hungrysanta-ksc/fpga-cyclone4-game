"""Feed SPI bytes from the fitted arbiter/observer bench through the BIN decoder."""
import struct
import sys
from pathlib import Path
from prepare_nes_supply905 import WORK
from read_nes_supply905 import ROW,SIZE,CAP,HEADER,decode

def check(temp):
    words=(temp/'nes-supply905-wire/physical-page905.hex').read_text().splitlines()
    assert len(words)==62
    for index,s in enumerate(words):
        # An all-cache-hit tile has no first/last ROM stamp. Only its 30
        # undefined timestamp bits are outside the protocol.
        if 'x' in s.lower():
            assert 15<=index<=18
    octets=bytes(int(s.lower().replace('x','0'),16) for s in words)
    h,tokens=bytes(1)+octets[:31],bytes(1)+octets[31:]
    assert h[1:6]==tokens[1:6] and h[12:16]==tokens[12:16]
    blob=bytearray(SIZE);HEADER.pack_into(blob,0,0x9001,905,0,1,0,0,44,CAP)
    gen=int.from_bytes(h[2:4],'little');tok=int.from_bytes(h[12:16],'little')
    ROW.pack_into(blob,16,5599,gen,1,150,2,5,1,0,7,0,h[:16],struct.pack('<BBHHHI',1,1,32,0,gen,tok))
    at=16+CAP*ROW.size
    struct.pack_into('<HH',blob,at,1,1);at+=4
    blob[at:at+16]=h[16:32]
    addr=at+256*8
    blob[addr:addr+16]=tokens[16:32]
    path=WORK/'proof/rtl-pages.bin';path.write_bytes(blob)
    rows=decode(path)['rows'][0]['detail']
    assert [r['ROM_grants'] for r in rows]==[0,2]
    assert rows[1]['longest_first_grant_wait_ms']>0 and rows[0]['bank']==0 and rows[1]['bank']==1
    for index,bit in [(addr+2,16),(addr+3,1),(addr+8+1,8)]:
        blob[index]^=bit
        bad=WORK/'proof/damaged-pages.bin';bad.write_bytes(blob)
        try:decode(bad)
        except ValueError:pass
        else:raise AssertionError('accepted damaged return')
        blob[index]^=bit
    print('PASS905 RTL trace bytes, decoded two tokens, held ROM grant and damaged bank/token/length rejection')

if __name__=='__main__':check(Path(sys.argv[1]))
