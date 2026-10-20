# SPDX-License-Identifier: MIT
"""Retain270 ARM guards, then exercise split bounds and preflight atomicity."""
from pathlib import Path
import argparse,json,struct,sys
import guard_nes_arm270 as old
from probe_nes_split274 import verify,ARM,plans,u16,sha,Endpoint

def main():
 saved=old.old.verify
 try:old.old.verify=verify;old.main()
 finally:old.old.verify=saved
 ap=argparse.ArgumentParser();ap.add_argument('--arm',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
 a=ap.parse_args();prior,groups=plans();pp=groups[1]
 def packet(op,kind,offset,data,out=0):
  p=bytearray(16)+data;p[0]=op;p[1]=kind;p[10:12]=offset.to_bytes(2,'little')
  p[12:14]=len(data).to_bytes(2,'little');p[14:16]=out.to_bytes(2,'little');return bytes(p)
 cases=[
  ('CGRAM_start',packet(2,3,1,bytes(32))),
  ('CGRAM_length',packet(2,3,0,bytes(17))),
  ('CGRAM_limit',packet(2,3,496,bytes(32))),
  ('section',packet(2,2,0,bytes(16))),
  ('scroll_partial',packet(2,5,1,bytes(20))),
  ('bitmap_start',packet(2,5,1122,bytes(16))),
  ('tail_start',packet(2,5,3170,bytes(16))),
  ('tail_end',packet(2,5,3169,bytes(17))),
  ('dense_limit',packet(10,2,250,bytes(7))),
  ('dense_empty',packet(10,2,0,b'')),
  ('RLE_marker',packet(11,2,0,b'\2\xff')),
  ('RLE_prefix_only',packet(11,2,0,b'\3')),
  ('RLE_truncated',packet(11,2,0,b'\3\2\x11')),
  ('RLE_overflow',packet(11,2,0,b'\3\xff\xff\x80')),
  ('RLE_type',packet(11,3,0,b'\3\xff')),
  ('manifest_outlen',packet(11,2,0,b'\3\xff',2)),
 ]
 checked=[]
 class NoSPI:
  def transfer(self,tx):raise AssertionError('dry preflight touched SPI')
 for label,p in cases:
  arm=ARM(a.arm/'output.elf',NoSPI());arm.call('reset259',[])
  arm.uc.mem_write(arm.symbols['scroll274'],struct.pack('<I',21))
  arm.uc.mem_write(arm.symbols['raw274'],struct.pack('<I',7))
  arm.uc.mem_write(0x20010000,p)
  assert arm.call('parts274',[0x20010000,len(p),1])==0,label
  assert arm.uc.mem_read(arm.symbols['state259']+17,1)[0]==21,label
  checked.append(label)
 # Malformed data follows enough legal RLE tokens to trigger a first split.
 # Whole-packet preflight must prevent any fragment of that command escaping.
 pp=[bytes(p) for p in groups[50]];i=next(i for i,p in enumerate(pp) if p[0]==11)
 bad=bytearray(pp[i]);bad.extend(b'\1');bad[12:14]=(len(bad)-16).to_bytes(2,'little');pp[i]=bytes(bad)
 ep=Endpoint();ep.begin(50,groups[50]);arm=ARM(a.arm/'output.elf',ep);arm.call('reset259',[])
 blob=b''.join(len(p).to_bytes(2,'little')+p for p in pp)
 arm.uc.mem_write(0x20010000,blob);meta=(prior/f'expected-{u16(pp[0],8)}.bin').read_bytes()
 arm.uc.mem_write(0x20018000,meta);arm.uc.mem_write(arm.symbols['material259'],struct.pack('<I',0x20018000))
 assert arm.call('frame259',[0x20010000,len(blob),50,u16(pp[0],8)])==0
 assert arm.uc.mem_read(arm.symbols['state259']+17,1)[0]==21
 assert not any(p[0] in (11,3) for p in ep.packets)
 before=len(ep.transfers)
 assert arm.call('frame259',[0x20010000,len(blob),50,u16(pp[0],8)])==0 and len(ep.transfers)==before
 path=a.out/'result.json';r=json.loads(path.read_text());r.update(split_guards=checked,
  partial_RLE_preflight=dict(passed=True,no_fragment_sent=True,sticky_no_more_SPI=True),
  script_sha256=sha(Path(__file__)),scope=__doc__)
 path.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps(dict(passed=True,split_guards=len(checked),partial_RLE_atomic=True)))

if __name__=='__main__':main()
